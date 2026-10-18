import uuid

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField


def has_public_id(model):
    return any(f.name == 'public_id' for f in model._meta.concrete_fields)


def numeric_ids_allowed():
    return getattr(settings, 'ALLOW_NUMERIC_IDS', True)


def wants_uuid(request):
    if request is None:
        return getattr(settings, 'PUBLIC_IDS_DEFAULT', 'numeric') == 'uuid'
    requested = (request.headers.get('X-Id-Format') or request.GET.get('id_format') or '').lower()
    if requested in ('uuid', 'numeric'):
        return requested == 'uuid' or not numeric_ids_allowed()
    return getattr(settings, 'PUBLIC_IDS_DEFAULT', 'numeric') == 'uuid'


def parse_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def id_lookup(model, value):
    """
    Filter kwargs that find `value` (a UUID or, while allowed, a number) on `model`,
    or None when the value can't be an id of it.
    """
    if value is None or value == '':
        return None
    if has_public_id(model):
        public_id = parse_uuid(value)
        if public_id is not None:
            return {'public_id': public_id}
    if (numeric_ids_allowed() or not has_public_id(model)) and str(value).isdigit():
        return {'pk': int(value)}
    return None


def resolve_pk(model, value, queryset=None):
    """Numeric primary key for a public or numeric id, or None if there is no such record."""
    lookup = id_lookup(model, value)
    if lookup is None:
        return None
    if list(lookup) == ['pk'] and queryset is None:
        return lookup['pk']
    qs = queryset if queryset is not None else model._default_manager.all()
    return qs.filter(**lookup).values_list('pk', flat=True).first()


def filter_by_id(queryset, field, model, value):
    """`queryset.filter(<field>=<id>)` where the id may be public; no match if it can't resolve."""
    pk = resolve_pk(model, value)
    return queryset.filter(**{field: pk}) if pk is not None else queryset.none()


def expose_id(obj, request):
    """The id to put in a hand-built response: the public UUID or the number, per request."""
    if has_public_id(type(obj)) and wants_uuid(request):
        return str(obj.public_id)
    return obj.pk


class PublicIdRelatedField(PrimaryKeyRelatedField):
    """Relation field that accepts a public UUID or numeric id, and returns either per request."""

    def _related_model(self):
        queryset = self.get_queryset()
        if queryset is not None:
            return queryset.model
        # Read-only relations have no queryset; take the model from the serializer's model field
        parent_model = getattr(getattr(self.parent, 'Meta', None), 'model', None)
        try:
            return parent_model._meta.get_field(self.source).related_model
        except Exception:
            return None

    def _uuid_mode(self):
        model = self._related_model()
        return model is not None and has_public_id(model) and wants_uuid(self.context.get('request'))

    def use_pk_only_optimization(self):
        return not self._uuid_mode()

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        lookup = id_lookup(queryset.model, data)
        if lookup is None:
            self.fail('incorrect_type', data_type=type(data).__name__)
        try:
            return queryset.get(**lookup)
        except queryset.model.DoesNotExist:
            self.fail('does_not_exist', pk_value=data)

    def to_representation(self, value):
        if self._uuid_mode():
            return str(value.public_id)
        return value.pk


def _model_to_representation(original):
    def to_representation(self, instance):
        data = original(self, instance)
        model = getattr(getattr(self, 'Meta', None), 'model', None)
        if (model is not None and has_public_id(model) and isinstance(instance, model)
                and wants_uuid(self.context.get('request'))):
            pk_name = model._meta.pk.name
            if pk_name in data:
                data[pk_name] = str(instance.public_id)
        return data
    return to_representation


def install():
    """Called from AppConfig.ready(): every ModelSerializer understands public ids."""
    serializers.ModelSerializer.serializer_related_field = PublicIdRelatedField
    if not getattr(serializers.ModelSerializer.to_representation, '_public_ids', False):
        patched = _model_to_representation(serializers.ModelSerializer.to_representation)
        patched._public_ids = True
        serializers.ModelSerializer.to_representation = patched


class PublicIdLookupMixin:
    """Detail URLs take the public UUID (and, while allowed, the numeric id)."""

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = id_lookup(queryset.model, self.kwargs[url_kwarg])
        if lookup is None:
            raise Http404
        obj = get_object_or_404(queryset, **lookup)
        self.check_object_permissions(self.request, obj)
        return obj
