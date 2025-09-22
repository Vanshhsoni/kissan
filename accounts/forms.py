from django import forms
from .models import User

class UserRegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["mobile", "name", "acreage", "district", "pincode", "soil_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mark all as required
        for field in self.fields.values():
            field.required = True
            field.widget.attrs.update({
                "class": "w-full bg-slate-50 border-2 border-slate-200 rounded-lg p-3.5 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all duration-200",
            })

        # Custom placeholders
        self.fields["mobile"].widget.attrs.update({"placeholder": "9876543210", "maxlength": "10"})
        self.fields["name"].widget.attrs.update({"placeholder": "നിങ്ങളുടെ പൂർണ്ണ പേര്"})
        self.fields["pincode"].widget.attrs.update({"placeholder": "695001", "maxlength": "6"})
