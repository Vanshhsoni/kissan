from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

DISTRICTS = [
    ("തിരുവനന്തപുരം", "തിരുവനന്തപുരം"),  # Thiruvananthapuram
    ("കൊല്ലം", "കൊല്ലം"),              # Kollam
    ("പത്തനംതിട്ട", "പത്തനംതിട്ട"),      # Pathanamthitta
    ("ആലപ്പുഴ", "ആലപ്പുഴ"),            # Alappuzha
    ("കോട്ടയം", "കോട്ടയം"),            # Kottayam
    ("ഇടുക്കി", "ഇടുക്കി"),            # Idukki
    ("എറണാകുളം", "എറണാകുളം"),        # Ernakulam
    ("ത്രിശ്ശൂർ", "ത്രിശ്ശൂർ"),        # Thrissur
    ("പാലക്കാട്", "പാലക്കാട്"),        # Palakkad
    ("മലപ്പുറം", "മലപ്പുറം"),          # Malappuram
    ("കോഴിക്കോട്", "കോഴിക്കോട്"),      # Kozhikode
    ("വയനാട്", "വയനാട്"),            # Wayanad
    ("കണ്ണൂർ", "കണ്ണൂർ"),              # Kannur
    ("കാസർഗോഡ്", "കാസർഗോഡ്"),      # Kasaragod
]

ACREAGE_CHOICES = [
    ("<1", "1 ഏക്കറിൽ താഴെ"),      # Less than 1 acre
    (">1", "1 ഏക്കറിൽ കൂടുതൽ"),   # More than 1 acre
]

SOIL_TYPES = [
    ("മണൽ", "മണൽ"),            # Sandy soil
    ("ചെങ്കൽ", "ചെങ്കൽ"),        # Laterite
    ("കറുത്ത മണ്ണ്", "കറുത്ത മണ്ണ്"),  # Black soil
    ("ചെങ്കൽ മണ്ണ്", "ചെങ്കൽ മണ്ണ്"), # Lateritic soil
    ("അല്ലുവിയൽ", "അല്ലുവിയൽ"),    # Alluvial soil
]


class UserManager(BaseUserManager):
    def create_user(self, mobile, name=None, **extra_fields):
        if not mobile:
            raise ValueError("Mobile number is required")
        user = self.model(mobile=mobile, name=name, **extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(mobile, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    mobile = models.CharField(max_length=15, unique=True, primary_key=True)
    name = models.CharField(max_length=100)  # required
    acreage = models.CharField(max_length=10, choices=ACREAGE_CHOICES)  # required
    district = models.CharField(max_length=50, choices=DISTRICTS)  # required
    pincode = models.CharField(max_length=6)  # required
    soil_type = models.CharField(max_length=50, choices=SOIL_TYPES)  # required

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = ["name", "acreage", "district", "pincode", "soil_type"]

    objects = UserManager()

    def __str__(self):
        return self.name or self.mobile

