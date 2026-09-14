from django.urls import path
from .views import reports, reports_export

urlpatterns = [
    path("", reports, name="reports"),
    path("export/", reports_export, name="reports_export"),
]