# insurance_project/urls.py
"""
Main URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from insurance.views.notifications import NotificationViewSet, MessageViewSet
from insurance.views.upload import MediaUploadView
from insurance.views.sync import SyncAPIView


# Import all ViewSets
from insurance.views import (
    # Auth viewsa
    LoginView,
    RegisterView,
    LogoutView,
    RefreshTokenView,

    # Base views
    CountryViewSet,
    OrganizationTypeViewSet,
    OrganizationViewSet,

    # User views
    UserViewSet,

    # Agriculture views
    CropViewSet,
    CropVarietyViewSet,
    CoverTypeViewSet,
    ProductCategoryViewSet,
    SeasonViewSet,

    # Farmer views
    FarmerViewSet,
    FarmViewSet,

    # Insurance views
    InsuranceProductViewSet,

    # Policy views
    QuotationViewSet,

    # Claims views
    ClaimViewSet,
    LossAssessorViewSet,

    # Financial views
    SubsidyViewSet,
    InvoiceViewSet,

    # Advisory views
    AdvisoryViewSet,
    WeatherDataViewSet,

    # Dashboard views
    DashboardViewSet,
#inspection View
 InspectionViewSet,
NotificationViewSet,
MessageViewSet,
)


def api_root(request):
    """API root endpoint showing all available endpoints"""
    return JsonResponse({
        'message': 'Insurance Management System API',
        'version': 'v1',
        'endpoints': {
            'admin': '/admin/',
            'api': '/api/v1/',
            'auth': {
                'login': '/api/v1/auth/login/',
                'register': '/api/v1/auth/register/',
                'logout': '/api/v1/auth/logout/',
                'refresh': '/api/v1/auth/token/refresh/',
            },
            'resources': [
                '/api/v1/countries/',
                '/api/v1/organisation_types/',
                '/api/v1/organisations/',
                '/api/v1/users/',
                '/api/v1/crops/',
                '/api/v1/crop_varieties/',
                '/api/v1/cover_types/',
                '/api/v1/product_categories/',
                '/api/v1/seasons/',
                '/api/v1/farmers/',
                '/api/v1/farms/',
                '/api/v1/insurance_products/',
                '/api/v1/quotations/',
                '/api/v1/loss_assessors/',
                '/api/v1/claims/',
                '/api/v1/subsidies/',
                '/api/v1/invoices/',
                '/api/v1/advisories/',
                '/api/v1/weather_data/',
                '/api/v1/dashboard/statistics/',
                '/api/v1/sync/',
            ]
        }
    })


# Create router and register all viewsets
router = DefaultRouter()
router.register(r'countries', CountryViewSet)
router.register(r'organisation_types', OrganizationTypeViewSet)
router.register(r'organisations', OrganizationViewSet)
router.register(r'users', UserViewSet)
router.register(r'crops', CropViewSet)
router.register(r'crop_varieties', CropVarietyViewSet)
router.register(r'cover_types', CoverTypeViewSet)
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
router.register(r'inspections', InspectionViewSet)
# ADD to router.register() calls:
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    # Root endpoint
    path('', api_root, name='api-root'),

    # Admin panel
    path('admin/', admin.site.urls),

    # All API endpoints under /api/v1/
    path('api/v1/', include(router.urls)),

    path('api/v1/sync/', SyncAPIView.as_view(), name='sync'),
    # Authentication endpoints
    path('api/v1/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/v1/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/v1/auth/token/refresh/', RefreshTokenView.as_view(), name='auth-token-refresh'),
     path('api/v1/upload/', MediaUploadView.as_view(), name='media-upload'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
