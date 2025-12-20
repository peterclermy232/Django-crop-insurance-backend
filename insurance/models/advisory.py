from django.db import models


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
    title = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'advisories'

    def __str__(self):
        return f"Advisory {self.advisory_id}"


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