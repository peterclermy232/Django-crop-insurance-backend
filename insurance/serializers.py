# serializers.py
from rest_framework import serializers
from .models import *
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Organization, Country


class LoginSerializer(serializers.Serializer):
    username = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )

            if not user:
                raise serializers.ValidationError('Invalide username or password')
            if user.user_status !='Active':
                raise serializers.ValidationError('User account is not active')
            data['user'] = user
            return data
        else:
            raise serializers.ValidationError('Must include "username" and "password"')

class RegistrationSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    user_phone_number = serializers.CharField(required=False, allow_blank=True)
    organisation_id = serializers.IntegerField(required=False)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(user_email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value

    def create(self, validated_data):
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        phone = validated_data.pop("user_phone_number", None)
        org_id = validated_data.pop("organisation_id", None)
        try:
            if not org_id:
                default_org = Organization.objects.get(organisation_code="DEFAULT")
            else:
                default_org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            raise serializers.ValidationError(
                'System not properly configured. Please run: python manage.py seed_data'
            )

        user = User.objects.create_user(
            user_email=validated_data['email'],
            user_name=f"{first_name} {last_name}",
            password=validated_data['password'],
            user_phone_number=phone,
            organisation=default_org,
            user_role='CUSTOMER'
        )
        return user

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "user_email", "password",
            "user_phone_number", "organisation_id"
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)
    country_name = serializers.CharField(source='country.country', read_only=True)

    class Meta:
        model = User
        fields = [
            'user_id', 'user_name', 'user_email', 'user_phone_number',
            'user_role', 'user_status', 'organisation_name',
            'country_name', 'date_time_added'
        ]
        read_only_fields = fields

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