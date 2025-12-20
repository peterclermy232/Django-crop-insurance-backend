from rest_framework import serializers
from insurance.models import InsuranceProduct, CoverType, ProductCategory


class CoverTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverType
        fields = '__all__'


class ProductCategorySerializer(serializers.ModelSerializer):
    cover_type_name = serializers.CharField(
        source='cover_type.cover_type',
        read_only=True
    )
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )

    class Meta:
        model = ProductCategory
        fields = '__all__'


class InsuranceProductSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )
    product_category_name = serializers.CharField(
        source='product_category.product_category',
        read_only=True
    )
    season_name = serializers.CharField(source='season.season', read_only=True)
    crop_name = serializers.CharField(source='crop.crop', read_only=True)
    crop_variety_name = serializers.CharField(
        source='crop_variety.crop_variety',
        read_only=True
    )

    class Meta:
        model = InsuranceProduct
        fields = '__all__'