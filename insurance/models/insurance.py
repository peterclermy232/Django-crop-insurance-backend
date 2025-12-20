from django.db import models


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

    class Meta:
        db_table = 'insurance_products'

    def __str__(self):
        return self.product_name