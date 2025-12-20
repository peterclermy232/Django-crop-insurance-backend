from django.db import models


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