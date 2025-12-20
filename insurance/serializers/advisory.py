from rest_framework import serializers
from insurance.models import Advisory, WeatherData


class AdvisorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Advisory
        fields = '__all__'


class WeatherDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherData
        fields = '__all__'

    def validate_data_type(self, value):
        """Ensure data_type is uppercase"""
        return value.upper() if value else value

    def validate(self, data):
        """Validate date ranges"""
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError(
                    'End date must be after start date'
                )
        return data