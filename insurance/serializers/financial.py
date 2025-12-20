from rest_framework import serializers
from insurance.models import Subsidy, Invoice


class SubsidySerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )
    product_name = serializers.CharField(
        source='insurance_product.product_name',
        read_only=True
    )

    class Meta:
        model = Subsidy
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )
    subsidy_name = serializers.CharField(
        source='subsidy.subsidy_name',
        read_only=True
    )

    class Meta:
        model = Invoice
        fields = '__all__'