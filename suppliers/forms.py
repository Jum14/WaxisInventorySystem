from django import forms

from .models import Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "company_name",
            "contact_person",
            "email",
            "phone",
            "address",
            "category",
            "lead_time_days",
            "rating",
            "is_active",
            "notes",
        ]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Waxi's Meat Supplier Inc."}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "supplier@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "lead_time_days": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "rating": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "5"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
