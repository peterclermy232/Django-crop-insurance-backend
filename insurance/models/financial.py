from django.db import models


class Subsidy(models.Model):
    subsidy_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    insurance_product = models.ForeignKey('InsuranceProduct', on_delete=models.PROTECT)
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
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
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