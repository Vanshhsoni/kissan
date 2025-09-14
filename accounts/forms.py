from django import forms
from .models import User, DISTRICTS, SOIL_TYPES, ACREAGE_CHOICES

class MobileLoginForm(forms.Form):
    mobile = forms.CharField(max_length=15, label="Mobile Number")


class UserRegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["mobile", "name", "acreage", "district", "pincode", "soil_type"]
        widgets = {
            "acreage": forms.Select(choices=ACREAGE_CHOICES, attrs={"class": "form-input"}),
            "district": forms.Select(choices=DISTRICTS, attrs={"class": "form-input"}),
            "soil_type": forms.Select(choices=SOIL_TYPES, attrs={"class": "form-input"}),
        }
