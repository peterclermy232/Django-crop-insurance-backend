from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from insurance.models import (
    # Base
    Country, OrganizationType, Organization,
    # User
    User, RoleType, Notification, Message,
    # Agriculture
    Crop, CropVariety, Season,
    # Farmer
    Farmer, Farm, NextOfKin, BankAccount,
    # Insurance
    InsuranceProduct, CoverType, ProductCategory,
    # Policy
    Quotation,
    # Claims
    Claim, ClaimAssignment, LossAssessor,
    # Financial
    Subsidy, Invoice,
    # Advisory
    Advisory, WeatherData,
)


# ===== Base Models =====
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['country_id', 'country', 'country_code', 'country_is_deleted']
    search_fields = ['country', 'country_code']
    list_filter = ['country_is_deleted']


@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):
    list_display = ['organisation_type_id', 'organisation_type']
    search_fields = ['organisation_type']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['organisation_id', 'organisation_name', 'organisation_type', 'country']
    search_fields = ['organisation_name', 'organisation_code']
    list_filter = ['organisation_type', 'country', 'organisation_is_deleted']


# ===== User Models =====
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['user_id', 'user_email', 'user_name', 'user_role', 'user_status', 'organisation']
    search_fields = ['user_email', 'user_name']
    list_filter = ['user_role', 'user_status', 'organisation']

    fieldsets = (
        (None, {'fields': ('user_email', 'password')}),
        ('Personal info', {'fields': ('user_name', 'user_phone_number')}),
        ('Permissions', {'fields': ('user_role', 'user_status', 'user_is_active')}),
        ('Organization', {'fields': ('organisation', 'country')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('user_email', 'user_name', 'password1', 'password2'),
        }),
    )

    ordering = ['user_email']


@admin.register(RoleType)
class RoleTypeAdmin(admin.ModelAdmin):
    list_display = ['role_id', 'role_name', 'role_status', 'is_system_role', 'organisation']
    search_fields = ['role_name']
    list_filter = ['role_status', 'is_system_role']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'user', 'notification_type', 'title', 'is_read', 'created_at']
    search_fields = ['title', 'message']
    list_filter = ['notification_type', 'is_read', 'created_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'sender', 'recipient', 'subject', 'is_read', 'created_at']
    search_fields = ['subject', 'text']
    list_filter = ['is_read', 'created_at']


# ===== Agriculture Models =====
@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ['crop_id', 'crop', 'organisation', 'deleted']
    search_fields = ['crop']
    list_filter = ['organisation', 'deleted']


@admin.register(CropVariety)
class CropVarietyAdmin(admin.ModelAdmin):
    list_display = ['crop_variety_id', 'crop_variety', 'crop', 'organisation', 'deleted']
    search_fields = ['crop_variety']
    list_filter = ['crop', 'organisation', 'deleted']


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ['season_id', 'season', 'start_date', 'end_date', 'organisation', 'deleted']
    search_fields = ['season']
    list_filter = ['organisation', 'deleted']


# ===== Farmer Models =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ['farmer_id', 'first_name', 'last_name', 'id_number', 'phone_number', 'status']
    search_fields = ['first_name', 'last_name', 'id_number', 'phone_number']
    list_filter = ['status', 'gender', 'country']


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['farm_id', 'farm_name', 'farmer', 'farm_size', 'location_district']
    search_fields = ['farm_name', 'farmer__first_name', 'farmer__last_name']
    list_filter = ['location_province', 'location_district']


@admin.register(NextOfKin)
class NextOfKinAdmin(admin.ModelAdmin):
    list_display = ['next_of_kin_id', 'name', 'relationship', 'farmer']
    search_fields = ['name', 'farmer__first_name', 'farmer__last_name']


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['bank_account_id', 'account_number', 'bank_name', 'farmer']
    search_fields = ['account_number', 'bank_name', 'farmer__first_name']


# ===== Insurance Models =====
@admin.register(CoverType)
class CoverTypeAdmin(admin.ModelAdmin):
    list_display = ['cover_type_id', 'cover_type', 'deleted']
    search_fields = ['cover_type']
    list_filter = ['deleted']


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['product_category_id', 'product_category', 'cover_type', 'organisation']
    search_fields = ['product_category']
    list_filter = ['cover_type', 'organisation']


@admin.register(InsuranceProduct)
class InsuranceProductAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'product_name', 'product_category', 'average_premium_rate', 'status']
    search_fields = ['product_name']
    list_filter = ['product_category', 'status', 'organisation']


# ===== Policy Models =====
@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['quotation_id', 'policy_number', 'farmer', 'premium_amount', 'sum_insured', 'status']
    search_fields = ['policy_number', 'farmer__first_name', 'farmer__last_name']
    list_filter = ['status', 'quotation_date']


# ===== Claims Models =====
@admin.register(LossAssessor)
class LossAssessorAdmin(admin.ModelAdmin):
    list_display = ['assessor_id', 'user', 'organisation', 'status']
    search_fields = ['user__user_name']
    list_filter = ['status', 'organisation']


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_id', 'claim_number', 'farmer', 'estimated_loss_amount', 'approved_amount', 'status']
    search_fields = ['claim_number', 'farmer__first_name', 'farmer__last_name']
    list_filter = ['status', 'claim_date']


@admin.register(ClaimAssignment)
class ClaimAssignmentAdmin(admin.ModelAdmin):
    list_display = ['assignment_id', 'claim', 'loss_assessor', 'assignment_date']
    search_fields = ['claim__claim_number']
    list_filter = ['assignment_date']


# ===== Financial Models =====
@admin.register(Subsidy)
class SubsidyAdmin(admin.ModelAdmin):
    list_display = ['subsidy_id', 'subsidy_name','subsidy_rate', 'status', 'organisation']
    search_fields = ['subsidy_name']
    list_filter = ['status','organisation']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_id', 'invoice_number', 'amount', 'status', 'organisation']
    search_fields = ['invoice_number']
    list_filter = ['status', 'organisation']


# ===== Advisory Models =====
@admin.register(Advisory)
class AdvisoryAdmin(admin.ModelAdmin):
    list_display = ['advisory_id', 'title', 'status', 'send_now', 'sent_date_time']
    search_fields = ['title', 'message']
    list_filter = ['status', 'send_now']


@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = ['weather_id', 'data_type', 'location', 'value', 'recorded_at']
    search_fields = ['location']
    list_filter = ['data_type', 'recorded_at']