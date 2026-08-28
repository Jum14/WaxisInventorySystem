from django.urls import path

from .views import forecast

app_name = "forecasting"

urlpatterns = [
    path("", forecast, name="forecast"),
]
