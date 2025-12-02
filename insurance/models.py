from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, user_email, user_name, password=None, **extra_fields):
        if not user_email:
            raise ValueError('The Email field is required')
        email = self.normalize_email(user_email)

        # Get or create default organization if not provided
        if 'organisation' not in extra_fields or extra_fields.get('organisation') is None:
            default_org = Organization.objects.get(organisation_code='DEFAULT')
            extra_fields['organisation'] = default_org

        user = self.model(user_email=email, user_name=user_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_email, user_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'SUPERUSER')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(user_email, user_name, password, **extra_fields)

class Country(models.Model):
    country_id = models.AutoField(primary_key=True)
    country = models.CharField(max_length=100)
    country_code = models.CharField(max_length=10)
    country_is_deleted = models.BooleanField(default=False)
    record_version = models.IntegerField(default=1)
    date_time_added = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField(null=True, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    date_time_modified = models.DateTimeField(auto_now=True)
    modified_by = models.IntegerField(null=True, blank=True)
    latest_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'countries'
        verbose_name_plural = 'Countries'

    def __str__(self):
        return self.country


class OrganizationType(models.Model):
    organisation_type_id = models.AutoField(primary_key=True)
    organisation_type = models.CharField(max_length=100)
    organisation_type_description = models.TextField(null=True, blank=True)
    organisation_type_status = models.CharField(max_length=20, default='ACTIVE')
    record_version = models.IntegerField(default=1)
    date_time_added = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField(null=True, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    date_time_modified = models.DateTimeField(auto_now=True)
    modified_by = models.IntegerField(null=True, blank=True)
    latest_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'organisation_types'

    def __str__(self):
        return self.organisation_type


class Organization(models.Model):
    organisation_id = models.AutoField(primary_key=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, db_column='country_id')
    organisation_type = models.ForeignKey(OrganizationType, on_delete=models.PROTECT, db_column='organisation_type_id')
    organisation_code = models.CharField(max_length=50, unique=True)
    organisation_name = models.CharField(max_length=200)
    organisation_email = models.EmailField()
    organisation_msisdn = models.CharField(max_length=20)
    organisation_contact = models.CharField(max_length=200)
    organisation_physical_address = models.TextField(null=True, blank=True)
    organisation_status = models.CharField(max_length=20, default='ACTIVE')
    organisation_is_deleted = models.BooleanField(default=False)
    failed_login_threshold = models.IntegerField(default=5)
    failed_login_backoff = models.IntegerField(default=30)
    record_version = models.IntegerField(default=1)
    date_time_added = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField(null=True, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    date_time_modified = models.DateTimeField(auto_now=True)
    modified_by = models.IntegerField(null=True, blank=True)
    latest_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'organisations'

    def __str__(self):
        return self.organisation_name


class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, null=True, blank=True)
    user_role = models.CharField(max_length=50, default='API USER')
    user_name = models.CharField(max_length=200)
    user_email = models.EmailField(unique=True)
    user_phone_number = models.CharField(max_length=20, null=True, blank=True)
    user_status = models.CharField(max_length=20, default='ACTIVE')
    failed_logins = models.IntegerField(default=0)
    locked_till_date_time = models.DateTimeField(null=True, blank=True)
    reset_code = models.CharField(max_length=100, null=True, blank=True)
    reset_password = models.BooleanField(default=False)
    date_time_added = models.DateTimeField(auto_now_add=True)
    is_staff = models.BooleanField(default=False)
    user_is_active = models.BooleanField(default=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    # user_role = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'user_email'
    REQUIRED_FIELDS = ['user_name']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.user_name


class Crop(models.Model):
    crop_id = models.AutoField(primary_key=True, db_column='cropId')
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT, db_column='organisationId')
    crop = models.CharField(max_length=100)
    icon = models.CharField(max_length=200, null=True, blank=True)
    status = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    record_version = models.IntegerField(default=1, db_column='recordVersion')
    date_time_added = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'crops'

    def __str__(self):
        return self.crop


class CropVariety(models.Model):
    crop_variety_id = models.AutoField(primary_key=True)
    crop = models.ForeignKey(Crop, on_delete=models.PROTECT)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    crop_variety = models.CharField(max_length=100)
    status = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    record_version = models.IntegerField(default=1)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crop_varieties'

    def __str__(self):
        return self.crop_variety


class CoverType(models.Model):
    cover_type_id = models.AutoField(primary_key=True)
    cover_type = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cover_types'

    def __str__(self):
        return self.cover_type


class ProductCategory(models.Model):
    product_category_id = models.AutoField(primary_key=True)
    cover_type = models.ForeignKey(CoverType, on_delete=models.PROTECT)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    product_category = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_categories'

    def __str__(self):
        return self.product_category


class Season(models.Model):
    season_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    season = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seasons'

    def __str__(self):
        return self.season


class Farmer(models.Model):
    farmer_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    farmer_category = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'farmers'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Farm(models.Model):
    farm_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name='farms')
    farm_name = models.CharField(max_length=200)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2)
    unit_of_measure = models.CharField(max_length=20)
    location_province = models.CharField(max_length=100, null=True, blank=True)
    location_district = models.CharField(max_length=100, null=True, blank=True)
    location_sector = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'farms'

    def __str__(self):
        return self.farm_name


class NextOfKin(models.Model):
    next_of_kin_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='next_of_kin')
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'next_of_kin'

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    bank_account_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    account_name = models.CharField(max_length=200)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bank_accounts'

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"


class InsuranceProduct(models.Model):
    product_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    product_category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    season = models.ForeignKey(Season, on_delete=models.PROTECT)
    crop = models.ForeignKey(Crop, on_delete=models.PROTECT)
    crop_variety = models.ForeignKey(CropVariety, on_delete=models.PROTECT, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    average_premium_rate = models.DecimalField(max_digits=5, decimal_places=2)
    sum_insured = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'insurance_products'

    def __str__(self):
        return self.product_name


class Quotation(models.Model):
    quotation_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT)
    farm = models.ForeignKey(Farm, on_delete=models.PROTECT)
    insurance_product = models.ForeignKey(InsuranceProduct, on_delete=models.PROTECT)
    policy_number = models.CharField(max_length=100, null=True, blank=True)
    premium_amount = models.DecimalField(max_digits=15, decimal_places=2)
    sum_insured = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, default='OPEN')
    quotation_date = models.DateTimeField(auto_now_add=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    # farm_size = models.DecimalField(max_digits=10, decimal_places=2)
    # unit_of_measure = models.CharField(max_length=20)

    class Meta:
        db_table = 'quotations'

    def __str__(self):
        return f"Quotation {self.quotation_id}"


class LossAssessor(models.Model):
    assessor_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loss_assessors'

    def __str__(self):
        return self.user.user_name


class Claim(models.Model):
    claim_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT)
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT)
    loss_assessor = models.ForeignKey(LossAssessor, on_delete=models.PROTECT, null=True, blank=True)
    claim_number = models.CharField(max_length=100, unique=True)
    estimated_loss_amount = models.DecimalField(max_digits=15, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=30, default='OPEN')
    claim_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'claims'

    def __str__(self):
        return self.claim_number


class ClaimAssignment(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE)
    loss_assessor = models.ForeignKey(LossAssessor, on_delete=models.PROTECT)
    assigned_by = models.IntegerField()
    assignment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'claim_assignments'


class Subsidy(models.Model):
    subsidy_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    insurance_product = models.ForeignKey(InsuranceProduct, on_delete=models.PROTECT)
    subsidy_name = models.CharField(max_length=200)
    subsidy_rate = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subsidies'

    def __str__(self):
        return self.subsidy_name


class Invoice(models.Model):
    invoice_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    subsidy = models.ForeignKey(Subsidy, on_delete=models.PROTECT)
    invoice_number = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, default='PENDING')
    approved_date = models.DateTimeField(null=True, blank=True)
    settlement_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invoices'

    def __str__(self):
        return self.invoice_number


class Advisory(models.Model):
    advisory_id = models.AutoField(primary_key=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    sector = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    message = models.TextField()
    recipients_count = models.IntegerField(default=0)
    send_now = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='DRAFT')
    sent_date_time = models.DateTimeField(null=True, blank=True)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'advisories'

    def __str__(self):
        return f"Advisory {self.advisory_id}"


class WeatherData(models.Model):
    weather_id = models.AutoField(primary_key=True)
    location = models.CharField(max_length=200)
    data_type = models.CharField(max_length=50)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_at = models.DateTimeField()
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'weather_data'

    def __str__(self):
        return f"{self.location} - {self.data_type}"

    class WeatherData(models.Model):
        DATA_TYPE_CHOICES = [
            ('HISTORICAL', 'Historical'),
            ('FORECAST', 'Forecast'),
        ]

        weather_id = models.AutoField(primary_key=True)
        location = models.CharField(max_length=200)
        data_type = models.CharField(max_length=50, choices=DATA_TYPE_CHOICES)
        value = models.DecimalField(max_digits=10, decimal_places=2)
        recorded_at = models.DateTimeField()
        start_date = models.DateField(null=True, blank=True)
        end_date = models.DateField(null=True, blank=True)
        status = models.CharField(max_length=20, default='ACTIVE')
        date_time_added = models.DateTimeField(auto_now_add=True)

        class Meta:
            db_table = 'weather_data'
            ordering = ['-recorded_at']
            indexes = [
                models.Index(fields=['location', 'data_type']),
                models.Index(fields=['recorded_at']),
            ]

        def __str__(self):
            return f"{self.location} - {self.data_type} - {self.value}"