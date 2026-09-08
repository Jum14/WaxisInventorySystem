from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models

class Ingredient(models.Model):
    class Category(models.TextChoices):
        DRY = "DRY", "Dry Goods"
        CHILLED = "CHILLED", "Chilled Products"
        FROZEN = "FROZEN", "Frozen Products"

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=Category.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="kg")
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maximum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="PHP per unit - for inventory valuation")
    # Legacy free-text supplier kept for backward compat during migration, new FK preferred
    supplier = models.CharField(max_length=150, blank=True, help_text="Legacy free-text (migrated to supplier_fk)")
    supplier_fk = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingredients",
        help_text="Linked supplier (preferred)",
    )
    expiration_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def status(self):
        if self.quantity <= 0:
            return "OUT"
        if self.minimum_stock > 0 and self.quantity <= self.minimum_stock * Decimal("0.5"):
            return "CRITICAL"
        if self.minimum_stock > 0 and self.quantity <= self.minimum_stock:
            return "LOW"
        return "GOOD"

    @property
    def status_label(self):
        return {
            "OUT": "Out of Stock",
            "CRITICAL": "Critical",
            "LOW": "Low Stock",
            "GOOD": "In Stock",
        }[self.status]

class StockTransaction(models.Model):
    class Type(models.TextChoices):
        ADDED = "ADDED", "Stock Added"
        DEDUCTED = "DEDUCTED", "Stock Deducted"
        ADJUSTMENT = "ADJUSTMENT", "Stock Adjustment"
        SPOILAGE = "SPOILAGE", "Spoilage"
        RETURN = "RETURN", "Return"

    class Reason(models.TextChoices):
        NORMAL_USAGE = "NORMAL_USAGE", "Normal Usage"
        SPOILAGE_WASTE = "SPOILAGE_WASTE", "Spoilage/Waste"
        DAMAGED = "DAMAGED", "Damaged"
        OTHER = "OTHER", "Other"

    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name="transactions"
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="stock_transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=Type.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    previous_stock = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_stock = models.DecimalField(max_digits=12, decimal_places=2)
    # SDG 12: structured reason for waste tracking
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.NORMAL_USAGE)
    # Keep free-text notes for details
    notes = models.CharField(max_length=255, blank=True, help_text="Additional details")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ingredient} - {self.get_transaction_type_display()}"