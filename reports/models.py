from django.db import models

from forecasting.models import AIProcurementAlert
from inventory.models import Ingredient


class AIVarianceLog(models.Model):
    """
    Logs AI predicted stockout vs actual zero date for accuracy tracking.
    Related to AIProcurementAlert and Ingredient for executive reporting.
    """
    alert = models.ForeignKey(
        AIProcurementAlert, on_delete=models.CASCADE, related_name="variance_logs", null=True, blank=True
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="variance_logs")
    predicted_stockout_date = models.DateField()
    actual_zero_date = models.DateField()
    variance_days = models.IntegerField(help_text="actual - predicted (positive = AI early, negative = AI late)")
    predicted_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["ingredient", "created_at"])]

    def save(self, *args, **kwargs):
        if self.predicted_stockout_date and self.actual_zero_date:
            self.variance_days = (self.actual_zero_date - self.predicted_stockout_date).days
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Variance {self.ingredient.name}: {self.variance_days} days"
