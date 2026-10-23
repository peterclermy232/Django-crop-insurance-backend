from rest_framework import serializers
from django.utils import timezone
from insurance.area_yield import basis_risk_notice, unit_at_level
from insurance.models import Quotation


class QuotationSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    product_name = serializers.CharField(
        source='insurance_product.product_name',
        read_only=True
    )

    # Add these for better data structure
    farmer_first_name = serializers.CharField(
        source='farmer.first_name',
        read_only=True
    )
    farmer_last_name = serializers.CharField(
        source='farmer.last_name',
        read_only=True
    )
    farmer_id_number = serializers.CharField(
        source='farmer.id_number',
        read_only=True
    )
    farm_size = serializers.DecimalField(
        source='farm.farm_size',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    unit_of_measure = serializers.CharField(
        source='farm.unit_of_measure',
        read_only=True
    )
    calculation_method = serializers.CharField(
        source='insurance_product.product_category.cover_type.calculation_method',
        read_only=True
    )
    # Shown to the farmer before buying an area yield policy
    basis_risk_notice = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = '__all__'

    def get_farmer_name(self, obj):
        """Return full farmer name"""
        return f"{obj.farmer.first_name} {obj.farmer.last_name}"

    def get_basis_risk_notice(self, obj):
        return basis_risk_notice(obj.insurance_product)

    def validate(self, data):
        """Validate quotation data"""
        # Ensure premium and sum_insured are positive
        if data.get('premium_amount') and data['premium_amount'] <= 0:
            raise serializers.ValidationError({
                'premium_amount': 'Premium amount must be greater than 0'
            })

        if data.get('sum_insured') and data['sum_insured'] <= 0:
            raise serializers.ValidationError({
                'sum_insured': 'Sum insured must be greater than 0'
            })

        # Verify farm belongs to farmer
        if 'farm' in data and 'farmer' in data:
            if data['farm'].farmer_id != data['farmer'].farmer_id:
                raise serializers.ValidationError({
                    'farm': 'Selected farm does not belong to the selected farmer'
                })

        # Area yield policies are paid by the farm's area, so the farm must be in one
        product = data.get('insurance_product') or getattr(self.instance, 'insurance_product', None)
        farm = data.get('farm') or getattr(self.instance, 'farm', None)
        if product and farm and product.is_area_yield and product.area_level:
            if unit_at_level(farm.administrative_unit, product.area_level) is None:
                raise serializers.ValidationError({
                    'farm': f'{product.product_name} pays by {product.get_area_level_display().lower()}. '
                            f'Set the farm\'s {product.get_area_level_display().lower()} before selling it.'
                })

        return data

    def create(self, validated_data):
        """Create quotation with auto-generated policy number if status is WRITTEN"""
        quotation = super().create(validated_data)

        if quotation.status == 'WRITTEN' and not quotation.policy_number:
            quotation.policy_number = f"POL-{timezone.now().strftime('%Y%m%d')}-{quotation.quotation_id}"
            quotation.save()

        return quotation