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

    # Add these for better data structure
    farmer_first_name = serializers.CharField(source='farmer.first_name', read_only=True)
    farmer_last_name = serializers.CharField(source='farmer.last_name', read_only=True)
    farmer_id_number = serializers.CharField(source='farmer.id_number', read_only=True)

    class Meta:
        model = Quotation
        fields = '__all__'
        # OR explicitly list all fields:
        # fields = [
        #     'quotation_id', 'farmer', 'farm', 'insurance_product',
        #     'policy_number', 'premium_amount', 'sum_insured', 'status',
        #     'quotation_date', 'payment_date', 'payment_reference',
        #     'farmer_name', 'farm_name', 'product_name',
        #     'farmer_first_name', 'farmer_last_name', 'farmer_id_number'
        # ]

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


class LossAssessorSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.user_name', read_only=True)
    organisation_name = serializers.CharField(source='organisation.organisation_name', read_only=True)

    class Meta:
        model = LossAssessor
        fields = '__all__'


class ClaimSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    policy_number = serializers.CharField(source='quotation.policy_number', read_only=True)
    assessor_name = serializers.SerializerMethodField()
    # Make loss_details optional and handle it properly
    loss_details = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Claim
        fields = '__all__'
        read_only_fields = ('claim_id', 'claim_date', 'approval_date')

    def get_farmer_name(self, obj):
        """Return full farmer name"""
        return f"{obj.farmer.first_name} {obj.farmer.last_name}" if obj.farmer else None

    def get_assessor_name(self, obj):
        """Return assessor name if assigned"""
        return obj.loss_assessor.user.user_name if obj.loss_assessor else None

    def validate_loss_details(self, value):
        """
        Validate loss_details JSON field
        Accepts: dict, None, or valid JSON string
        """
        if value is None:
            return None

        # If it's already a dict, return it
        if isinstance(value, dict):
            return value

        # If it's a string, try to parse it as JSON
        if isinstance(value, str):
            # Handle empty string
            if not value.strip():
                return None

            try:
                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    raise serializers.ValidationError(
                        'loss_details must be a JSON object (dictionary), not a list or other type'
                    )
                return parsed
            except json.JSONDecodeError as e:
                raise serializers.ValidationError(
                    f'Invalid JSON format: {str(e)}'
                )

        # If it's some other type, reject it
        raise serializers.ValidationError(
            'loss_details must be a valid JSON object or dictionary'
        )

    def validate_farmer(self, value):
        """Validate farmer exists and is active"""
        if value and value.status != 'ACTIVE':
            raise serializers.ValidationError('Selected farmer is not active')
        return value

    def validate_quotation(self, value):
        """Validate quotation is a written policy"""
        if value:
            if value.status != 'WRITTEN':
                raise serializers.ValidationError(
                    'Can only create claims for written policies. Current status: ' + value.status
                )
            if not value.policy_number:
                raise serializers.ValidationError('Quotation must have a policy number')
        return value

    def validate_estimated_loss_amount(self, value):
        """Validate estimated loss amount"""
        if value <= 0:
            raise serializers.ValidationError('Estimated loss must be greater than zero')
        return value

    def validate_claim_number(self, value):
        """Validate claim number uniqueness"""
        if value:
            existing = Claim.objects.filter(claim_number=value)
            if self.instance:
                existing = existing.exclude(claim_id=self.instance.claim_id)
            if existing.exists():
                raise serializers.ValidationError('A claim with this number already exists')
        return value

    def validate(self, data):
        """Cross-field validation"""
        # Validate estimated loss doesn't exceed sum insured
        estimated_loss = data.get('estimated_loss_amount')
        quotation = data.get('quotation')

        if estimated_loss and quotation:
            if estimated_loss > quotation.sum_insured:
                raise serializers.ValidationError({
                    'estimated_loss_amount': f'Estimated loss ({estimated_loss}) cannot exceed sum insured ({quotation.sum_insured})'
                })

        return data

    def create(self, validated_data):
        """Override create to auto-generate claim number if not provided"""
        from django.utils import timezone

        if not validated_data.get('claim_number'):
            # Generate claim number: CLM-YYYYMMDD-XXXXXX
            date_str = timezone.now().strftime('%Y%m%d')
            last_claim = Claim.objects.filter(
                claim_number__startswith=f'CLM-{date_str}'
            ).order_by('-claim_id').first()

            if last_claim:
                try:
                    last_num = int(last_claim.claim_number.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            validated_data['claim_number'] = f'CLM-{date_str}-{new_num:06d}'

        # Ensure loss_details is properly set
        if 'loss_details' not in validated_data or validated_data['loss_details'] is None:
            validated_data['loss_details'] = {}

        return super().create(validated_data)

    def to_representation(self, instance):
        """Customize output representation"""
        data = super().to_representation(instance)

        # Ensure loss_details is always a dict in output
        if data.get('loss_details') is None:
            data['loss_details'] = {}

        return data

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

    class WeatherDataSerializer(serializers.ModelSerializer):
        class Meta:
            model = WeatherData
            fields = '__all__'

        def validate_data_type(self, value):
            '''Ensure data_type is uppercase'''
            return value.upper() if value else value

        def validate(self, data):
            '''Validate date ranges'''
            if data.get('start_date') and data.get('end_date'):
                if data['start_date'] > data['end_date']:
                    raise serializers.ValidationError(
                        'End date must be after start date'
                    )
            return data