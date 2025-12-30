from rest_framework import serializers
from django.contrib.auth import authenticate
from insurance.models import User, Organization, RoleType


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
                raise serializers.ValidationError('Invalid username or password')
            if user.user_status != 'Active':
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
    user_role = serializers.CharField(required=False, default='CUSTOMER')

    def validate_email(self, value):
        if User.objects.filter(user_email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value

    def validate_user_role(self, value):
        """Validate that the role exists and is active"""
        if not value:
            return 'CUSTOMER'
        
        # Convert to uppercase
        role_name = value.upper()
        
        # Check if role exists and is active
        try:
            role = RoleType.objects.get(role_name=role_name, role_status='ACTIVE')
        except RoleType.DoesNotExist:
            raise serializers.ValidationError(
                f'Role "{role_name}" does not exist or is inactive. '
                f'Available roles: SUPERUSER, ADMIN, MANAGER, ASSESSOR, AGENT, USER, CUSTOMER'
            )
        
        return role_name

    def validate(self, data):
        """Additional validation for role-based registration"""
        user_role = data.get('user_role', 'CUSTOMER')
        
        # Optional: Add restrictions on who can register with certain roles
        # For example, prevent public registration as SUPERUSER or ADMIN
        restricted_roles = ['SUPERUSER', 'ADMIN']
        
        if user_role in restricted_roles:
            # Check if request has an admin user
            request = self.context.get('request')
            if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
                raise serializers.ValidationError(
                    f'Cannot register as {user_role}. Admin approval required.'
                )
            
            # Only existing SUPERUSER or ADMIN can create these roles
            if request.user.user_role not in ['SUPERUSER', 'ADMIN']:
                raise serializers.ValidationError(
                    f'Only administrators can register users with {user_role} role.'
                )
        
        return data

    def create(self, validated_data):
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        phone = validated_data.pop("user_phone_number", None)
        org_id = validated_data.pop("organisation_id", None)
        user_role = validated_data.pop("user_role", "CUSTOMER")

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
            user_role=user_role,
            first_name=first_name,
            last_name=last_name,
            user_status='ACTIVE'
        )
        return user

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email", "password",
            "user_phone_number", "organisation_id", "user_role"
        ]