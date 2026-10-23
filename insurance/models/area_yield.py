import uuid

from django.conf import settings
from django.db import models


class AreaYield(models.Model):
    """
    The expected and measured yield of one crop in one area for one season.
    An approved actual yield triggers payouts on every area yield policy in that
    area, so it is entered by one person and approved by another.
    """
    DRAFT = 'DRAFT'
    APPROVED = 'APPROVED'
    STATUSES = [(DRAFT, 'Draft'), (APPROVED, 'Approved')]

    area_yield_id = models.AutoField(primary_key=True)
    # Random id shown in the API instead of the sequential primary key
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    crop = models.ForeignKey('Crop', on_delete=models.PROTECT)
    season = models.ForeignKey('Season', on_delete=models.PROTECT)
    administrative_unit = models.ForeignKey('AdministrativeUnit', on_delete=models.PROTECT)
    expected_yield = models.DecimalField(max_digits=10, decimal_places=2)
    actual_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    yield_unit = models.CharField(max_length=30)
    # Where the actual yield came from, e.g. "County crop-cut survey, May 2027"
    source = models.CharField(max_length=200, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUSES, default=DRAFT)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   blank=True, related_name='+')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)
    payouts_calculated_at = models.DateTimeField(null=True, blank=True)
    date_time_added = models.DateTimeField(auto_now_add=True)
    date_time_modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'area_yields'
        constraints = [
            models.UniqueConstraint(fields=['crop', 'season', 'administrative_unit'],
                                    name='unique_area_yield_per_crop_season_unit'),
        ]

    def __str__(self):
        return f'{self.crop} / {self.season} / {self.administrative_unit}'
