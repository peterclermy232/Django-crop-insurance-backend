from rest_framework import viewsets
from insurance.models import InsuranceProduct
from insurance.serializers import InsuranceProductSerializer


class InsuranceProductViewSet(viewsets.ModelViewSet):
    queryset = InsuranceProduct.objects.all().order_by('-product_id')
    serializer_class = InsuranceProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset