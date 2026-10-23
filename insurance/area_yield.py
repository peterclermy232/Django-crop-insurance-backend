"""
Area yield index cover: farmers are paid from the average yield of their area
(ward or sub-county) rather than an inspection of their own farm.

    guaranteed = expected yield x coverage level %
    payout %   = (guaranteed - actual) / guaranteed, capped at the product's max payout %
    payout     = sum insured x payout %

Once an area's actual yield is approved, calculate_payouts() creates a claim for
every area yield policy in that area. Those claims skip loss assessment and go
straight to the normal approve -> pay steps.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from insurance.models import Claim, CoverType, Quotation

BASIS_RISK_NOTICE = (
    'Payouts are based on the average yield of the whole {area}, not on your own farm. '
    'You may get no payout after a poor harvest on your farm if the {area} average is good, '
    'and you may get a payout after a good harvest if the {area} average is poor.'
)
CENT = Decimal('0.01')
HUNDRED = Decimal('100')
POLICY_STATUSES = ('WRITTEN', 'PAID')


def basis_risk_notice(product):
    if not product.is_area_yield:
        return None
    area = (product.get_area_level_display() if product.area_level else 'area').lower()
    return BASIS_RISK_NOTICE.format(area=area)


def unit_at_level(unit, level):
    """The unit itself or the one above it at `level`, or None."""
    while unit is not None:
        if unit.level == level:
            return unit
        unit = unit.parent
    return None


def in_area(unit, prefix='farm__administrative_unit'):
    """Filter for records whose unit is `unit` or lies below it (wards sit at most two levels down)."""
    return Q(**{prefix: unit}) | Q(**{f'{prefix}__parent': unit}) | Q(**{f'{prefix}__parent__parent': unit})


def payout_for(product, area_yield, sum_insured):
    """The calculation for one policy, as stored on the claim."""
    guaranteed = (area_yield.expected_yield * product.coverage_level / HUNDRED).quantize(CENT, ROUND_HALF_UP)
    actual = area_yield.actual_yield
    shortfall = max(guaranteed - actual, Decimal('0'))
    payout_percent = (shortfall / guaranteed * HUNDRED) if guaranteed else Decimal('0')
    payout_percent = min(payout_percent, product.max_payout_percent)
    # Pay on the exact percentage; it is only rounded for display
    payout = (sum_insured * payout_percent / HUNDRED).quantize(CENT, ROUND_HALF_UP)
    payout_percent = payout_percent.quantize(CENT, ROUND_HALF_UP)
    return {
        'calculation_method': CoverType.AREA_YIELD,
        'area_yield': str(area_yield.public_id),
        'area': area_yield.administrative_unit.name,
        'area_level': area_yield.administrative_unit.level,
        'yield_unit': area_yield.yield_unit,
        'expected_yield': str(area_yield.expected_yield),
        'coverage_level': str(product.coverage_level),
        'guaranteed_yield': str(guaranteed),
        'actual_yield': str(actual),
        'payout_percent': str(payout_percent),
        'max_payout_percent': str(product.max_payout_percent),
        'sum_insured': str(sum_insured),
        'payout': str(payout),
    }


def area_yield_policies(area_yield):
    """Written or paid area yield policies for this crop and season in this area."""
    unit = area_yield.administrative_unit
    return (
        Quotation.objects
        .filter(in_area(unit), status__in=POLICY_STATUSES,
                farmer__organisation_id=area_yield.organisation_id,
                insurance_product__crop_id=area_yield.crop_id,
                insurance_product__season_id=area_yield.season_id,
                insurance_product__area_level=unit.level,
                insurance_product__product_category__cover_type__calculation_method=CoverType.AREA_YIELD)
        .select_related('farmer', 'farm', 'insurance_product__product_category__cover_type')
        .order_by('quotation_id')
    )


def calculate_payouts(area_yield, user, commit):
    """
    Works out the payout for every policy in the area. With commit, creates a claim
    for each policy that is owed something and doesn't have an area yield claim yet.
    """
    from insurance.serializers.claims import next_claim_number

    rows, created = [], 0
    with transaction.atomic():
        for policy in area_yield_policies(area_yield):
            details = payout_for(policy.insurance_product, area_yield, policy.sum_insured)
            existing = Claim.objects.filter(
                quotation=policy, loss_details__calculation_method=CoverType.AREA_YIELD).first()
            payout = Decimal(details['payout'])
            if existing is not None:
                outcome = 'ALREADY_CLAIMED'
            elif payout <= 0:
                outcome = 'NO_PAYOUT'
            else:
                outcome = 'CLAIM_CREATED' if commit else 'WILL_CREATE_CLAIM'
                if commit:
                    existing = Claim.objects.create(
                        farmer=policy.farmer, quotation=policy, claim_number=next_claim_number(),
                        estimated_loss_amount=payout, status='OPEN', loss_details=details,
                        created_by=user if getattr(user, 'is_authenticated', False) else None,
                    )
                    created += 1
            rows.append({
                'quotation': policy, 'policy_number': policy.policy_number,
                'farmer_name': f'{policy.farmer.first_name} {policy.farmer.last_name}',
                'farm_name': policy.farm.farm_name, 'outcome': outcome,
                'claim_number': existing.claim_number if existing else None, **details,
            })
        if commit:
            area_yield.payouts_calculated_at = timezone.now()
            area_yield.save(update_fields=['payouts_calculated_at', 'date_time_modified'])

    owed = [r for r in rows if r['outcome'] in ('CLAIM_CREATED', 'WILL_CREATE_CLAIM')]
    return {
        'policies': len(rows),
        'claims_created': created,
        'total_payout': str(sum((Decimal(r['payout']) for r in owed), Decimal('0')).quantize(CENT)),
        'rows': rows,
    }
