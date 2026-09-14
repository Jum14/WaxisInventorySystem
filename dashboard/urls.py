from django.urls import path
from .views import home, ai_summary_view

app_name = "dashboard"

urlpatterns = [
    path("", home, name="home"),
    path("ai-summary/", ai_summary_view, name="ai_summary"),
]
