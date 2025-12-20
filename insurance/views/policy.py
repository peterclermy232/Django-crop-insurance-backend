from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Count, Sum

from insurance.models import Quotation, Farmer, InsuranceProduct
from insurance.serializers import (
    QuotationSerializer, FarmerSerializer, InsuranceProductSerializer
)


class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.select_related(
        'farmer', 'farm', 'insurance_product'
    ).all().order_by('-quotation_id')
    serializer_class = QuotationSerializer

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
        """Create quotation with detailed error handling"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e), 'errors': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': f'Error creating quotation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update quotation with detailed error handling"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)
        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e), 'errors': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': f'Error updating quotation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get quotation statistics"""
        total = self.get_queryset().count()
        by_status = self.get_queryset().values('status').annotate(
            count=Count('quotation_id')
        )
        total_premium = self.get_queryset().aggregate(
            total=Sum('premium_amount')
        )['total'] or 0

        return Response({
            'total_quotations': total,
            'by_status': list(by_status),
            'total_premium': float(total_premium)
        })

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark quotation as paid"""
        try:
            quotation = self.get_object()

            if quotation.status == 'PAID':
                return Response(
                    {'error': 'Quotation is already marked as paid'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment_reference = request.data.get('payment_reference')
            if not payment_reference:
                return Response(
                    {'error': 'Payment reference is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            quotation.status = 'PAID'
            quotation.payment_date = timezone.now()
            quotation.payment_reference = payment_reference
            quotation.save()

            return Response(self.get_serializer(quotation).data)
        except Exception as e:
            return Response(
                {'error': f'Failed to mark as paid: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def write_policy(self, request, pk=None):
        """Convert quotation to written policy"""
        try:
            quotation = self.get_object()

            if quotation.status != 'PAID':
                return Response(
                    {'error': 'Quotation must be paid before writing policy'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if quotation.policy_number:
                return Response(
                    {
                        'error': 'Policy already written',
                        'policy_number': quotation.policy_number
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            quotation.status = 'WRITTEN'
            quotation.policy_number = (
                f"POL-{timezone.now().strftime('%Y%m%d')}-{quotation.quotation_id}"
            )
            quotation.save()

            return Response({
                'message': 'Policy written successfully',
                'policy_number': quotation.policy_number,
                'quotation': self.get_serializer(quotation).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to write policy: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return quotations with related data for frontend"""
        quotations = self.get_serializer(self.get_queryset(), many=True).data
        farmers = FarmerSerializer(Farmer.objects.all(), many=True).data
        products = InsuranceProductSerializer(
            InsuranceProduct.objects.filter(status='ACTIVE'),
            many=True
        ).data

        return Response({
            'quotations': quotations,
            'farmers': farmers,
            'insurance_products': products
        })