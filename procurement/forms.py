from django import forms
from .models import ProcurementRequest

class ProcurementForm(forms.ModelForm):
    class Meta:
        model = ProcurementRequest
        fields = ["ingredient", "requested_quantity", "priority", "reason"]
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-select"}),
            "requested_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "reason": forms.TextInput(attrs={"class": "form-control", "placeholder": "Why is this needed?"}),
        }