from django.db import models


class Farmer(models.Model):
    farmer_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    country = models.ForeignKey('Country', on_delete=models.PROTECT, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    farmer_category = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'farmers'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Farm(models.Model):
    farm_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name='farms')
    farm_name = models.CharField(max_length=200)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2)
    unit_of_measure = models.CharField(max_length=20)
    location_province = models.CharField(max_length=100, null=True, blank=True)
    location_district = models.CharField(max_length=100, null=True, blank=True)
    location_sector = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'farms'

    def __str__(self):
        return self.farm_name


class NextOfKin(models.Model):
    next_of_kin_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='next_of_kin')
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'next_of_kin'

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    bank_account_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    account_name = models.CharField(max_length=200)
    date_time_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bank_accounts'

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"
