from django import forms
from .models import ProcurementRequest

class ProcurementForm(forms.ModelForm):
    class Meta:
        model = ProcurementRequest
        fields = ["ingredient", "supplier", "requested_quantity", "expected_delivery_date", "unit_price", "priority", "reason"]
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "requested_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "expected_delivery_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "placeholder": "PHP per unit"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "reason": forms.TextInput(attrs={"class": "form-control", "placeholder": "Why is this needed?"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from suppliers.models import Supplier
            self.fields["supplier"].queryset = Supplier.objects.filter(is_active=True).order_by("company_name")
            self.fields["supplier"].required = False
            self.fields["supplier"].empty_label = "— Select supplier (or leave blank) —"
        except Exception:
            pass
        # Pre-fill supplier from ingredient's linked supplier via JS/GET param handled in view