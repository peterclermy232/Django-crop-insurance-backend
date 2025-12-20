from django.db import models


class Quotation(models.Model):
    quotation_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey('Farmer', on_delete=models.PROTECT)
    farm = models.ForeignKey('Farm', on_delete=models.PROTECT)
    insurance_product = models.ForeignKey('InsuranceProduct', on_delete=models.PROTECT)
    policy_number = models.CharField(max_length=100, null=True, blank=True)
    premium_amount = models.DecimalField(max_digits=15, decimal_places=2)
    sum_insured = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, default='OPEN')
    quotation_date = models.DateTimeField(auto_now_add=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'quotations'

    def __str__(self):
        return f"Quotation {self.quotation_id}"