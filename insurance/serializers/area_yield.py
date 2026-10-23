from rest_framework import serializers

from insurance.models import AreaYield

AREA_LEVELS = ('WARD', 'SUB_COUNTY', 'COUNTY')


class AreaYieldSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.crop', read_only=True)
    season_name = serializers.CharField(source='season.season', read_only=True)
    unit_name = serializers.CharField(source='administrative_unit.name', read_only=True)
    unit_level = serializers.CharField(source='administrative_unit.level', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.user_name', read_only=True, default=None)
    approved_by_name = serializers.CharField(source='approved_by.user_name', read_only=True, default=None)

    class Meta:
        model = AreaYield
        fields = '__all__'
        read_only_fields = ('organisation', 'status', 'entered_by', 'approved_by', 'approved_at',
                            'payouts_calculated_at')

    def validate(self, data):
        crop = data.get('crop') or getattr(self.instance, 'crop', None)
        season = data.get('season') or getattr(self.instance, 'season', None)
        unit = data.get('administrative_unit') or getattr(self.instance, 'administrative_unit', None)
        if crop and season and crop.organisation_id != season.organisation_id:
            raise serializers.ValidationError({'season': 'The crop and season must belong to the same organisation.'})
        if unit and unit.level not in AREA_LEVELS:
            raise serializers.ValidationError({'administrative_unit': 'Pick a ward, sub-county or county.'})
        if data.get('expected_yield') is not None and data['expected_yield'] <= 0:
            raise serializers.ValidationError({'expected_yield': 'Expected yield must be more than 0.'})
        if data.get('actual_yield') is not None and data['actual_yield'] < 0:
            raise serializers.ValidationError({'actual_yield': 'Actual yield cannot be negative.'})
        if crop:
            # The yield belongs to whoever owns the crop
            data['organisation'] = crop.organisation
        return data
