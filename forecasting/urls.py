from django.urls import path

from .views import forecast, generate_alerts, alerts_list, alert_approve, alert_reject

app_name = "forecasting"

urlpatterns = [
    path("", forecast, name="forecast"),
    path("alerts/", alerts_list, name="alerts"),
    path("generate/", generate_alerts, name="generate_alerts"),
    path("alerts/<int:pk>/approve/", alert_approve, name="alert_approve"),
    path("alerts/<int:pk>/reject/", alert_reject, name="alert_reject"),
]
