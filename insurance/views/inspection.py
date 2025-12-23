from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count

from insurance.models.inspection import Inspection, InspectionPhoto, ClaimPhoto
from insurance.serializers.inspection import (
    InspectionSerializer, InspectionPhotoSerializer, ClaimPhotoSerializer
)


class InspectionViewSet(viewsets.ModelViewSet):
    queryset = Inspection.objects.all()
    serializer_class = InspectionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        inspector_id = self.request.query_params.get('inspector_id')
        status_filter = self.request.query_params.get('status')
        farm_id = self.request.query_params.get('farm_id')

        if inspector_id:
            queryset = queryset.filter(inspector_id=inspector_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)

        return queryset.select_related('farm', 'inspector')

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Record inspector check-in at farm"""
        inspection = self.get_object()

        if inspection.status != 'SCHEDULED':
            return Response(
                {'error': f'Cannot check in to {inspection.status.lower()} inspection'},
                status=status.HTTP_400_BAD_REQUEST
            )

        inspection.status = 'IN_PROGRESS'
        inspection.check_in_time = timezone.now()
        inspection.check_in_latitude = request.data.get('latitude')
        inspection.check_in_longitude = request.data.get('longitude')
        inspection.save()

        return Response({
            'message': 'Checked in successfully',
            'inspection': self.get_serializer(inspection).data
        })

    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """Record inspector check-out from farm"""
        inspection = self.get_object()

        if inspection.status != 'IN_PROGRESS':
            return Response(
                {'error': 'Can only check out from in-progress inspections'},
                status=status.HTTP_400_BAD_REQUEST
            )

        inspection.status = 'COMPLETED'
        inspection.completed_at = timezone.now()
        inspection.check_out_time = timezone.now()
        inspection.check_out_latitude = request.data.get('latitude')
        inspection.check_out_longitude = request.data.get('longitude')
        inspection.findings = request.data.get('findings', {})
        inspection.recommendations = request.data.get('recommendations', '')
        inspection.save()

        return Response({
            'message': 'Checked out successfully',
            'inspection': self.get_serializer(inspection).data
        })

    @action(detail=True, methods=['post'])
    def upload_photo(self, request, pk=None):
        """Upload photo for inspection"""
        inspection = self.get_object()
        photo = request.FILES.get('photo')

        if not photo:
            return Response(
                {'error': 'No photo provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        inspection_photo = InspectionPhoto.objects.create(
            inspection=inspection,
            photo=photo,
            caption=request.data.get('caption', ''),
            latitude=request.data.get('latitude'),
            longitude=request.data.get('longitude')
        )

        return Response(
            InspectionPhotoSerializer(inspection_photo, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def my_inspections(self, request):
        """Get inspections assigned to current user"""
        inspections = self.get_queryset().filter(inspector=request.user)
        serializer = self.get_serializer(inspections, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get inspection statistics"""
        queryset = self.get_queryset()

        stats = {
            'total': queryset.count(),
            'by_status': dict(queryset.values_list('status').annotate(Count('inspection_id'))),
            'by_type': dict(queryset.values_list('inspection_type').annotate(Count('inspection_id'))),
        }

        return Response(stats)