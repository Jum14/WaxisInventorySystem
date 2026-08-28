from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "module", "status")
    list_filter = ("module", "action", "status")
    search_fields = ("user__username", "details", "object_id")
    readonly_fields = ("timestamp",)