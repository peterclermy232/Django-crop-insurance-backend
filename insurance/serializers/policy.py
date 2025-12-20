from rest_framework import serializers
from django.utils import timezone
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

    class Meta:
        model = Quotation
        fields = '__all__'

    def get_farmer_name(self, obj):
        """Return full farmer name"""
        return f"{obj.farmer.first_name} {obj.farmer.last_name}"

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

        return data

    def create(self, validated_data):
        """Create quotation with auto-generated policy number if status is WRITTEN"""
        quotation = super().create(validated_data)

        if quotation.status == 'WRITTEN' and not quotation.policy_number:
            quotation.policy_number = f"POL-{timezone.now().strftime('%Y%m%d')}-{quotation.quotation_id}"
            quotation.save()

        return quotation