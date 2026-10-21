import logging
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from insurance.models import (
    AdministrativeUnit, BankAccount, Claim, CoverType, Crop, CropVariety, Farm, Farmer,
    InsuranceProduct, NextOfKin, ProductCategory, Quotation, Season,
)
from insurance.models.inspection import Inspection
from insurance.models.location import FARM_UNITS_RELATED
from insurance.public_ids import expose_id, has_public_id, id_lookup
from insurance.serializers import (
    ClaimSerializer, CoverTypeSerializer, CropSerializer, CropVarietySerializer,
    FarmerSerializer, FarmSerializer, InsuranceProductSerializer,
    ProductCategorySerializer, QuotationSerializer, SeasonSerializer,
)
from insurance.serializers.inspection import InspectionSerializer

logger = logging.getLogger(__name__)

FIELD_ROLES = {'SUPERUSER', 'ADMIN', 'MANAGER', 'AGENT', 'ASSESSOR'}

# Once the office moves a record past these statuses, devices can't change it.
EDITABLE_STATUSES = {
    'quotations': {'OPEN', 'DRAFT'},
    'claims': {'OPEN'},
}


class IsFieldOfficer(BasePermission):
    message = 'Your role is not allowed to sync field data.'

    def has_permission(self, request, view):
        return getattr(request.user, 'user_role', None) in FIELD_ROLES


class EntitySpec:
    def __init__(self, model, serializer, fields, parents=None):
        self.model = model
        self.serializer = serializer
        self.fields = fields            # writable fields accepted from devices
        self.parents = parents or {}    # field name -> parent model


# Processed in this order: parents before children.
ENTITIES = {
    'farmers': EntitySpec(
        Farmer, FarmerSerializer,
        fields=['first_name', 'last_name', 'id_number', 'phone_number', 'email', 'gender',
                'date_of_birth', 'farmer_category', 'country',
                'registration_latitude', 'registration_longitude'],
    ),
    'farms': EntitySpec(
        Farm, FarmSerializer,
        fields=['farm_name', 'farm_size', 'unit_of_measure', 'location_province',
                'location_district', 'location_sector', 'administrative_unit', 'location_unit', 'village', 'clan',
                'latitude', 'longitude', 'status'],
        parents={'farmer': Farmer},
    ),
    'quotations': EntitySpec(
        Quotation, QuotationSerializer,
        fields=['insurance_product', 'sum_insured'],
        parents={'farmer': Farmer, 'farm': Farm},
    ),
    'claims': EntitySpec(
        Claim, ClaimSerializer,
        fields=['estimated_loss_amount', 'loss_details'],
        parents={'farmer': Farmer, 'quotation': Quotation},
    ),
    'inspections': EntitySpec(
        Inspection, InspectionSerializer,
        fields=['inspection_type', 'status', 'scheduled_date', 'scheduled_time', 'completed_at',
                'check_in_latitude', 'check_in_longitude', 'check_in_time',
                'check_out_latitude', 'check_out_longitude', 'check_out_time',
                'findings', 'recommendations'],
        parents={'farm': Farm},
    ),
}

# How to reach the owning farmer (and so the organisation) from each entity
OWNER = {
    'farmers': lambda o: o,
    'farms': lambda o: o.farmer,
    'quotations': lambda o: o.farmer,
    'claims': lambda o: o.farmer,
    'inspections': lambda o: o.farm.farmer,
}


def in_org(name, obj, org):
    return OWNER[name](obj).organisation_id == org.pk


def ref(obj):
    """How to name a record in serializer input: its public id when it has one."""
    return str(obj.public_id) if has_public_id(type(obj)) else obj.pk


class ItemError(Exception):
    def __init__(self, errors, status='error', server_id=None):
        super().__init__(str(errors))
        self.errors = errors
        self.status = status
        self.server_id = server_id


class SyncAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFieldOfficer]

    def post(self, request):
        user = request.user
        changes = request.data.get('changes') or {}
        since = self._parse_since(request.data.get('last_sync'))
        # Taken before processing so nothing written during this request is missed next time
        server_time = timezone.now()

        unknown = set(changes) - set(ENTITIES)
        if unknown:
            return Response({'error': f'Unknown entity types: {", ".join(sorted(unknown))}'}, status=400)

        results = {
            name: [self._sync_item(name, item, user) for item in changes.get(name) or []]
            for name in ENTITIES
        }

        response = {
            'server_time': server_time.isoformat(),
            'results': results,
            'updates': self._updates_since(since, user),
        }
        if request.data.get('include_reference', True):
            response['reference'] = self._reference_data(user, since)
        return Response(response)

    # ------------------------------------------------------------------ upload

    def _sync_item(self, name, item, user):
        spec = ENTITIES[name]
        client_uuid = item.get('client_uuid') if isinstance(item, dict) else None
        if not client_uuid:
            return {'client_uuid': None, 'status': 'error',
                    'errors': {'client_uuid': ['This field is required.']}}

        try:
            with transaction.atomic():
                status, obj = self._upsert(name, spec, item, user)
            return {'client_uuid': client_uuid, 'status': status, 'server_id': expose_id(obj, self.request),
                    'record': self._serialize(spec, obj)}
        except ItemError as e:
            result = {'client_uuid': client_uuid, 'status': e.status, 'server_id': None, 'errors': e.errors}
            if e.server_id is not None:
                # duplicate / locked: hand back the server copy so the device can adopt it
                existing = spec.model.objects.get(pk=e.server_id)
                result['server_id'] = expose_id(existing, self.request)
                result['record'] = self._serialize(spec, existing)
            return result
        except IntegrityError as e:
            logger.warning('Sync integrity error on %s %s: %s', name, client_uuid, e)
            return {'client_uuid': client_uuid, 'status': 'error',
                    'errors': {'non_field_errors': ['This record conflicts with existing data.']}}
        except Exception:
            logger.exception('Sync failed for %s %s', name, client_uuid)
            return {'client_uuid': client_uuid, 'status': 'error',
                    'errors': {'non_field_errors': ['Server error while saving this record.']}}

    def _upsert(self, name, spec, item, user):
        org = user.organisation
        data = {k: item[k] for k in spec.fields if k in item}
        data['client_uuid'] = item['client_uuid']

        resolved = {}
        for field, parent_model in spec.parents.items():
            if item.get(f'{field}_uuid') or item.get(field):
                resolved[field] = self._resolve_parent(field, parent_model, item, org)
                data[field] = ref(resolved[field])

        instance = spec.model.objects.filter(client_uuid=item['client_uuid']).first()
        if instance is not None and not in_org(name, instance, org):
            raise ItemError({'client_uuid': ['Already used by another organisation.']})

        if name == 'farmers' and instance is None and data.get('id_number'):
            existing = Farmer.objects.filter(id_number=data['id_number']).first()
            if existing is not None:
                if existing.organisation_id != org.pk:
                    raise ItemError({'id_number': ['A farmer with this ID number is registered elsewhere.']})
                # Already registered (e.g. at the office): the device links to it
                raise ItemError({'id_number': ['A farmer with this ID number already exists.']},
                                status='duplicate', server_id=existing.pk)

        if instance is not None and name in EDITABLE_STATUSES \
                and instance.status not in EDITABLE_STATUSES[name]:
            raise ItemError(
                {'status': [f'This record is {instance.status} and can no longer be changed from the field.']},
                status='locked', server_id=instance.pk)

        self._apply_server_values(name, data, instance, user, resolved)
        serializer = spec.serializer(instance, data=data, partial=instance is not None,
                                     context={'request': self.request})
        if not serializer.is_valid():
            raise ItemError(serializer.errors)
        extra = {'created_by': user} if instance is None else {}
        if name == 'inspections' and item.get('completed_at'):
            completed_at = self._parse_since(item['completed_at'])
            if completed_at is None:
                raise ItemError({'completed_at': ['Enter a valid date/time.']})
            extra['completed_at'] = completed_at
        obj = serializer.save(**extra)

        if name == 'farmers':
            self._save_farmer_children(obj, item)
        return ('updated' if instance is not None else 'created'), obj

    def _serialize(self, spec, obj):
        return spec.serializer(obj, context={'request': self.request}).data

    @staticmethod
    def _resolve_parent(field, parent_model, item, org):
        """Parent by the device's uuid, or by its server id (public UUID or number)."""
        uuid = item.get(f'{field}_uuid')
        lookup = {'client_uuid': uuid} if uuid else id_lookup(parent_model, item.get(field))
        parent = parent_model.objects.filter(**lookup).first() if lookup else None
        if parent is None or not in_org(f'{field}s', parent, org):
            # Usually the parent failed in this same request; the device retries later
            raise ItemError({field: ['Linked record has not been synced yet.']}, status='pending_parent')
        return parent

    @staticmethod
    def _apply_server_values(name, data, instance, user, resolved):
        """Values the server decides; never trusted from the device."""
        data.pop('created_by', None)
        if name == 'farmers' and instance is None:
            data['organisation'] = ref(user.organisation)

        if name == 'quotations':
            if data.get('insurance_product'):
                lookup = id_lookup(InsuranceProduct, data['insurance_product']) or {'pk': None}
            else:
                lookup = {'pk': getattr(instance, 'insurance_product_id', None)}
            product = InsuranceProduct.objects.filter(
                **lookup, status='ACTIVE', organisation=user.organisation_id).first()
            if product is None:
                raise ItemError({'insurance_product': ['Unknown or inactive insurance product.']})
            data['insurance_product'] = ref(product)
            if 'farm' in resolved:
                farm = resolved['farm']
                if 'farmer' in resolved and resolved['farmer'].pk != farm.farmer_id:
                    raise ItemError({'farm': ["This farm doesn't belong to the selected farmer."]})
                data['farmer'] = ref(farm.farmer)
            sum_insured = data.get('sum_insured', getattr(instance, 'sum_insured', None))
            try:
                premium = Decimal(str(sum_insured)) * product.average_premium_rate / Decimal('100')
            except (InvalidOperation, TypeError):
                raise ItemError({'sum_insured': ['A valid number is required.']})
            data['premium_amount'] = str(premium.quantize(Decimal('0.01')))
            if instance is None:
                data['status'] = 'OPEN'

        if name == 'claims':
            if 'quotation' in resolved:
                quotation = resolved['quotation']
                if 'farmer' in resolved and resolved['farmer'].pk != quotation.farmer_id:
                    raise ItemError({'quotation': ["This policy doesn't belong to the selected farmer."]})
                data['farmer'] = ref(quotation.farmer)
            if instance is None:
                data['status'] = 'OPEN'

        if name == 'inspections' and instance is None:
            data['inspector'] = ref(user)

    @staticmethod
    def _save_farmer_children(farmer, item):
        """Next of kin and bank accounts are sent in full and replace what's stored."""
        if 'next_of_kin' in item:
            farmer.next_of_kin.all().delete()
            for kin in item['next_of_kin'] or []:
                NextOfKin.objects.create(
                    farmer=farmer, name=kin.get('name', ''),
                    relationship=kin.get('relationship', ''), phone_number=kin.get('phone_number', ''),
                )
        if 'bank_accounts' in item:
            farmer.bank_accounts.all().delete()
            for account in item['bank_accounts'] or []:
                BankAccount.objects.create(
                    farmer=farmer, bank_name=account.get('bank_name', ''),
                    account_number=account.get('account_number', ''),
                    account_name=account.get('account_name', ''),
                )

    # ---------------------------------------------------------------- download

    @staticmethod
    def _parse_since(value):
        if not value:
            return None
        parsed = parse_datetime(str(value).replace('Z', '+00:00'))
        if parsed and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)
        return parsed

    def _updates_since(self, since, user):
        org = user.organisation
        querysets = {
            'farmers': Farmer.objects.filter(organisation=org)
                .select_related('organisation', 'country')
                .prefetch_related(
                    Prefetch('farms', queryset=Farm.objects.select_related(*FARM_UNITS_RELATED)),
                    'next_of_kin', 'bank_accounts',
                ),
            'farms': Farm.objects.filter(farmer__organisation=org).select_related('farmer', *FARM_UNITS_RELATED),
            'quotations': Quotation.objects.filter(farmer__organisation=org)
                .select_related('farmer', 'farm', 'insurance_product'),
            'claims': Claim.objects.filter(farmer__organisation=org)
                .select_related('farmer', 'quotation', 'loss_assessor'),
            'inspections': Inspection.objects.filter(farm__farmer__organisation=org)
                .select_related('farm', 'inspector').prefetch_related('photos'),
        }
        updates = {}
        for name, queryset in querysets.items():
            if since is not None:
                queryset = queryset.filter(updated_at__gt=since)
            updates[name] = ENTITIES[name].serializer(queryset, many=True, context={'request': self.request}).data
        return updates

    def _reference_data(self, user, since):
        org = user.organisation
        ctx = {'context': {'request': self.request}}
        reference = {
            'crops': CropSerializer(Crop.objects.filter(organisation=org), many=True, **ctx).data,
            'crop_varieties': CropVarietySerializer(
                CropVariety.objects.filter(organisation=org), many=True, **ctx).data,
            'seasons': SeasonSerializer(Season.objects.filter(organisation=org), many=True, **ctx).data,
            'insurance_products': InsuranceProductSerializer(
                InsuranceProduct.objects.filter(organisation=org, status='ACTIVE')
                .select_related('crop', 'season', 'crop_variety', 'product_category'), many=True, **ctx).data,
            'cover_types': CoverTypeSerializer(
                CoverType.objects.filter(Q(organisation=org) | Q(organisation__isnull=True)), many=True, **ctx).data,
            'product_categories': ProductCategorySerializer(
                ProductCategory.objects.filter(organisation=org), many=True, **ctx).data,
        }
        # The location tree is large, so it is only sent on a first sync or after it changes.
        # Devices replace the whole list when the key is present and keep theirs when it isn't.
        units = AdministrativeUnit.objects.filter(country_id=org.country_id)
        if since is None or units.filter(date_time_modified__gt=since).exists():
            reference['administrative_units'] = list(
                units.filter(is_deleted=False).values('unit_id', 'parent', 'level', 'name')
            )
        return reference
