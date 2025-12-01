from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ===========================
# User Manager
# ===========================
class UserManager(BaseUserManager):
    def create_user(self, user_email, user_name, password=None, **extra_fields):
        if not user_email:
            raise ValueError('The Email field is required')
        email = self.normalize_email(user_email)
        user = self.model(user_email=email, user_name=user_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_email, user_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(user_email, user_name, password, **extra_fields)


# ===========================
# Core Models
# ===========================
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
    organisation_type = models.ForeignKey(OrganizationType, on_delete=models.PROTECT,
                                          db_column='organisation_type_id')
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


# ===========================
# User Model
# ===========================
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey(Organization, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, null=True, blank=True)
    user_type = models.CharField(max_length=50, default='API USER')
    user_name = models.CharField(max_length=200)
    user_email = models.EmailField(unique=True)
    user_msisdn = models.CharField(max_length=20, null=True, blank=True)
    user_status = models.CharField(max_length=20, default='ACTIVE')
    failed_logins = models.IntegerField(default=0)
    locked_till_date_time = models.DateTimeField(null=True, blank=True)
    reset_code = models.CharField(max_length=100, null=True, blank=True)
    reset_password = models.BooleanField(default=False)
    date_time_added = models.DateTimeField(auto_now_add=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'user_email'
    REQUIRED_FIELDS = ['user_name']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.user_name


# ===========================
# Add your other models here
# (Crop, CropVariety, CoverType, ProductCategory, Season, Farmer, Farm, etc.)
# ===========================

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

