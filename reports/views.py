import json

from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from accounts.decorators import role_required
from accounts.models import Profile
from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest

@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def reports(request):
    ingredients = Ingredient.objects.select_related("supplier_fk").all()
    transactions = StockTransaction.objects.select_related("ingredient", "user")
    procurements = ProcurementRequest.objects.select_related("ingredient", "supplier")

    # Aggregations for charts
    by_category = list(Ingredient.objects.values("category").annotate(count=Count("id")).order_by("category"))
    by_status = {
        "GOOD": sum(1 for i in ingredients if i.status == "GOOD"),
        "LOW": sum(1 for i in ingredients if i.status == "LOW"),
        "CRITICAL": sum(1 for i in ingredients if i.status == "CRITICAL"),
        "OUT": sum(1 for i in ingredients if i.status == "OUT"),
    }
    # Last 7 days transaction volume
    since = timezone.now() - timedelta(days=7)
    daily = (
        transactions.filter(created_at__gte=since)
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    # Brand palette mapping for charts
    chart_category = json.dumps({"labels": [d["category"] for d in by_category], "counts": [d["count"] for d in by_category], "colors": ["#FE5F10", "#871F09", "#FED216"][:len(by_category)]})
    chart_status = json.dumps({"labels": list(by_status.keys()), "counts": list(by_status.values()), "colors": ["#198754", "#FED216", "#FE5F10", "#6c757d"]})

    return render(request, "reports/dashboard.html", {
        "ingredients": ingredients,
        "transactions": transactions.order_by("-created_at")[:100],
        "procurements": procurements.order_by("-created_at")[:50],
        "total_ingredients": ingredients.count(),
        "total_transactions": transactions.count(),
        "total_procurements": procurements.count(),
        "by_category": by_category,
        "by_status": by_status,
        "chart_category": chart_category,
        "chart_status": chart_status,
        "daily": list(daily),
    })