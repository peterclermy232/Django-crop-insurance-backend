from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from insurance.models import Country, OrganizationType, Organization
from insurance.serializers import (
    CountrySerializer,
    OrganizationTypeSerializer,
    OrganizationSerializer,
)


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.filter(country_is_deleted=False)
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]


class OrganizationTypeViewSet(viewsets.ModelViewSet):
    queryset = OrganizationType.objects.all().order_by('-organisation_type_id')
    serializer_class = OrganizationTypeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organizations.
    Provides CRUD operations: list, retrieve, create, update, partial_update, destroy
    """
    queryset = Organization.objects.filter(organisation_is_deleted=False)
    serializer_class = OrganizationSerializer
    lookup_field = 'organisation_id'

    def get_permissions(self):
        """
        Allow unauthenticated access to list and retrieve operations
        Require authentication for create, update, and delete operations
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Custom action to get organizations with additional details"""
        organisations = self.get_queryset()
        serializer = self.get_serializer(organisations, many=True)
        return Response(serializer.data)

    def perform_update(self, serializer):
        """Override to add custom logic on update"""
        serializer.save(
            modified_by=self.request.user.user_id,
            latest_ip=self.request.META.get('REMOTE_ADDR')
        )

    def perform_create(self, serializer):
        """Override to add custom logic on create"""
        serializer.save(
            added_by=self.request.user.user_id,
            source_ip=self.request.META.get('REMOTE_ADDR')
        )