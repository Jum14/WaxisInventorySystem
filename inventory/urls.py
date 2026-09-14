from django.urls import path
from .views import (
    inventory_list, ingredient_detail, ingredient_create,
    ingredient_edit, transactions, deduct_stock, inventory_search_partial
)

urlpatterns = [
    path("", inventory_list, name="inventory"),
    path("search-partial/", inventory_search_partial, name="inventory_search_partial"),
    path("transactions/", transactions, name="transactions"),
    path("deduct/", deduct_stock, name="deduct_stock"),
    path("add/", ingredient_create, name="ingredient_create"),
    path("<int:pk>/", ingredient_detail, name="ingredient_detail"),
    path("<int:pk>/edit/", ingredient_edit, name="ingredient_edit"),
]