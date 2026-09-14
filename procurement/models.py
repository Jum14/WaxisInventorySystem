from django.contrib.auth.models import User
from django.db import models
from inventory.models import Ingredient

class ProcurementRequest(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        ORDERED = "ORDERED", "Ordered"
        DELIVERED = "DELIVERED", "Delivered"

    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name="procurement_requests"
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_requests",
        help_text="Assigned supplier for fulfillment",
    )
    requested_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    delivered_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Actual delivered qty")
    expected_date = models.DateField(null=True, blank=True, help_text="Legacy alias - use expected_delivery_date")
    expected_delivery_date = models.DateField(null=True, blank=True, help_text="Expected supplier delivery")
    actual_delivery_date = models.DateField(null=True, blank=True, help_text="Actual delivery - for reliability metrics")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="PHP per unit at procurement time")
    requested_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="procurement_requests"
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_procurements"
    )
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField(max_length=255, blank=True)
    auto_generated = models.BooleanField(default=False, help_text="Created by AI forecasting")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PR-{self.pk:04d} - {self.ingredient.name}"