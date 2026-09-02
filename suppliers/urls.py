from django.urls import path

from .views import supplier_create, supplier_delete, supplier_edit, supplier_list, supplier_toggle

app_name = "suppliers"

urlpatterns = [
    path("", supplier_list, name="list"),
    path("add/", supplier_create, name="create"),
    path("<int:pk>/edit/", supplier_edit, name="edit"),
    path("<int:pk>/toggle/", supplier_toggle, name="toggle"),
    path("<int:pk>/delete/", supplier_delete, name="delete"),
]
