from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from insurance.models import AdministrativeUnit
from insurance.serializers.location import (
    AdministrativeUnitSerializer,
    AdministrativeUnitBreadcrumbSerializer,
)


class AdministrativeUnitViewSet(viewsets.ModelViewSet):
    """
    Cascading location lookup. Under each county there are two branches:
    Sub-County -> Ward (county government) and Location -> Sub-Location (national government).

    GET /administrative_units/?country=<id>   top-level units (counties) of a country
    GET /administrative_units/?parent=<id>    units directly under a unit
    GET /administrative_units/<id>/children/  same as ?parent=<id>
    GET /administrative_units/<id>/path/      the unit and everything above it
    Optional: ?level=SUB_COUNTY (e.g. ?parent=<county>&level=LOCATION picks one branch), ?search=<name>
    """
    serializer_class = AdministrativeUnitSerializer
    pagination_class = None  # dropdowns need the full list for a parent
    search_fields = ['name', 'code']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'children', 'path', 'levels']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = (
            AdministrativeUnit.objects.filter(is_deleted=False)
            .select_related('country', 'parent')
            .annotate(children_count=Count('children', filter=Q(children__is_deleted=False)))
            .order_by('name')  # Meta.ordering is dropped on aggregate queries
        )
        if self.action != 'list':
            return queryset

        params = self.request.query_params
        parent = params.get('parent')
        country = params.get('country')
        level = params.get('level')

        if parent:
            queryset = queryset.filter(parent_id=parent)
        elif country and not level and not params.get('search'):
            # Choosing a country with no other filter returns its top level only
            queryset = queryset.filter(parent__isnull=True)
        if country:
            queryset = queryset.filter(country_id=country)
        if level:
            queryset = queryset.filter(level=level.upper())
        return queryset

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        queryset = self.get_queryset().filter(parent_id=pk)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=['get'])
    def path(self, request, pk=None):
        unit = self.get_object()
        chain = unit.ancestors() + [unit]
        return Response({
            'country': {'country_id': unit.country_id, 'country': unit.country.country},
            'path': AdministrativeUnitBreadcrumbSerializer(chain, many=True).data,
        })

    @action(detail=False, methods=['get'])
    def levels(self, request):
        return Response([{'value': v, 'label': l} for v, l in AdministrativeUnit.LEVEL_CHOICES])

    def perform_create(self, serializer):
        serializer.save(
            added_by=self.request.user.user_id,
            source_ip=self.request.META.get('REMOTE_ADDR'),
        )

    def perform_update(self, serializer):
        serializer.save(
            modified_by=self.request.user.user_id,
            latest_ip=self.request.META.get('REMOTE_ADDR'),
        )

    def perform_destroy(self, instance):
        # Soft delete, consistent with countries/organisations
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'date_time_modified'])
