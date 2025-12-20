from django.db import models


class Crop(models.Model):
    crop_id = models.AutoField(primary_key=True, db_column='cropId')
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT, db_column='organisationId')
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
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    crop_variety = models.CharField(max_length=100)
    status = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    record_version = models.IntegerField(default=1)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crop_varieties'

    def __str__(self):
        return self.crop_variety


class Season(models.Model):
    season_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
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