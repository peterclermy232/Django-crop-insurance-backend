from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from insurance.models import (
    Crop, CropVariety, CoverType, ProductCategory, Season, Organization
)
from insurance.serializers import (
    CropSerializer, CropVarietySerializer, CoverTypeSerializer,
    ProductCategorySerializer, SeasonSerializer, OrganizationSerializer,
)


class CropViewSet(viewsets.ModelViewSet):
    queryset = Crop.objects.filter(deleted=False)
    serializer_class = CropSerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return crops with organizations"""
        crops = self.get_serializer(self.get_queryset(), many=True).data
        orgs = OrganizationSerializer(
            Organization.objects.filter(organisation_is_deleted=False),
            many=True
        ).data

        return Response({
            'cropsResponse': crops,
            'orgsResponse': {'results': orgs}
        })


class CropVarietyViewSet(viewsets.ModelViewSet):
    queryset = CropVariety.objects.filter(deleted=False)
    serializer_class = CropVarietySerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return crop varieties with crops and organizations"""
        varieties = self.get_serializer(self.get_queryset(), many=True).data
        crops = CropSerializer(Crop.objects.filter(deleted=False), many=True).data
        orgs = OrganizationSerializer(
            Organization.objects.filter(organisation_is_deleted=False),
            many=True
        ).data

        return Response({
            'cropVarResponse': varieties,
            'cropsResponse': crops,
            'orgsResponse': {'results': orgs}
        })


class CoverTypeViewSet(viewsets.ModelViewSet):
    queryset = CoverType.objects.filter(deleted=False)
    serializer_class = CoverTypeSerializer


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.filter(deleted=False)
    serializer_class = ProductCategorySerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return product categories with cover types and organizations"""
        categories = self.get_serializer(self.get_queryset(), many=True).data
        cover_types = CoverTypeSerializer(
            CoverType.objects.filter(deleted=False),
            many=True
        ).data
        orgs = OrganizationSerializer(
            Organization.objects.filter(organisation_is_deleted=False),
            many=True
        ).data

        return Response({
            'productCategoryResponse': categories,
            'coverTypesResponse': cover_types,
            'organisationsResponse': orgs
        })


class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.filter(deleted=False)
    serializer_class = SeasonSerializer