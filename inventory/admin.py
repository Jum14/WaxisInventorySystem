from django.contrib import admin
from .models import Ingredient, StockTransaction

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "quantity", "unit", "unit_cost", "minimum_stock", "status", "supplier_fk", "updated_at")
    list_filter = ("category", "supplier_fk")
    search_fields = ("name", "supplier", "supplier_fk__company_name")

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "ingredient", "user", "transaction_type", "quantity", "remaining_stock", "reason")
    list_filter = ("transaction_type", "reason")
    search_fields = ("ingredient__name", "user__username", "reason", "notes")
    readonly_fields = ("created_at",)