from django.urls import path
from .views import procurement_list, create_request, approve, reject, mark_ordered, mark_delivered, po_email_draft

urlpatterns = [
    path("", procurement_list, name="procurement"),
    path("create/", create_request, name="procurement_create"),
    path("<int:pk>/approve/", approve, name="procurement_approve"),
    path("<int:pk>/reject/", reject, name="procurement_reject"),
    path("<int:pk>/ordered/", mark_ordered, name="procurement_ordered"),
    path("<int:pk>/delivered/", mark_delivered, name="procurement_delivered"),
    path("<int:pk>/email/", po_email_draft, name="procurement_email"),
]