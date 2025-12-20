from django.db import models


class LossAssessor(models.Model):
    assessor_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('User', on_delete=models.PROTECT)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loss_assessors'

    def __str__(self):
        return self.user.user_name


class Claim(models.Model):
    claim_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey('Farmer', on_delete=models.PROTECT)
    quotation = models.ForeignKey('Quotation', on_delete=models.PROTECT)
    loss_assessor = models.ForeignKey(LossAssessor, on_delete=models.PROTECT, null=True, blank=True)
    claim_number = models.CharField(max_length=100, unique=True)
    estimated_loss_amount = models.DecimalField(max_digits=15, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=30, default='OPEN')
    claim_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    loss_details = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'claims'

    def __str__(self):
        return self.claim_number


class ClaimAssignment(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE)
    loss_assessor = models.ForeignKey(LossAssessor, on_delete=models.PROTECT)
    assigned_by = models.IntegerField()
    assignment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'claim_assignments'