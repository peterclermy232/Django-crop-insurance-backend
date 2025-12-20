from rest_framework import serializers
from insurance.models import Crop, CropVariety, Season


class CropSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )

    class Meta:
        model = Crop
        fields = '__all__'


class CropVarietySerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.crop', read_only=True)
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )

    class Meta:
        model = CropVariety
        fields = '__all__'


class SeasonSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )

    class Meta:
        model = Season
        fields = '__all__'