# settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    'django_filters',
    
    # Local apps
    'insurance',  # Your app name
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'insurance_project.urls'
WSGI_APPLICATION = 'insurance_project.wsgi.application'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'insurance_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
AUTH_USER_MODEL = 'insurance.User'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Change to IsAuthenticated in production
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'user_id',
    'USER_ID_CLAIM': 'user_id',
}

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@insurance.com')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)


# ============= requirements.txt =============
"""
Django==4.2.7
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-filter==23.5
psycopg2-binary==2.9.9
djangorestframework-simplejwt==5.3.1
python-decouple==3.8
celery==5.3.4
redis==5.0.1
pillow==10.1.0
openpyxl==3.1.2
pandas==2.1.4
reportlab==4.0.8
gunicorn==21.2.0
whitenoise==6.6.0
"""


# ============= .env.example =============
"""
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=insurance_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@insurance.com

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# SMS Gateway (if applicable)
SMS_API_KEY=your-sms-api-key
SMS_SENDER_ID=INSURANCE
"""


# ============= admin.py =============
"""
from django.contrib import admin
from .models import *


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['country_id', 'country', 'country_code', 'country_is_deleted']
    search_fields = ['country', 'country_code']
    list_filter = ['country_is_deleted']


@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):
    list_display = ['organisation_type_id', 'organisation_type', 'organisation_type_status']
    search_fields = ['organisation_type']
    list_filter = ['organisation_type_status']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['organisation_id', 'organisation_name', 'organisation_code', 
                   'organisation_status', 'country']
    search_fields = ['organisation_name', 'organisation_code', 'organisation_email']
    list_filter = ['organisation_status', 'country', 'organisation_type']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'user_name', 'user_email', 'user_status', 'organisation']
    search_fields = ['user_name', 'user_email']
    list_filter = ['user_status', 'user_type', 'organisation']


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ['farmer_id', 'first_name', 'last_name', 'id_number', 
                   'phone_number', 'status']
    search_fields = ['first_name', 'last_name', 'id_number', 'phone_number']
    list_filter = ['status', 'gender', 'farmer_category', 'organisation']


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['farm_id', 'farm_name', 'farmer', 'farm_size', 
                   'unit_of_measure', 'status']
    search_fields = ['farm_name', 'farmer__first_name', 'farmer__last_name']
    list_filter = ['status', 'unit_of_measure', 'location_province']


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ['crop_id', 'crop', 'organisation', 'status', 'deleted']
    search_fields = ['crop']
    list_filter = ['status', 'deleted', 'organisation']


@admin.register(CropVariety)
class CropVarietyAdmin(admin.ModelAdmin):
    list_display = ['crop_variety_id', 'crop_variety', 'crop', 'status']
    search_fields = ['crop_variety', 'crop__crop']
    list_filter = ['status', 'deleted', 'crop']


@admin.register(InsuranceProduct)
class InsuranceProductAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'product_name', 'crop', 'average_premium_rate', 'status']
    search_fields = ['product_name']
    list_filter = ['status', 'crop', 'season', 'product_category']


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['quotation_id', 'policy_number', 'farmer', 'premium_amount', 
                   'status', 'quotation_date']
    search_fields = ['policy_number', 'farmer__first_name', 'farmer__last_name']
    list_filter = ['status', 'quotation_date']


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_id', 'claim_number', 'farmer', 'estimated_loss_amount', 
                   'status', 'claim_date']
    search_fields = ['claim_number', 'farmer__first_name', 'farmer__last_name']
    list_filter = ['status', 'claim_date']


@admin.register(Advisory)
class AdvisoryAdmin(admin.ModelAdmin):
    list_display = ['advisory_id', 'province', 'district', 'status', 
                   'recipients_count', 'date_time_added']
    search_fields = ['province', 'district', 'sector']
    list_filter = ['status', 'province', 'gender']
"""


# ============= management/commands/seed_data.py =============
"""
from django.core.management.base import BaseCommand
from insurance.models import *

class Command(BaseCommand):
    help = 'Seeds the database with initial data'

    def handle(self, *args, **options):
        # Create Countries
        countries_data = [
            {'country': 'Kenya', 'country_code': 'KE'},
            {'country': 'Uganda', 'country_code': 'UG'},
            {'country': 'Tanzania', 'country_code': 'TZ'},
            {'country': 'Rwanda', 'country_code': 'RW'},
        ]
        
        for country_data in countries_data:
            Country.objects.get_or_create(**country_data)
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded countries'))
        
        # Create Organization Types
        org_types_data = [
            {'organisation_type': 'Insurance Company', 
             'organisation_type_description': 'Insurance provider organizations'},
            {'organisation_type': 'Agricultural Cooperative', 
             'organisation_type_description': 'Farmer cooperative organizations'},
            {'organisation_type': 'Government Agency', 
             'organisation_type_description': 'Government departments'},
            {'organisation_type': 'NGO', 
             'organisation_type_description': 'Non-governmental organizations'},
        ]
        
        for org_type_data in org_types_data:
            OrganizationType.objects.get_or_create(**org_type_data)
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded organization types'))
        
        self.stdout.write(self.style.SUCCESS('Database seeding completed!'))
"""