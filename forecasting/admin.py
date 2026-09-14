from django.contrib import admin

from .models import AIProcurementAlert


@admin.register(AIProcurementAlert)
class AIProcurementAlertAdmin(admin.ModelAdmin):
    list_display = ("id", "ingredient", "risk", "days_until_stockout", "suggested_quantity", "status", "created_at")
    list_filter = ("risk", "status")
    search_fields = ("ingredient__name", "reason")
    readonly_fields = ("created_at", "updated_at")
