from django.http import Http404
from rest_framework.exceptions import APIException
# insurance/views/claims.py
import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status
from django.utils import timezone
from django.db.models import Count, Sum
from django.db import transaction

from insurance.models import Claim, LossAssessor, ClaimAssignment, Farmer, Quotation
from insurance.serializers import (
    ClaimSerializer, LossAssessorSerializer, ClaimAssignmentSerializer
)
from insurance.public_ids import expose_id, filter_by_id, id_lookup, resolve_pk
from insurance.scoping import OrganisationScopedMixin, is_platform_admin, scope_queryset

logger = logging.getLogger(__name__)


class LossAssessorViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = LossAssessor.objects.all()
    serializer_class = LossAssessorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if (Claim.objects.filter(loss_assessor=instance).exists()
                or ClaimAssignment.objects.filter(loss_assessor=instance).exists()):
            return Response(
                {'detail': 'This loss assessor has claims assigned and cannot be deleted. '
                           'Set the status to INACTIVE instead.'},
                status=http_status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class ClaimViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
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
            queryset = filter_by_id(queryset, 'farmer_id', Farmer, farmer_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create claim with comprehensive error handling"""
        try:
            logger.info(f"📥 Received claim creation request from user: {request.user.user_email}")
            logger.info(f"📦 Request data: {request.data}")

            # Extract and validate data
            data = request.data.copy()

            # Validate required fields
            required_fields = ['farmer', 'quotation', 'estimated_loss_amount']
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                logger.error(f"❌ Missing required fields: {missing_fields}")
                return Response(
                    {
                        'error': 'Missing required fields',
                        'missing_fields': missing_fields,
                        'required_fields': required_fields
                    },
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # Validate farmer exists
            try:
                farmer = scope_queryset(Farmer.objects.all(), request.user).get(**(id_lookup(Farmer, data['farmer']) or {'pk': None}))
                logger.info(f"✅ Farmer found: {farmer.first_name} {farmer.last_name}")
            except Farmer.DoesNotExist:
                logger.error(f"❌ Farmer not found: {data['farmer']}")
                return Response(
                    {'error': f'Farmer with ID {data["farmer"]} not found'},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # Validate quotation exists
            try:
                quotation = scope_queryset(Quotation.objects.all(), request.user).get(**(id_lookup(Quotation, data['quotation']) or {'pk': None}))
                logger.info(f"✅ Quotation found: {quotation.policy_number}")

                # Check quotation status
                if quotation.status not in ['WRITTEN', 'PAID']:
                    logger.error(f"❌ Invalid quotation status: {quotation.status}")
                    return Response(
                        {
                            'error': 'Invalid quotation status',
                            'details': f'Quotation status is {quotation.status}. Must be WRITTEN or PAID.',
                            'quotation_id': expose_id(quotation, request),
                            'current_status': quotation.status
                        },
                        status=http_status.HTTP_400_BAD_REQUEST
                    )

            except Quotation.DoesNotExist:
                logger.error(f"❌ Quotation not found: {data['quotation']}")
                return Response(
                    {'error': f'Quotation with ID {data["quotation"]} not found'},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # Handle loss_details
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

            logger.info(f"📋 Processed loss_details: {data['loss_details']}")

            # Validate and create claim
            serializer = self.get_serializer(data=data)

            if not serializer.is_valid():
                logger.error(f"❌ Validation errors: {serializer.errors}")
                return Response(
                    {
                        'error': 'Validation failed',
                        'details': serializer.errors
                    },
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # Create claim in transaction
            with transaction.atomic():
                self.perform_create(serializer)
                claim = serializer.instance

                logger.info(f"✅ Claim created successfully: {claim.claim_number}")

            headers = self.get_success_headers(serializer.data)
            return Response(
                {
                    'message': 'Claim created successfully',
                    'claim_id': expose_id(claim, request),
                    'claim_number': claim.claim_number,
                    'data': serializer.data
                },
                status=http_status.HTTP_201_CREATED,
                headers=headers
            )

        except (APIException, Http404):
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error creating claim: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': 'Failed to create claim',
                    'details': str(e),
                    'type': type(e).__name__
                },
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update claim with error handling"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()

            data = request.data.copy()

            # Handle loss_details
            if 'loss_details' in data:
                if isinstance(data['loss_details'], str):
                    try:
                        import json
                        data['loss_details'] = json.loads(data['loss_details'])
                    except json.JSONDecodeError:
                        data['loss_details'] = {'description': data['loss_details']}
                elif data['loss_details'] == '' or data['loss_details'] is None:
                    data['loss_details'] = {}

            logger.info(f"🔄 Updating claim {instance.claim_number}")

            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            # Stamp the payment date when a claim is marked PAID without one
            extra = {}
            if (serializer.validated_data.get('status') == 'PAID'
                    and not serializer.validated_data.get('payment_date')
                    and not instance.payment_date):
                extra['payment_date'] = timezone.now()
            serializer.save(**extra)

            return Response(serializer.data)

        except (APIException, Http404):
            # Validation errors / not found keep their proper 4xx status
            raise
        except Exception as e:
            logger.error(f"❌ Error updating claim: {str(e)}", exc_info=True)
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
        assessor_id = resolve_pk(LossAssessor, assessor_id, scope_queryset(LossAssessor.objects.all(), request.user))
        if assessor_id is None:
            return Response({'error': 'Loss assessor not found'}, status=http_status.HTTP_400_BAD_REQUEST)

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

    @action(detail=True, methods=['post'])
    def upload_photo(self, request, pk=None):
        """Upload photo for claim"""
        claim = self.get_object()
        photo = request.FILES.get('photo')

        if not photo:
            return Response(
                {'error': 'No photo provided'},
                status=http_status.HTTP_400_BAD_REQUEST
            )

        from insurance.models.inspection import ClaimPhoto

        claim_photo = ClaimPhoto.objects.create(
            claim=claim,
            photo=photo,
            caption=request.data.get('caption', ''),
            latitude=request.data.get('latitude'),
            longitude=request.data.get('longitude')
        )

        return Response({
            'photo_url': request.build_absolute_uri(claim_photo.photo.url),
            'photo_id': claim_photo.photo_id,
            'message': 'Photo uploaded successfully'
        }, status=http_status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def photos(self, request, pk=None):
        """Get all photos for a claim"""
        claim = self.get_object()
        from insurance.models.inspection import ClaimPhoto
        from insurance.serializers.inspection import ClaimPhotoSerializer

        photos = ClaimPhoto.objects.filter(claim=claim)
        serializer = ClaimPhotoSerializer(photos, many=True, context={'request': request})
        return Response(serializer.data)