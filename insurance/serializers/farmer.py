from rest_framework import serializers
from insurance.models import AdministrativeUnit, Farmer, Farm, NextOfKin, BankAccount
from insurance.serializers.location import AdministrativeUnitBreadcrumbSerializer


class NextOfKinSerializer(serializers.ModelSerializer):
    class Meta:
        model = NextOfKin
        fields = '__all__'


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = '__all__'


class FarmSerializer(serializers.ModelSerializer):
    # Farmer.__str__ returns "first_name last_name"
    farmer_name = serializers.CharField(source='farmer.__str__', read_only=True)
    administrative_unit_name = serializers.CharField(
        source='administrative_unit.name', read_only=True, default=None
    )
    location_unit_name = serializers.CharField(source='location_unit.name', read_only=True, default=None)
    location_country = serializers.SerializerMethodField()
    administrative_unit_path = serializers.SerializerMethodField()
    location_unit_path = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = '__all__'

    @staticmethod
    def _path(unit):
        if unit is None:
            return []
        return AdministrativeUnitBreadcrumbSerializer(unit.ancestors() + [unit], many=True).data

    def get_administrative_unit_path(self, obj):
        return self._path(obj.administrative_unit)

    def get_location_unit_path(self, obj):
        return self._path(obj.location_unit)

    def get_location_country(self, obj):
        unit = obj.administrative_unit or obj.location_unit
        return unit.country_id if unit else None

    def validate(self, attrs):
        farmer = attrs.get('farmer', getattr(self.instance, 'farmer', None))
        branches = {
            'administrative_unit': (AdministrativeUnit.ADMINISTRATIVE_LEVELS, 'a county, sub-county or ward'),
            'location_unit': (AdministrativeUnit.NATIONAL_LEVELS, 'a location or sub-location'),
        }
        counties = {}
        for field, (levels, label) in branches.items():
            unit = attrs.get(field, getattr(self.instance, field, None))
            if unit is None:
                continue
            if unit.level not in levels:
                raise serializers.ValidationError({field: f'Choose {label}.'})
            if farmer is not None and farmer.country_id and unit.country_id != farmer.country_id:
                raise serializers.ValidationError({field: "This location is not in the farmer's country."})
            chain = unit.ancestors() + [unit]
            counties[field] = chain[0].pk
        if len(set(counties.values())) > 1:
            raise serializers.ValidationError({'location_unit': 'The location must be in the same county as the ward.'})
        return attrs


class FarmerSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )
    country_name = serializers.CharField(source='country.country', read_only=True)
    farms = FarmSerializer(many=True, read_only=True)
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    next_of_kin = NextOfKinSerializer(many=True, read_only=True)

    class Meta:
        model = Farmer
        fields = '__all__'