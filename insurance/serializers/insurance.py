from rest_framework import serializers
from insurance.models import InsuranceProduct, CoverType, ProductCategory


class CoverTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverType
        fields = '__all__'

    def validate_calculation_method(self, value):
        # Products and claims already rely on how this cover pays out
        if (self.instance and value != self.instance.calculation_method
                and ProductCategory.objects.filter(cover_type=self.instance).exists()):
            raise serializers.ValidationError(
                'Product categories already use this cover type, so its calculation method cannot change.')
        return value


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
    cover_type_name = serializers.CharField(
        source='product_category.cover_type.cover_type',
        read_only=True
    )
    calculation_method = serializers.CharField(
        source='product_category.cover_type.calculation_method',
        read_only=True
    )

    class Meta:
        model = InsuranceProduct
        fields = '__all__'

    def validate(self, data):
        category = data.get('product_category') or getattr(self.instance, 'product_category', None)
        if category is None or category.cover_type.calculation_method != CoverType.AREA_YIELD:
            return data

        def value(field):
            return data[field] if field in data else getattr(self.instance, field, None)

        errors = {}
        for field, label in (('area_level', 'Area level'), ('coverage_level', 'Coverage level'),
                             ('yield_unit', 'Yield unit')):
            if value(field) in (None, ''):
                errors[field] = f'{label} is required for area yield products.'
        coverage = value('coverage_level')
        if coverage is not None and not 0 < coverage <= 100:
            errors['coverage_level'] = 'Coverage level must be more than 0 and at most 100 (%).'
        max_payout = value('max_payout_percent')
        if max_payout is not None and not 0 < max_payout <= 100:
            errors['max_payout_percent'] = 'Maximum payout must be more than 0 and at most 100 (%).'
        if errors:
            raise serializers.ValidationError(errors)
        return data