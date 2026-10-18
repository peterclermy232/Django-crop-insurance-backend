from rest_framework import serializers
from insurance.models import AdministrativeUnit


class AdministrativeUnitSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='country.country', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    has_children = serializers.SerializerMethodField()

    class Meta:
        model = AdministrativeUnit
        fields = [
            'unit_id', 'country', 'country_name', 'parent', 'parent_name',
            'level', 'level_display', 'name', 'code', 'has_children',
        ]

    def get_has_children(self, obj):
        # Annotated in the view's queryset to avoid one query per row
        if hasattr(obj, 'children_count'):
            return obj.children_count > 0
        return obj.children.filter(is_deleted=False).exists()

    def validate(self, attrs):
        parent = attrs.get('parent', getattr(self.instance, 'parent', None))
        country = attrs.get('country', getattr(self.instance, 'country', None))
        if parent is not None and country is not None and parent.country_id != country.pk:
            raise serializers.ValidationError({'parent': 'Parent unit belongs to a different country.'})
        if parent is not None and self.instance is not None:
            node = parent
            while node is not None:
                if node.pk == self.instance.pk:
                    raise serializers.ValidationError({'parent': 'A unit cannot be placed under itself.'})
                node = node.parent
        return attrs


class AdministrativeUnitBreadcrumbSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source='get_level_display', read_only=True)

    class Meta:
        model = AdministrativeUnit
        fields = ['unit_id', 'level', 'level_display', 'name']
