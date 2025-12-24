from django.db import models


class Inspection(models.Model):
    INSPECTION_TYPES = [
        ('PRE_PLANTING', 'Pre-Planting'),
        ('MID_SEASON', 'Mid-Season'),
        ('PRE_HARVEST', 'Pre-Harvest'),
        ('LOSS_ASSESSMENT', 'Loss Assessment'),
    ]

    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    inspection_id = models.AutoField(primary_key=True)
    farm = models.ForeignKey('Farm', on_delete=models.PROTECT)
    inspector = models.ForeignKey('User', on_delete=models.PROTECT)
    inspection_type = models.CharField(max_length=20, choices=INSPECTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')

    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    check_in_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_in_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_in_time = models.DateTimeField(null=True, blank=True)

    check_out_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_out_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    findings = models.JSONField(default=dict, blank=True)
    recommendations = models.TextField(blank=True)

    verified_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='verified_inspections')
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'inspections'
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.get_inspection_type_display()} - {self.farm.farm_name}"


class InspectionPhoto(models.Model):
    photo_id = models.AutoField(primary_key=True)
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='inspection_photos/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    taken_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inspection_photos'

    def __str__(self):
        return f"Photo for {self.inspection}"


class ClaimPhoto(models.Model):
    photo_id = models.AutoField(primary_key=True)
    claim = models.ForeignKey('Claim', on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='claim_photos/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'claim_photos'

    def __str__(self):
        return f"Photo for {self.claim.claim_number}"
