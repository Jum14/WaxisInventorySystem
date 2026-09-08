from django.contrib import admin
from .models import ProcurementRequest

@admin.register(ProcurementRequest)
class ProcurementRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "ingredient", "supplier", "requested_quantity", "unit_price", "priority", "status", "expected_delivery_date", "actual_delivery_date", "auto_generated", "requested_by", "created_at")
    list_filter = ("status", "priority", "auto_generated")
    search_fields = ("ingredient__name", "supplier__company_name", "requested_by__username")
    list_display_links = ("id", "ingredient")