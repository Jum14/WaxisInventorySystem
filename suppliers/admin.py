from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("company_name", "category", "contact_person", "email", "phone", "lead_time_days", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("company_name", "contact_person", "email")
    list_editable = ("is_active",)
