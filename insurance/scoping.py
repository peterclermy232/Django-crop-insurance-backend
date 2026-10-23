from django.db.models import Q
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.relations import ManyRelatedField, RelatedField
from rest_framework.serializers import ListSerializer

from insurance.public_ids import PublicIdLookupMixin

from insurance.models import (
    Advisory, AreaYield, BankAccount, Claim, ClaimAssignment, CoverType, Crop, CropVariety, Farm, Farmer, InsuranceProduct,
    Invoice, LossAssessor, NextOfKin, Organization, ProductCategory, Quotation,
    Season, Subsidy, User,
)
from insurance.models.inspection import ClaimPhoto, Inspection, InspectionPhoto

# Model -> lookup from the model to the owning organisation's id.
# Models not listed (countries, organisation types, locations, weather) are
# platform-wide reference data: everyone reads them, only superusers change them.
# Roles are handled in RoleTypeViewSet: system roles are shared, custom roles per organisation.
ORG_PATHS = {
    Organization: 'organisation_id',
    Advisory: 'organisation_id',
    AreaYield: 'organisation_id',
    CoverType: 'organisation_id',
    User: 'organisation_id',
    Crop: 'organisation_id',
    CropVariety: 'organisation_id',
    Season: 'organisation_id',
    ProductCategory: 'organisation_id',
    InsuranceProduct: 'organisation_id',
    Subsidy: 'organisation_id',
    Invoice: 'organisation_id',
    LossAssessor: 'organisation_id',
    Farmer: 'organisation_id',
    NextOfKin: 'farmer__organisation_id',
    BankAccount: 'farmer__organisation_id',
    Farm: 'farmer__organisation_id',
    Quotation: 'farmer__organisation_id',
    Claim: 'farmer__organisation_id',
    ClaimAssignment: 'claim__farmer__organisation_id',
    ClaimPhoto: 'claim__farmer__organisation_id',
    Inspection: 'farm__farmer__organisation_id',
    InspectionPhoto: 'inspection__farm__farmer__organisation_id',
}

# Models whose records without an organisation are shared: every organisation sees them,
# only superusers change them (see SharedRecordsReadOnly).
SHARED_WHEN_UNOWNED = {CoverType}


def is_platform_admin(user):
    return bool(user and user.is_authenticated
                and (user.is_superuser or getattr(user, 'user_role', None) == 'SUPERUSER'))


class IsPlatformAdminOrReadOnly(BasePermission):
    """Shared reference data: any signed-in user may read it, only superusers change it."""
    message = 'Only a superuser can change shared reference data.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return is_platform_admin(request.user)


class SharedRecordsReadOnly(BasePermission):
    """Records without an organisation are shared by everyone, so only a superuser may change them."""
    message = 'Only a superuser can change shared reference data.'

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.organisation_id is not None or is_platform_admin(request.user)


def scope_queryset(queryset, user):
    """Restricts an organisation-owned queryset to the user's organisation."""
    path = ORG_PATHS.get(queryset.model)
    if path is None or is_platform_admin(user):
        return queryset
    if not (user and user.is_authenticated):
        return queryset.none()
    own = Q(**{path: user.organisation_id})
    if queryset.model in SHARED_WHEN_UNOWNED:
        own |= Q(**{path: None})
    return queryset.filter(own)


def restrict_relation_fields(serializer, user):
    """Makes relation fields reject ids that belong to another organisation."""
    if isinstance(serializer, ListSerializer) or is_platform_admin(user):
        return
    for name, field in serializer.fields.items():
        if isinstance(field, ManyRelatedField):
            field = field.child_relation
        if isinstance(field, RelatedField) and not field.read_only and field.queryset is not None:
            field.queryset = scope_queryset(field.queryset, user)
            if name == 'organisation':
                # Filled in with the user's organisation on save (see organisation_save_kwargs)
                field.required = False


class OrganisationScopedMixin(PublicIdLookupMixin):
    def get_queryset(self):
        return scope_queryset(super().get_queryset(), self.request.user)

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        restrict_relation_fields(serializer, self.request.user)
        return serializer

    def organisation_save_kwargs(self):
        """New records of models owned directly by an organisation belong to the user's."""
        model = self.get_queryset().model
        user = self.request.user
        if ORG_PATHS.get(model) == 'organisation_id' and model is not Organization and not is_platform_admin(user):
            return {'organisation': user.organisation}
        return {}

    def perform_create(self, serializer):
        serializer.save(**self.organisation_save_kwargs())
