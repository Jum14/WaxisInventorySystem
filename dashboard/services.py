from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta

from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest


def storage_distribution():
    qs = Ingredient.objects.values("category").annotate(count=Count("id"), total_qty=Sum("quantity")).order_by("category")
    # Ensure all 3 categories present even if 0
    return list(qs)


def dashboard_context():
    ingredients = list(Ingredient.objects.select_related("supplier_fk").all())
    total = len(ingredients)
    low = sum(1 for i in ingredients if i.status == "LOW")
    critical = sum(1 for i in ingredients if i.status in {"CRITICAL", "OUT"})
    pending = ProcurementRequest.objects.filter(status="PENDING").count()
    ordered = ProcurementRequest.objects.filter(status="ORDERED").count()
    distribution = storage_distribution()
    recent = StockTransaction.objects.select_related("ingredient", "user").order_by("-created_at")[:8]
    # Turnover last 7 days
    since = timezone.now() - timedelta(days=7)
    weekly = StockTransaction.objects.filter(created_at__gte=since).count()
    return {
        "ingredients": ingredients,
        "total": total,
        "low": low,
        "critical": critical,
        "pending": pending,
        "ordered": ordered,
        "distribution": distribution,
        "recent": recent,
        "weekly_movements": weekly,
    }
