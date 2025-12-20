from rest_framework import serializers
from insurance.models import Country, OrganizationType, Organization


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class OrganizationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationType
        fields = '__all__'


class OrganizationSerializer(serializers.ModelSerializer):
    organisation_type_name = serializers.CharField(
        source='organisation_type.organisation_type',
        read_only=True
    )
    country_name = serializers.CharField(
        source='country.country',
        read_only=True
    )

    class Meta:
        model = Organization
        fields = '__all__'