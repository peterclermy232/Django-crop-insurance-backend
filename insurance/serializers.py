# serializers.py
from rest_framework import serializers
from .models import *
from django.contrib.auth.hashers import make_password


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class OrganizationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationType
        fields = '__all__'


class OrganizationSerializer(serializers.ModelSerializer):
    organisation_type_name = serializers.CharField(source='organisation_type.organisation_type', read_only=True)
    country_name = serializers.CharField(source='country.country', read_only=True)

    class Meta:
        model = Organization
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)
    country_name = serializers.CharField(source='country.country', read_only=True)
    new_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'user_password': {'write_only': True}
        }

    def create(self, validated_data):
        new_password = validated_data.pop('new_password', None)
        if new_password:
            validated_data['user_password'] = make_password(new_password)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        new_password = validated_data.pop('new_password', None)
        if new_password:
            validated_data['user_password'] = make_password(new_password)
        return super().update(instance, validated_data)


class CropSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)

    class Meta:
        model = Crop
        fields = '__all__'


class CropVarietySerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.crop', read_only=True)
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)

    class Meta:
        model = CropVariety
        fields = '__all__'


class CoverTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverType
        fields = '__all__'


class ProductCategorySerializer(serializers.ModelSerializer):
    cover_type_name = serializers.CharField(source='cover_type.cover_type', read_only=True)
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)

    class Meta:
        model = ProductCategory
        fields = '__all__'


class SeasonSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)

    class Meta:
        model = Season
        fields = '__all__'


class NextOfKinSerializer(serializers.ModelSerializer):
    class Meta:
        model = NextOfKin
        fields = '__all__'


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = '__all__'


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = '__all__'


class FarmerSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)
    country_name = serializers.CharField(source='country.country', read_only=True)
    farms = FarmSerializer(many=True, read_only=True)
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    next_of_kin = NextOfKinSerializer(many=True, read_only=True)

    class Meta:
        model = Farmer
        fields = '__all__'


class InsuranceProductSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)
    product_category_name = serializers.CharField(source='product_category.product_category', read_only=True)
    season_name = serializers.CharField(source='season.season', read_only=True)
    crop_name = serializers.CharField(source='crop.crop', read_only=True)
    crop_variety_name = serializers.CharField(source='crop_variety.crop_variety', read_only=True)

    class Meta:
        model = InsuranceProduct
        fields = '__all__'


class QuotationSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    product_name = serializers.CharField(source='insurance_product.product_name', read_only=True)

    class Meta:
        model = Quotation
        fields = '__all__'

    def get_farmer_name(self, obj):
        return f"{obj.farmer.first_name} {obj.farmer.last_name}"


class LossAssessorSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.user_name', read_only=True)
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)

    class Meta:
        model = LossAssessor
        fields = '__all__'


class ClaimSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    policy_number = serializers.CharField(source='quotation.policy_number', read_only=True)

    class Meta:
        model = Claim
        fields = '__all__'

    def get_farmer_name(self, obj):
        return f"{obj.farmer.first_name} {obj.farmer.last_name}"


class ClaimAssignmentSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    assessor_name = serializers.CharField(source='loss_assessor.user.user_name', read_only=True)

    class Meta:
        model = ClaimAssignment
        fields = '__all__'


class SubsidySerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)
    product_name = serializers.CharField(source='insurance_product.product_name', read_only=True)

    class Meta:
        model = Subsidy
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)
    subsidy_name = serializers.CharField(source='subsidy.subsidy_name', read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class AdvisorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Advisory
        fields = '__all__'


class WeatherDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherData
        fields = '__all__'


# Batch operations serializers
class UserBatchSerializer(serializers.Serializer):
    users = serializers.ListField(child=serializers.DictField())
    organisations = serializers.ListField(child=serializers.DictField())
    countries = serializers.ListField(child=serializers.DictField())