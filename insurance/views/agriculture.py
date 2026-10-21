from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from insurance.models import (
    Crop, CropVariety, CoverType, ProductCategory, Season, Organization
)
from insurance.serializers import (
    CropSerializer, CropVarietySerializer, CoverTypeSerializer,
    ProductCategorySerializer, SeasonSerializer, OrganizationSerializer,
)
import django_filters
from insurance.public_ids import filter_by_id
from insurance.scoping import (
    OrganisationScopedMixin, SharedRecordsReadOnly, is_platform_admin, scope_queryset,
)


class PublicIdFilter(django_filters.CharFilter):
    """`?crop=<id>` filter that takes a public UUID or a numeric id."""

    def __init__(self, model, *args, **kwargs):
        self.related_model = model
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        return filter_by_id(qs, f'{self.field_name}_id', self.related_model, value) if value else qs


class CropFilter(django_filters.FilterSet):
    organisation = PublicIdFilter(Organization, field_name='organisation')

    class Meta:
        model = Crop
        fields = ['status']


class CropVarietyFilter(django_filters.FilterSet):
    organisation = PublicIdFilter(Organization, field_name='organisation')
    crop = PublicIdFilter(Crop, field_name='crop')

    class Meta:
        model = CropVariety
        fields = ['status']


class CropViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Crop.objects.filter(deleted=False)
    serializer_class = CropSerializer
    # Query params used by the frontend: ?search=, ?status=true, ?organisation=<id>
    filterset_class = CropFilter
    search_fields = ['crop']

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return crops with organizations"""
        crops = self.get_serializer(self.get_queryset(), many=True).data
        orgs = OrganizationSerializer(
            scope_queryset(Organization.objects.filter(organisation_is_deleted=False), request.user),
            many=True
        ).data

        return Response({
            'cropsResponse': crops,
            'orgsResponse': {'results': orgs}
        })


class CropVarietyViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = CropVariety.objects.filter(deleted=False)
    serializer_class = CropVarietySerializer
    # Query params used by the frontend: ?crop=<id>, ?organisation=<id>, ?status=true, ?search=
    filterset_class = CropVarietyFilter
    search_fields = ['crop_variety', 'crop__crop']

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return crop varieties with crops and organizations"""
        varieties = self.get_serializer(self.get_queryset(), many=True).data
        crops = CropSerializer(scope_queryset(Crop.objects.filter(deleted=False), request.user), many=True).data
        orgs = OrganizationSerializer(
            scope_queryset(Organization.objects.filter(organisation_is_deleted=False), request.user),
            many=True
        ).data

        return Response({
            'cropVarResponse': varieties,
            'cropsResponse': crops,
            'orgsResponse': {'results': orgs}
        })


class CoverTypeViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    """Shared cover types (no organisation) plus the user's organisation's own."""
    permission_classes = [IsAuthenticated, SharedRecordsReadOnly]
    queryset = CoverType.objects.filter(deleted=False)
    serializer_class = CoverTypeSerializer

    def perform_update(self, serializer):
        # Keeps an organisation from turning its cover type into a shared one
        serializer.save(**self.organisation_save_kwargs())


class ProductCategoryViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = ProductCategory.objects.filter(deleted=False)
    serializer_class = ProductCategorySerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return product categories with cover types and organizations"""
        categories = self.get_serializer(self.get_queryset(), many=True).data
        cover_types = CoverTypeSerializer(
            scope_queryset(CoverType.objects.filter(deleted=False), request.user),
            many=True
        ).data
        orgs = OrganizationSerializer(
            scope_queryset(Organization.objects.filter(organisation_is_deleted=False), request.user),
            many=True
        ).data

        return Response({
            'productCategoryResponse': categories,
            'coverTypesResponse': cover_types,
            'organisationsResponse': orgs
        })


class SeasonViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Season.objects.filter(deleted=False)
    serializer_class = SeasonSerializer