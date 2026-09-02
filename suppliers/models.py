from django.db import models


class Supplier(models.Model):
    class Category(models.TextChoices):
        MEAT = "MEAT", "Meat & Poultry"
        PRODUCE = "PRODUCE", "Produce"
        DAIRY = "DAIRY", "Dairy"
        DRY = "DRY", "Dry Goods"
        FROZEN = "FROZEN", "Frozen"
        CHILLED = "CHILLED", "Chilled"
        BEVERAGE = "BEVERAGE", "Beverages"
        PACKAGING = "PACKAGING", "Packaging"
        OTHER = "OTHER", "Other"

    company_name = models.CharField(max_length=150, unique=True)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    lead_time_days = models.PositiveIntegerField(default=3, help_text="Average delivery lead time in days")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, help_text="0.00 - 5.00")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name
