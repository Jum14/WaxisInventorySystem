from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from inventory.models import Ingredient, StockTransaction


def daily_usage(ingredient, days=30):
    """
    Compute average daily usage from StockTransaction history.
    Uses DEDUCTED/SPOILAGE in last `days`. Falls back to forecast based on status if no history.
    """
    since = timezone.now() - timedelta(days=days)
    agg = (
        StockTransaction.objects.filter(
            ingredient=ingredient,
            transaction_type__in=[StockTransaction.Type.DEDUCTED, StockTransaction.Type.SPOILAGE],
            created_at__gte=since,
        ).aggregate(total=Sum("quantity"))
    )
    total = agg["total"]
    if total is None:
        # No history: heuristic - if no minimum, small default; else estimate from status
        # Use 0.5 if out/low, else small baseline
        if ingredient.status in {"CRITICAL", "OUT"}:
            return 1.0
        if ingredient.status == "LOW":
            return 0.7
        return 0.3
    total_f = float(total)
    avg = total_f / days if days else total_f
    return max(avg, 0.1)


def forecast_row(ingredient, days_window=30):
    usage = daily_usage(ingredient, days=days_window)
    qty_f = float(ingredient.quantity)
    days_left = qty_f / usage if usage > 0 else 999
    # Reorder suggestion: fill to maximum_stock, or if max is 0, suggest 7*usage
    if float(ingredient.maximum_stock) > 0:
        reorder = max(float(ingredient.maximum_stock - ingredient.quantity), 0)
    else:
        # Default 7 days of usage
        reorder = max(usage * 7 - qty_f, 0)
    # Risk: HIGH if critical/out or days_left < 3, MEDIUM if low or days_left < 7
    if ingredient.status in {"CRITICAL", "OUT"} or days_left < 3:
        risk = "HIGH"
    elif ingredient.status == "LOW" or days_left < 7:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    # Predicted stockout date
    stockout_date = timezone.now().date() + timedelta(days=int(days_left)) if days_left < 365 else None

    return {
        "ingredient": ingredient,
        "daily": round(usage, 2),
        "days": round(days_left, 1),
        "reorder": round(reorder, 2),
        "risk": risk,
        "stockout_date": stockout_date,
    }


def generate_all_forecasts(days_window=30):
    ingredients = Ingredient.objects.select_related("supplier_fk").all()
    rows = [forecast_row(ing, days_window=days_window) for ing in ingredients]
    # Sort HIGH risk first, then shortest days
    rows.sort(key=lambda r: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[r["risk"]], r["days"]))
    return rows
