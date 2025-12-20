from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum

from insurance.models import Farmer, Quotation, Claim


class DashboardViewSet(viewsets.ViewSet):
    """Dashboard statistics endpoint"""

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get overall dashboard statistics"""
        today = timezone.now().date()

        # Farmer statistics
        total_farmers = Farmer.objects.count()
        active_farmers = Farmer.objects.filter(status='ACTIVE').count()

        # Quotation statistics
        total_quotations = Quotation.objects.count()
        open_quotations = Quotation.objects.filter(status='OPEN').count()
        paid_quotations = Quotation.objects.filter(status='PAID').count()
        written_policies = Quotation.objects.filter(status='WRITTEN').count()

        # Claim statistics
        total_claims = Claim.objects.count()
        open_claims = Claim.objects.filter(status='OPEN').count()
        pending_payment_claims = Claim.objects.filter(
            status='PENDING_PAYMENT'
        ).count()
        paid_claims = Claim.objects.filter(status='PAID').count()

        # Financial statistics
        total_premium = Quotation.objects.aggregate(
            total=Sum('premium_amount')
        )['total'] or 0
        total_claims_value = Claim.objects.aggregate(
            total=Sum('approved_amount')
        )['total'] or 0

        return Response({
            'farmers': {
                'total': total_farmers,
                'active': active_farmers
            },
            'quotations': {
                'total': total_quotations,
                'open': open_quotations,
                'paid': paid_quotations,
                'written': written_policies
            },
            'claims': {
                'total': total_claims,
                'open': open_claims,
                'pending_payment': pending_payment_claims,
                'paid': paid_claims
            },
            'financials': {
                'total_premium': float(total_premium),
                'total_claims_value': float(total_claims_value)
            }
        })