# insurance/views/financial.py
"""
Financial views for Subsidy and Invoice
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Count, Sum

from insurance.models import Subsidy, Invoice
from insurance.serializers import SubsidySerializer, InvoiceSerializer


class SubsidyViewSet(viewsets.ModelViewSet):
    queryset = Subsidy.objects.all().order_by('-subsidy_id')
    serializer_class = SubsidySerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().order_by('-invoice_id')
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        organisation_id = self.request.query_params.get('organisation_id')

        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        if organisation_id:
            queryset = queryset.filter(organisation_id=organisation_id)

        return queryset.order_by('-date_time_added')

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get invoice statistics by status"""
        total = self.get_queryset().count()
        by_status = self.get_queryset().values('status').annotate(
            count=Count('invoice_id')
        )

        total_amount = self.get_queryset().aggregate(
            total=Sum('amount')
        )['total'] or 0

        approved_amount = self.get_queryset().filter(
            status='APPROVED'
        ).aggregate(total=Sum('amount'))['total'] or 0

        settled_amount = self.get_queryset().filter(
            status='SETTLED'
        ).aggregate(total=Sum('amount'))['total'] or 0

        pending_amount = self.get_queryset().filter(
            status='PENDING'
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'total_invoices': total,
            'by_status': list(by_status),
            'total_amount': float(total_amount),
            'approved_amount': float(approved_amount),
            'settled_amount': float(settled_amount),
            'pending_amount': float(pending_amount)
        })

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve invoice - moves from PENDING to APPROVED"""
        try:
            invoice = self.get_object()

            if invoice.status != 'PENDING':
                return Response(
                    {'error': 'Only pending invoices can be approved'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invoice.status = 'APPROVED'
            invoice.approved_date = timezone.now()
            invoice.save()

            return Response({
                'message': 'Invoice approved successfully',
                'invoice': self.get_serializer(invoice).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to approve invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        """Settle invoice - moves from APPROVED to SETTLED"""
        try:
            invoice = self.get_object()

            if invoice.status != 'APPROVED':
                return Response(
                    {'error': 'Only approved invoices can be settled'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment_reference = request.data.get('payment_reference')
            if not payment_reference:
                return Response(
                    {'error': 'Payment reference is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invoice.status = 'SETTLED'
            invoice.settlement_date = timezone.now()
            invoice.payment_reference = payment_reference
            invoice.save()

            return Response({
                'message': 'Invoice settled successfully',
                'invoice': self.get_serializer(invoice).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to settle invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject invoice - moves to REJECTED status"""
        try:
            invoice = self.get_object()

            if invoice.status not in ['PENDING', 'APPROVED']:
                return Response(
                    {'error': 'Cannot reject settled invoices'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            rejection_reason = request.data.get('rejection_reason', '')

            invoice.status = 'REJECTED'
            invoice.payment_reference = f"REJECTED: {rejection_reason}"
            invoice.save()

            return Response({
                'message': 'Invoice rejected successfully',
                'invoice': self.get_serializer(invoice).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to reject invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending invoices"""
        invoices = self.get_queryset().filter(status='PENDING')
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def approved(self, request):
        """Get all approved invoices (ready for settlement)"""
        invoices = self.get_queryset().filter(status='APPROVED')
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def settled(self, request):
        """Get all settled invoices"""
        invoices = self.get_queryset().filter(status='SETTLED')
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        """Approve multiple invoices at once"""
        invoice_ids = request.data.get('invoice_ids', [])

        if not invoice_ids:
            return Response(
                {'error': 'No invoice IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoices = Invoice.objects.filter(
            invoice_id__in=invoice_ids,
            status='PENDING'
        )

        count = invoices.update(
            status='APPROVED',
            approved_date=timezone.now()
        )

        return Response({
            'message': f'{count} invoices approved successfully',
            'count': count
        })

    @action(detail=False, methods=['post'])
    def bulk_settle(self, request):
        """Settle multiple invoices at once"""
        invoice_ids = request.data.get('invoice_ids', [])
        payment_reference = request.data.get('payment_reference')

        if not invoice_ids:
            return Response(
                {'error': 'No invoice IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not payment_reference:
            return Response(
                {'error': 'Payment reference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoices = Invoice.objects.filter(
            invoice_id__in=invoice_ids,
            status='APPROVED'
        )

        count = invoices.update(
            status='SETTLED',
            settlement_date=timezone.now(),
            payment_reference=payment_reference
        )

        return Response({
            'message': f'{count} invoices settled successfully',
            'count': count
        })