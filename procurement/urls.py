from django.urls import path
from .views import procurement_list, create_request, approve, reject

urlpatterns = [
    path("", procurement_list, name="procurement"),
    path("create/", create_request, name="procurement_create"),
    path("<int:pk>/approve/", approve, name="procurement_approve"),
    path("<int:pk>/reject/", reject, name="procurement_reject"),
]