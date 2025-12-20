from rest_framework import serializers
from django.contrib.auth import authenticate
from insurance.models import User, Organization


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
            "first_name", "last_name", "email", "password",
            "user_phone_number", "organisation_id"
        ]