from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, user_email, user_name, password=None, **extra_fields):
        if not user_email:
            raise ValueError('The Email field is required')
        email = self.normalize_email(user_email)

        # Get or create default organization if not provided
        if 'organisation' not in extra_fields or extra_fields.get('organisation') is None:
            from insurance.models.base import Organization
            default_org = Organization.objects.get(organisation_code='DEFAULT')
            extra_fields['organisation'] = default_org

        user = self.model(user_email=email, user_name=user_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_email, user_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_role', 'SUPERUSER')  # Fixed: was 'user_type'
        extra_fields.setdefault('user_is_active', True)  # Fixed: ensure active

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(user_email, user_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    country = models.ForeignKey('Country', on_delete=models.PROTECT, null=True, blank=True)
    user_role = models.CharField(max_length=50, default='API USER')
    user_name = models.CharField(max_length=200)
    user_email = models.EmailField(unique=True)
    user_phone_number = models.CharField(max_length=20, null=True, blank=True)
    user_status = models.CharField(max_length=20, default='ACTIVE')
    failed_logins = models.IntegerField(default=0)
    locked_till_date_time = models.DateTimeField(null=True, blank=True)
    reset_code = models.CharField(max_length=100, null=True, blank=True)
    reset_password = models.BooleanField(default=False)
    date_time_added = models.DateTimeField(auto_now_add=True)
    is_staff = models.BooleanField(default=False)
    user_is_active = models.BooleanField(default=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'user_email'
    REQUIRED_FIELDS = ['user_name']

    class Meta:
        db_table = 'users'

    # Fix the is_active property to use the correct field name
    @property
    def is_active(self):
        return self.user_is_active

    @is_active.setter
    def is_active(self, value):
        self.user_is_active = value

    def __str__(self):
        return self.user_name


class RoleType(models.Model):
    role_id = models.AutoField(primary_key=True)
    organisation = models.ForeignKey('Organization', on_delete=models.PROTECT)
    role_name = models.CharField(max_length=100, unique=True)
    role_description = models.TextField(null=True, blank=True)
    role_status = models.CharField(max_length=20, default='ACTIVE')
    permissions = models.JSONField(null=True, blank=True)
    is_system_role = models.BooleanField(default=False)
    date_time_added = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField(null=True, blank=True)
    date_time_modified = models.DateTimeField(auto_now=True)
    modified_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'role_types'
        verbose_name_plural = 'Role Types'

    def __str__(self):
        return self.role_name


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('SUCCESS', 'Success'),
        ('DANGER', 'Danger'),
    ]

    notification_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='INFO')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.user_name}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200, null=True, blank=True)
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    parent_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')

    class Meta:
        db_table = 'messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"From {self.sender.user_name} to {self.recipient.user_name}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()