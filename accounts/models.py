from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

# CustomUserManager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("Email must be set!!!"))
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_("superuser must have is_staff=True"))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_("superuser must have is_superuser=True"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)  # Add other fields
        user.set_password(password)
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    USER_ROLE = [
        ('admin', 'ADMIN'),
        ('seller', 'SELLER'),
        ('buyer', 'BUYER')
    ]

    username = models.CharField(unique=True, max_length=200)
    email = models.EmailField(_('email_address'), unique=True, max_length=200)
    role = models.CharField(max_length=20, choices=USER_ROLE, blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    first_name = models.CharField(max_length=100 )
    last_name = models.CharField(max_length=100 )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    objects = CustomUserManager()

    class Meta:
        db_table = "user"

    def save(self, *args, **kwargs):
        if self.role == 'admin':
            self.is_staff = True
            self.is_superuser = True
        elif self.role == 'seller':
            self.is_staff = True
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    # @property
    # def is_admin(self):
    #     "Is the user an admin member?"
    #     return self.is_admin

    def __str__(self):
        return self.email

# profile
class Profile(models.Model):
    GENDER_CHOICE = [
        ('male', 'MALE'),
        ('female', 'FEMALE'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profiles')
    profile_pic = models.ImageField(upload_to='profile_pics', null=True, blank=True)
    mobile_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')],
        null=True, blank=True
    )
    address = models.TextField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICE, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "user_profile"

    # def __str__(self):
    #     return self.user.role