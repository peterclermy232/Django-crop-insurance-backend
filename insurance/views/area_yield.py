import django_filters
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from insurance.area_yield import calculate_payouts
from insurance.models import AreaYield, Crop, Season
from insurance.public_ids import expose_id
from insurance.scoping import OrganisationScopedMixin, is_platform_admin
from insurance.serializers.area_yield import AreaYieldSerializer
from insurance.views.agriculture import PublicIdFilter

YIELD_MANAGERS = ('SUPERUSER', 'ADMIN')


def can_manage_yields(user):
    return is_platform_admin(user) or getattr(user, 'user_role', None) in YIELD_MANAGERS


class CanManageAreaYields(BasePermission):
    """Everyone signed in can read area yields; admins enter, approve and pay them out."""
    message = 'Only an admin can enter, approve or pay out area yields.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or can_manage_yields(request.user)


class AreaYieldFilter(django_filters.FilterSet):
    crop = PublicIdFilter(Crop, field_name='crop')
    season = PublicIdFilter(Season, field_name='season')

    class Meta:
        model = AreaYield
        fields = ['status', 'administrative_unit']


class AreaYieldViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    """
    Expected and actual yields per crop, season and area. Flow:
    enter (DRAFT) -> approve by a second admin (APPROVED) -> calculate payouts (creates claims).
    """
    queryset = (AreaYield.objects
                .select_related('crop', 'season', 'administrative_unit', 'entered_by', 'approved_by')
                .order_by('-area_yield_id'))
    serializer_class = AreaYieldSerializer
    permission_classes = [CanManageAreaYields]
    # Query params used by the frontend: ?page=, ?page_size=, ?search=, ?status=, ?crop=, ?season=
    filterset_class = AreaYieldFilter
    search_fields = ['administrative_unit__name', 'crop__crop', 'season__season', 'source']

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user, **self.organisation_save_kwargs())

    def update(self, request, *args, **kwargs):
        if self.get_object().status == AreaYield.APPROVED:
            return Response({'detail': 'This area yield is approved and can no longer be changed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        # Whoever last changed the figures counts as the one who entered them
        serializer.save(entered_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().status == AreaYield.APPROVED:
            return Response({'detail': 'This area yield is approved and cannot be deleted.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        area_yield = self.get_object()
        if area_yield.status == AreaYield.APPROVED:
            return Response({'detail': 'This area yield is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        if area_yield.actual_yield is None:
            return Response({'detail': 'Enter the actual yield before approving.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if area_yield.entered_by_id == request.user.pk:
            return Response({'detail': 'A different admin must approve the figures you entered.'},
                            status=status.HTTP_403_FORBIDDEN)
        area_yield.status = AreaYield.APPROVED
        area_yield.approved_by = request.user
        area_yield.approved_at = timezone.now()
        area_yield.save(update_fields=['status', 'approved_by', 'approved_at', 'date_time_modified'])
        return Response(self.get_serializer(area_yield).data)

    @action(detail=True, methods=['post'])
    def calculate_payouts(self, request, pk=None):
        """`{"preview": true}` only shows the payouts; without it, claims are created."""
        area_yield = self.get_object()
        if area_yield.status != AreaYield.APPROVED:
            return Response({'detail': 'Approve the area yield before calculating payouts.'},
                            status=status.HTTP_400_BAD_REQUEST)
        preview = str(request.data.get('preview', '')).lower() in ('true', '1')
        result = calculate_payouts(area_yield, request.user, commit=not preview)
        for row in result['rows']:
            row['quotation'] = expose_id(row['quotation'], request)
        result['preview'] = preview
        result['area_yield'] = self.get_serializer(area_yield).data
        return Response(result, status=status.HTTP_200_OK if preview else status.HTTP_201_CREATED)
