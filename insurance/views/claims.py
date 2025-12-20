import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status
from django.utils import timezone
from django.db.models import Count, Sum

from insurance.models import Claim, LossAssessor, ClaimAssignment
from insurance.serializers import (
    ClaimSerializer, LossAssessorSerializer, ClaimAssignmentSerializer
)

logger = logging.getLogger(__name__)


class LossAssessorViewSet(viewsets.ModelViewSet):
    queryset = LossAssessor.objects.all()
    serializer_class = LossAssessorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class ClaimViewSet(viewsets.ModelViewSet):
    queryset = Claim.objects.all().order_by('-claim_date')
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        farmer_id = self.request.query_params.get('farmer_id')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if farmer_id:
            queryset = queryset.filter(farmer_id=farmer_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create claim with detailed error handling and logging"""
        try:
            logger.info(f"Attempting to create claim with data: {request.data}")

            data = request.data.copy()

            # Handle loss_details if it's a string
            if 'loss_details' in data:
                if isinstance(data['loss_details'], str):
                    try:
                        import json
                        data['loss_details'] = json.loads(data['loss_details'])
                    except json.JSONDecodeError:
                        data['loss_details'] = {'description': data['loss_details']}
                elif data['loss_details'] == '' or data['loss_details'] is None:
                    data['loss_details'] = {}
            else:
                data['loss_details'] = {}

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            logger.info(
                f"Claim created successfully: {serializer.data.get('claim_number')}"
            )

            headers = self.get_success_headers(serializer.data)
            return Response(
                {
                    'message': 'Claim created successfully',
                    'data': serializer.data
                },
                status=http_status.HTTP_201_CREATED,
                headers=headers
            )

        except Exception as e:
            logger.error(f"Unexpected error creating claim: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': 'Failed to create claim',
                    'details': str(e),
                    'type': type(e).__name__
                },
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update claim with detailed error handling"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()

            data = request.data.copy()
            if 'loss_details' in data:
                if isinstance(data['loss_details'], str):
                    try:
                        import json
                        data['loss_details'] = json.loads(data['loss_details'])
                    except json.JSONDecodeError:
                        data['loss_details'] = {'description': data['loss_details']}
                elif data['loss_details'] == '' or data['loss_details'] is None:
                    data['loss_details'] = {}

            logger.info(f"Updating claim {instance.claim_number}")

            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Unexpected error updating claim: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': 'Failed to update claim',
                    'details': str(e)
                },
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get claim statistics"""
        total = self.get_queryset().count()
        by_status = self.get_queryset().values('status').annotate(
            count=Count('claim_id')
        )
        total_claimed = self.get_queryset().aggregate(
            total=Sum('estimated_loss_amount')
        )['total'] or 0
        total_approved = self.get_queryset().aggregate(
            total=Sum('approved_amount')
        )['total'] or 0

        return Response({
            'total_claims': total,
            'by_status': list(by_status),
            'total_claimed': float(total_claimed),
            'total_approved': float(total_approved)
        })

    @action(detail=True, methods=['post'])
    def assign_assessor(self, request, pk=None):
        """Assign loss assessor to claim"""
        claim = self.get_object()
        assessor_id = request.data.get('assessor_id')

        if not assessor_id:
            return Response(
                {'error': 'Assessor ID required'},
                status=http_status.HTTP_400_BAD_REQUEST
            )

        ClaimAssignment.objects.create(
            claim=claim,
            loss_assessor_id=assessor_id,
            assigned_by=(
                request.user.user_id if hasattr(request.user, 'user_id') else 1
            )
        )

        claim.status = 'UNDER_ASSESSMENT'
        claim.loss_assessor_id = assessor_id
        claim.save()

        return Response(self.get_serializer(claim).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve claim"""
        claim = self.get_object()
        claim.status = 'PENDING_PAYMENT'
        claim.approved_amount = request.data.get('approved_amount')
        claim.approval_date = timezone.now()
        claim.save()

        return Response(self.get_serializer(claim).data)