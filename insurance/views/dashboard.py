from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum

from insurance.models import Farmer, Quotation, Claim
from insurance.scoping import scope_queryset


class DashboardViewSet(viewsets.ViewSet):
    """Dashboard statistics endpoint"""

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get overall dashboard statistics"""
        today = timezone.now().date()
        farmers = scope_queryset(Farmer.objects.all(), request.user)
        quotations = scope_queryset(Quotation.objects.all(), request.user)
        claims = scope_queryset(Claim.objects.all(), request.user)

        # Farmer statistics
        total_farmers = farmers.count()
        active_farmers = farmers.filter(status='ACTIVE').count()

        # Quotation statistics
        total_quotations = quotations.count()
        open_quotations = quotations.filter(status='OPEN').count()
        paid_quotations = quotations.filter(status='PAID').count()
        written_policies = quotations.filter(status='WRITTEN').count()

        # Claim statistics
        total_claims = claims.count()
        open_claims = claims.filter(status='OPEN').count()
        pending_payment_claims = claims.filter(
            status='PENDING_PAYMENT'
        ).count()
        paid_claims = claims.filter(status='PAID').count()

        # Financial statistics
        total_premium = quotations.aggregate(
            total=Sum('premium_amount')
        )['total'] or 0
        total_claims_value = claims.aggregate(
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