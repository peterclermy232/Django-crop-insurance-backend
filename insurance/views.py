from django.shortcuts import render

# Create your views here.
# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from .models import *
from .serializers import *


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.filter(country_is_deleted=False)
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]


class OrganizationTypeViewSet(viewsets.ModelViewSet):
    queryset = OrganizationType.objects.all()
    serializer_class = OrganizationTypeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.filter(organisation_is_deleted=False)
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return organizations with related org types and countries"""
        orgs = self.get_serializer(self.get_queryset(), many=True).data
        org_types = OrganizationTypeSerializer(OrganizationType.objects.all(), many=True).data
        countries = CountrySerializer(Country.objects.filter(country_is_deleted=False), many=True).data

        return Response({
            'orgsResponse': {'results': orgs},
            'orgTypesResponse': {'results': org_types},
            'countriesResponse': {'results': countries}
        })


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return users with related organizations and countries"""
        users = self.get_serializer(self.get_queryset(), many=True).data
        orgs = OrganizationSerializer(Organization.objects.filter(organisation_is_deleted=False), many=True).data
        countries = CountrySerializer(Country.objects.filter(country_is_deleted=False), many=True).data

        return Response({
            'usersResponse': users,
            'orgsResponse': orgs,
            'countriesResponse': countries
        })

    @action(detail=False, methods=['post'])
    def login(self, request):
        """User login endpoint"""
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = User.objects.get(user_email=username)
            if user.check_password(password):
                if user.user_status == 'ACTIVE':
                    # Generate token here (implement JWT or similar)
                    return Response({
                        'token': 'generated_token_here',
                        'user': self.get_serializer(user).data
                    })
                else:
                    return Response({'error': 'User account is inactive'},
                                    status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'error': 'Invalid credentials'},
                                status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'},
                            status=status.HTTP_401_UNAUTHORIZED)


class CropViewSet(viewsets.ModelViewSet):
    queryset = Crop.objects.filter(deleted=False)
    serializer_class = CropSerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return crops with organizations"""
        crops = self.get_serializer(self.get_queryset(), many=True).data
        orgs = OrganizationSerializer(Organization.objects.filter(organisation_is_deleted=False), many=True).data

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
        orgs = OrganizationSerializer(Organization.objects.filter(organisation_is_deleted=False), many=True).data

        return Response({
            'cropVarResponse': varieties,
            'cropsResponse': crops,
            'orgsResponse': {'results': orgs}
        })


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.filter(deleted=False)
    serializer_class = ProductCategorySerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return product categories with cover types and organizations"""
        categories = self.get_serializer(self.get_queryset(), many=True).data
        cover_types = CoverTypeSerializer(CoverType.objects.filter(deleted=False), many=True).data
        orgs = OrganizationSerializer(Organization.objects.filter(organisation_is_deleted=False), many=True).data

        return Response({
            'productCategoryResponse': categories,
            'coverTypesResponse': cover_types,
            'organisationsResponse': orgs
        })


class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.filter(deleted=False)
    serializer_class = SeasonSerializer


class FarmerViewSet(viewsets.ModelViewSet):
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
        by_gender = self.get_queryset().values('gender').annotate(count=Count('farmer_id'))

        return Response({
            'total_farmers': total,
            'active_farmers': active,
            'by_gender': list(by_gender)
        })


class FarmViewSet(viewsets.ModelViewSet):
    queryset = Farm.objects.all()
    serializer_class = FarmSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        farmer_id = self.request.query_params.get('farmer_id')
        if farmer_id:
            queryset = queryset.filter(farmer_id=farmer_id)
        return queryset


class InsuranceProductViewSet(viewsets.ModelViewSet):
    queryset = InsuranceProduct.objects.all()
    serializer_class = InsuranceProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.all()
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

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get quotation statistics"""
        total = self.get_queryset().count()
        by_status = self.get_queryset().values('status').annotate(count=Count('quotation_id'))
        total_premium = self.get_queryset().aggregate(total=Sum('premium_amount'))['total'] or 0

        return Response({
            'total_quotations': total,
            'by_status': list(by_status),
            'total_premium': float(total_premium)
        })

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark quotation as paid"""
        quotation = self.get_object()
        quotation.status = 'PAID'
        quotation.payment_date = timezone.now()
        quotation.payment_reference = request.data.get('payment_reference')
        quotation.save()

        return Response(self.get_serializer(quotation).data)

    @action(detail=True, methods=['post'])
    def write_policy(self, request, pk=None):
        """Convert quotation to written policy"""
        quotation = self.get_object()
        if quotation.status != 'PAID':
            return Response({'error': 'Quotation must be paid first'},
                            status=status.HTTP_400_BAD_REQUEST)

        quotation.status = 'WRITTEN'
        quotation.policy_number = f"POL-{timezone.now().strftime('%Y%m%d')}-{quotation.quotation_id}"
        quotation.save()

        return Response(self.get_serializer(quotation).data)


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
    queryset = Claim.objects.all()
    serializer_class = ClaimSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        farmer_id = self.request.query_params.get('farmer_id')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if farmer_id:
            queryset = queryset.filter(farmer_id=farmer_id)

        return queryset

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get claim statistics"""
        total = self.get_queryset().count()
        by_status = self.get_queryset().values('status').annotate(count=Count('claim_id'))
        total_claimed = self.get_queryset().aggregate(total=Sum('estimated_loss_amount'))['total'] or 0
        total_approved = self.get_queryset().aggregate(total=Sum('approved_amount'))['total'] or 0

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
            return Response({'error': 'Assessor ID required'},
                            status=status.HTTP_400_BAD_REQUEST)

        ClaimAssignment.objects.create(
            claim=claim,
            loss_assessor_id=assessor_id,
            assigned_by=request.user.user_id if hasattr(request.user, 'user_id') else 1
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


class SubsidyViewSet(viewsets.ModelViewSet):
    queryset = Subsidy.objects.all()
    serializer_class = SubsidySerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve invoice"""
        invoice = self.get_object()
        invoice.status = 'APPROVED'
        invoice.approved_date = timezone.now()
        invoice.save()

        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        """Settle invoice"""
        invoice = self.get_object()
        invoice.status = 'SETTLED'
        invoice.settlement_date = timezone.now()
        invoice.payment_reference = request.data.get('payment_reference')
        invoice.save()

        return Response(self.get_serializer(invoice).data)


class AdvisoryViewSet(viewsets.ModelViewSet):
    queryset = Advisory.objects.all()
    serializer_class = AdvisorySerializer

    @action(detail=False, methods=['post'])
    def send_advisory(self, request):
        """Send advisory message"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            advisory = serializer.save()

            if advisory.send_now:
                advisory.status = 'SENT'
                advisory.sent_date_time = timezone.now()
            else:
                advisory.status = 'SCHEDULED'

            advisory.save()

            return Response(self.get_serializer(advisory).data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def estimate_recipients(self, request):
        """Estimate number of recipients for advisory"""
        province = request.data.get('province')
        district = request.data.get('district')
        sector = request.data.get('sector')
        gender = request.data.get('gender')
        policy_status = request.data.get('policyStatus')

        # Build query
        farmers = Farmer.objects.all()

        if province:
            farmers = farmers.filter(farms__location_province=province)
        if district:
            farmers = farmers.filter(farms__location_district=district)
        if sector:
            farmers = farmers.filter(farms__location_sector=sector)
        if gender and gender != 'All':
            farmers = farmers.filter(gender=gender)

        count = farmers.distinct().count()

        return Response({'count': count})


class WeatherDataViewSet(viewsets.ModelViewSet):
    queryset = WeatherData.objects.all()
    serializer_class = WeatherDataSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        data_type = self.request.query_params.get('type')
        if data_type:
            queryset = queryset.filter(data_type=data_type)
        return queryset


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
        pending_payment_claims = Claim.objects.filter(status='PENDING_PAYMENT').count()
        paid_claims = Claim.objects.filter(status='PAID').count()

        # Financial statistics
        total_premium = Quotation.objects.aggregate(total=Sum('premium_amount'))['total'] or 0
        total_claims_value = Claim.objects.aggregate(total=Sum('approved_amount'))['total'] or 0

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


# ============= URLs Configuration =============
# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'countries', CountryViewSet)
router.register(r'organisation_types', OrganizationTypeViewSet)
router.register(r'organisations', OrganizationViewSet)
router.register(r'users', UserViewSet)
router.register(r'crops', CropViewSet)
router.register(r'crop_varieties', CropVarietyViewSet)
router.register(r'cover_types', viewsets.ModelViewSet.as_view({'get': 'list'}))
router.register(r'product_categories', ProductCategoryViewSet)
router.register(r'seasons', SeasonViewSet)
router.register(r'farmers', FarmerViewSet)
router.register(r'farms', FarmViewSet)
router.register(r'insurance_products', InsuranceProductViewSet)
router.register(r'quotations', QuotationViewSet)
router.register(r'loss_assessors', LossAssessorViewSet)
router.register(r'claims', ClaimViewSet)
router.register(r'subsidies', SubsidyViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'advisories', AdvisoryViewSet)
router.register(r'weather_data', WeatherDataViewSet)
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('api/v1/', include(router.urls)),
]