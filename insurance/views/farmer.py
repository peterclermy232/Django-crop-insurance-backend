from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count

from insurance.models import Farmer, Farm
from insurance.serializers import FarmerSerializer, FarmSerializer


class FarmerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(id_number__icontains=search) |
                Q(phone_number__icontains=search)
            )
        return queryset

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get farmer statistics"""
        total = self.get_queryset().count()
        active = self.get_queryset().filter(status='ACTIVE').count()
        by_gender = self.get_queryset().values('gender').annotate(
            count=Count('farmer_id')
        )

        return Response({
            'total_farmers': total,
            'active_farmers': active,
            'by_gender': list(by_gender)
        })


class FarmViewSet(viewsets.ModelViewSet):
    queryset = Farm.objects.all().order_by('-farm_id')
    serializer_class = FarmSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        farmer_id = self.request.query_params.get('farmer_id')
        if farmer_id:
            queryset = queryset.filter(farmer_id=farmer_id)
        return queryset