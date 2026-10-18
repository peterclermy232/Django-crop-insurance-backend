from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission

from insurance.models import Country, OrganizationType, Organization
from insurance.serializers import (
    CountrySerializer,
    OrganizationTypeSerializer,
    OrganizationSerializer,
)
from insurance.scoping import IsPlatformAdminOrReadOnly, OrganisationScopedMixin, is_platform_admin, scope_queryset


class CountryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsPlatformAdminOrReadOnly]
    queryset = Country.objects.filter(country_is_deleted=False)
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only cap the list view; slicing breaks detail lookups (retrieve/update/delete
        # would always 404 because a sliced queryset cannot be filtered).
        if self.action != 'list' or self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]


class OrganizationTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsPlatformAdminOrReadOnly]
    queryset = OrganizationType.objects.all().order_by('-organisation_type_id')
    serializer_class = OrganizationTypeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only cap the list view; slicing breaks detail lookups (retrieve/update/delete
        # would always 404 because a sliced queryset cannot be filtered).
        if self.action != 'list' or self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]


class IsPlatformAdmin(BasePermission):
    message = 'Only a superuser can do this.'

    def has_permission(self, request, view):
        return is_platform_admin(request.user)


class OrganizationViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing organizations.
    Provides CRUD operations: list, retrieve, create, update, partial_update, destroy
    """
    queryset = Organization.objects.filter(organisation_is_deleted=False)
    serializer_class = OrganizationSerializer
    lookup_field = 'organisation_id'

    def get_permissions(self):
        """
        Anyone may list/retrieve (anonymous callers get an empty list, everyone else
        only their own organisation); creating and deleting organisations is for
        platform superusers, and admins may edit their own organisation.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action in ['create', 'destroy']:
            permission_classes = [IsPlatformAdmin]
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