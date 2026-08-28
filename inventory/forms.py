from django import forms
from .models import Ingredient, StockTransaction

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = [
            "name", "category", "quantity", "unit",
            "minimum_stock", "maximum_stock",
            "supplier", "expiration_date",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "minimum_stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "maximum_stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "supplier": forms.TextInput(attrs={"class": "form-control"}),
            "expiration_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

class StockDeductionForm(forms.Form):
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-lg"})
    )
    quantity = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control form-control-lg", "step": "0.01", "min": "0.01"})
    )
    reason = forms.ChoiceField(
        choices=[
            ("ORDER_PREPARATION", "Order Preparation"),
            ("SPOILAGE", "Spoilage"),
            ("DAMAGED", "Damaged"),
            ("OTHER", "Other"),
        ],
        widget=forms.Select(attrs={"class": "form-select form-select-lg"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingredient"].queryset = Ingredient.objects.order_by("name")