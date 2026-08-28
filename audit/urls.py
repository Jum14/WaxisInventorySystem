from django.urls import path
from .views import logs

urlpatterns = [
    path("", logs, name="audit_logs"),
]