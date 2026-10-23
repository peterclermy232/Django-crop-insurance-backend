import uuid

from django.db import models


class CoverType(models.Model):
    # How losses are measured and paid. Names are free text, so code checks this instead.
    INDIVIDUAL_FARM = 'INDIVIDUAL_FARM'  # each farm's loss is claimed and assessed
    AREA_YIELD = 'AREA_YIELD'  # paid when the average yield of an area falls below a threshold
    WEATHER_INDEX = 'WEATHER_INDEX'  # paid when measured weather crosses a trigger
    CALCULATION_METHODS = [
        (INDIVIDUAL_FARM, 'Individual farm'),
        (AREA_YIELD, 'Area yield index'),
        (WEATHER_INDEX, 'Weather index'),
    ]

    cover_type_id = models.AutoField(primary_key=True)
    # Empty for shared cover types every organisation can use; set for an organisation's own
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT, null=True, blank=True)
    cover_type = models.CharField(max_length=100)
    calculation_method = models.CharField(max_length=20, choices=CALCULATION_METHODS, default=INDIVIDUAL_FARM)
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
    # Random id shown in the API instead of the sequential primary key
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    cover_type = models.ForeignKey(CoverType, on_delete=models.PROTECT)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    product_category = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_categories'

    def __str__(self):
        return self.product_category


class InsuranceProduct(models.Model):
    product_id = models.AutoField(primary_key=True)
    # Random id shown in the API instead of the sequential primary key
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    product_category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    season = models.ForeignKey('Season', on_delete=models.PROTECT)
    crop = models.ForeignKey('Crop', on_delete=models.PROTECT)
    crop_variety = models.ForeignKey('CropVariety', on_delete=models.PROTECT, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    average_premium_rate = models.DecimalField(max_digits=5, decimal_places=2)
    sum_insured = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    # Area yield index terms (only for products whose cover type is AREA_YIELD).
    # Pays sum_insured x (guaranteed - actual) / guaranteed, where guaranteed is
    # coverage_level % of the area's expected yield, capped at max_payout_percent.
    AREA_LEVELS = [('WARD', 'Ward'), ('SUB_COUNTY', 'Sub-County'), ('COUNTY', 'County')]
    area_level = models.CharField(max_length=20, choices=AREA_LEVELS, null=True, blank=True)
    coverage_level = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    yield_unit = models.CharField(max_length=30, null=True, blank=True)
    max_payout_percent = models.DecimalField(max_digits=5, decimal_places=2, default=100)

    class Meta:
        db_table = 'insurance_products'

    @property
    def calculation_method(self):
        return self.product_category.cover_type.calculation_method

    @property
    def is_area_yield(self):
        return self.calculation_method == CoverType.AREA_YIELD

    def __str__(self):
        return self.product_name