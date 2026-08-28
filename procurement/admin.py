from django.contrib import admin
from .models import ProcurementRequest

@admin.register(ProcurementRequest)
class ProcurementRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "ingredient", "requested_quantity", "priority", "status", "requested_by", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("ingredient__name", "requested_by__username")