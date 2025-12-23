from rest_framework import serializers
from insurance.models.inspection import Inspection, InspectionPhoto, ClaimPhoto


class InspectionPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionPhoto
        fields = '__all__'


class InspectionSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    inspector_name = serializers.CharField(source='inspector.user_name', read_only=True)
    photos = InspectionPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Inspection
        fields = '__all__'
        read_only_fields = ('inspection_id', 'completed_at', 'verified_at')


class ClaimPhotoSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ClaimPhoto
        fields = '__all__'
        read_only_fields = ('photo_id', 'uploaded_at')

    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None
