from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("dashboard.urls")),
    path("inventory/", include("inventory.urls")),
    path("procurement/", include("procurement.urls")),
    path("forecast/", include("forecasting.urls")),
    path("reports/", include("reports.urls")),
    path("audit/", include("audit.urls")),
    path("suppliers/", include("suppliers.urls")),
]
