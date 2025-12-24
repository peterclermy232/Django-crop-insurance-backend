# Auth views
from .auth import (
    LoginView,
    RegisterView,
    LogoutView,
    RefreshTokenView,
)

# Base views
from .base import (
    CountryViewSet,
    OrganizationTypeViewSet,
    OrganizationViewSet,
)

# User views
from .user import UserViewSet

# Agriculture views
from .agriculture import (
    CropViewSet,
    CropVarietyViewSet,
    CoverTypeViewSet,
    ProductCategoryViewSet,
    SeasonViewSet,
)

# Farmer views
from .farmer import (
    FarmerViewSet,
    FarmViewSet,
)

# Insurance views
from .insurance import InsuranceProductViewSet

# Policy views
from .policy import QuotationViewSet

# Claims views
from .claims import (
    ClaimViewSet,
    LossAssessorViewSet,
)

# Financial views
from .financial import (
    SubsidyViewSet,
    InvoiceViewSet,
)

# Advisory views
from .advisory import (
    AdvisoryViewSet,
    WeatherDataViewSet,
)

# Dashboard views
from .dashboard import DashboardViewSet
from .inspection import InspectionViewSet
__all__ = [
    # Auth
    'LoginView',
    'RegisterView',
    'LogoutView',
    'RefreshTokenView',

    # Base
    'CountryViewSet',
    'OrganizationTypeViewSet',
    'OrganizationViewSet',

    # User
    'UserViewSet',

    # Agriculture
    'CropViewSet',
    'CropVarietyViewSet',
    'CoverTypeViewSet',
    'ProductCategoryViewSet',
    'SeasonViewSet',

    # Farmer
    'FarmerViewSet',
    'FarmViewSet',

    # Insurance
    'InsuranceProductViewSet',

    # Policy
    'QuotationViewSet',

    # Claims
    'ClaimViewSet',
    'LossAssessorViewSet',

    # Financial
    'SubsidyViewSet',
    'InvoiceViewSet',

    # Advisory
    'AdvisoryViewSet',
    'WeatherDataViewSet',

    # Dashboard
    'DashboardViewSet',
#inspection View
 InspectionViewSet,
]