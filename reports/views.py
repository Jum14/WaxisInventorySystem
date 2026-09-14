import csv
import json
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Profile
from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest
from suppliers.models import Supplier


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def reports(request):
    ingredients = Ingredient.objects.select_related("supplier_fk").all()
    transactions = StockTransaction.objects.select_related("ingredient", "user")
    procurements = ProcurementRequest.objects.select_related("ingredient", "supplier")
    suppliers = Supplier.objects.filter(is_active=True)

    # Aggregations for charts
    by_category = list(Ingredient.objects.values("category").annotate(count=Count("id")).order_by("category"))
    by_status = {
        "GOOD": sum(1 for i in ingredients if i.status == "GOOD"),
        "LOW": sum(1 for i in ingredients if i.status == "LOW"),
        "CRITICAL": sum(1 for i in ingredients if i.status == "CRITICAL"),
        "OUT": sum(1 for i in ingredients if i.status == "OUT"),
    }
    since = timezone.now() - timedelta(days=7)
    daily = (
        transactions.filter(created_at__gte=since)
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    chart_category = json.dumps({"labels": [d["category"] for d in by_category], "counts": [d["count"] for d in by_category], "colors": ["#FE5F10", "#871F09", "#FED216"][:len(by_category)]})
    chart_status = json.dumps({"labels": list(by_status.keys()), "counts": list(by_status.values()), "colors": ["#198754", "#FED216", "#FE5F10", "#6c757d"]})

    # === Executive metrics ===

    # 1. Total inventory value: sum(quantity * unit_cost)
    total_inventory_value = (
        Ingredient.objects.aggregate(
            total=Sum(ExpressionWrapper(F("quantity") * F("unit_cost"), output_field=DecimalField(max_digits=20, decimal_places=2)))
        )["total"]
        or Decimal("0.00")
    )

    # 2. Monthly expenditure (this month delivered/ordered/approved)
    now = timezone.now()
    monthly_qs = ProcurementRequest.objects.filter(
        created_at__year=now.year, created_at__month=now.month
    ).exclude(status=ProcurementRequest.Status.REJECTED)
    # Prefer unit_price if set, else ingredient unit_cost
    monthly_expenditure = Decimal("0.00")
    for pr in monthly_qs.select_related("ingredient"):
        price = pr.unit_price if pr.unit_price and pr.unit_price > 0 else (pr.ingredient.unit_cost or Decimal("0"))
        monthly_expenditure += (pr.requested_quantity or Decimal("0")) * price
    # Alternative aggregate fallback if needed: already computed above

    # 3. Spoilage rate (SDG 12) - % of transactions that are Spoilage/Damaged
    total_tx = transactions.count()
    if total_tx:
        spoilage_tx = transactions.filter(
            Q(transaction_type=StockTransaction.Type.SPOILAGE) | Q(reason__in=[StockTransaction.Reason.SPOILAGE_WASTE, StockTransaction.Reason.DAMAGED])
        ).count()
        spoilage_rate = round(spoilage_tx / total_tx * 100, 1)
    else:
        spoilage_rate = 0.0

    # 4. Fast movers - Top 5 deducted this month
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fast_movers_qs = (
        StockTransaction.objects.filter(
            transaction_type__in=[StockTransaction.Type.DEDUCTED, StockTransaction.Type.SPOILAGE],
            created_at__gte=month_start,
        )
        .values("ingredient__name", "ingredient__unit")
        .annotate(total_deducted=Sum("quantity"))
        .order_by("-total_deducted")[:5]
    )
    # Map to template shape {name, unit, total_deducted}
    fast_movers = [
        {"name": r["ingredient__name"], "unit": r["ingredient__unit"], "total_deducted": r["total_deducted"]}
        for r in fast_movers_qs
    ]

    # 5. Supplier metrics - avg delay days
    supplier_metrics = []
    for sup in suppliers:
        delivered = ProcurementRequest.objects.filter(
            supplier=sup, status=ProcurementRequest.Status.DELIVERED,
            expected_delivery_date__isnull=False, actual_delivery_date__isnull=False
        )
        if not delivered.exists():
            # Fallback to legacy expected_date if new field empty
            delivered = ProcurementRequest.objects.filter(
                supplier=sup, status=ProcurementRequest.Status.DELIVERED,
                expected_date__isnull=False, actual_delivery_date__isnull=False
            )
            # Map legacy
            if not delivered.exists():
                continue
            # Use expected_date as expected_delivery_date alias
            avg_delay_days = 0
            delays = []
            for pr in delivered:
                exp = pr.expected_delivery_date or pr.expected_date
                act = pr.actual_delivery_date
                if exp and act:
                    delays.append((act - exp).days)
            avg_delay = sum(delays) / len(delays) if delays else 0
        else:
            delays = [(pr.actual_delivery_date - pr.expected_delivery_date).days for pr in delivered if pr.expected_delivery_date and pr.actual_delivery_date]
            avg_delay = sum(delays) / len(delays) if delays else 0

        supplier_metrics.append({
            "name": sup.company_name,
            "actual_lead_time": round(avg_delay, 1),
            "is_reliable": avg_delay <= 2,  # reliable if avg delay <=2 days
            "delay_days": avg_delay,
        })
    # If no delivered data, show suppliers with lead_time as placeholder
    if not supplier_metrics and suppliers.exists():
        for sup in suppliers[:5]:
            supplier_metrics.append({
                "name": sup.company_name,
                "actual_lead_time": sup.lead_time_days,
                "is_reliable": True,
                "delay_days": 0,
            })

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
        # Executive
        "total_inventory_value": total_inventory_value,
        "monthly_expenditure": monthly_expenditure,
        "spoilage_rate": spoilage_rate,
        "fast_movers": fast_movers,
        "supplier_metrics": supplier_metrics,
    })


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def reports_export(request):
    """CSV export for executive report data."""
    ingredients = Ingredient.objects.all()
    now = timezone.now()
    total_inventory_value = (
        Ingredient.objects.aggregate(
            total=Sum(ExpressionWrapper(F("quantity") * F("unit_cost"), output_field=DecimalField(max_digits=20, decimal_places=2)))
        )["total"]
        or Decimal("0.00")
    )
    monthly_qs = ProcurementRequest.objects.filter(
        created_at__year=now.year, created_at__month=now.month
    ).exclude(status=ProcurementRequest.Status.REJECTED)
    monthly_expenditure = Decimal("0.00")
    for pr in monthly_qs.select_related("ingredient"):
        price = pr.unit_price if pr.unit_price and pr.unit_price > 0 else (pr.ingredient.unit_cost or Decimal("0"))
        monthly_expenditure += (pr.requested_quantity or Decimal("0")) * price

    total_tx = StockTransaction.objects.count()
    spoilage_tx = StockTransaction.objects.filter(
        Q(transaction_type=StockTransaction.Type.SPOILAGE) | Q(reason__in=[StockTransaction.Reason.SPOILAGE_WASTE, StockTransaction.Reason.DAMAGED])
    ).count()
    spoilage_rate = round(spoilage_tx / total_tx * 100, 1) if total_tx else 0

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fast_movers = (
        StockTransaction.objects.filter(
            transaction_type__in=[StockTransaction.Type.DEDUCTED, StockTransaction.Type.SPOILAGE],
            created_at__gte=month_start,
        )
        .values("ingredient__name", "ingredient__unit")
        .annotate(total_deducted=Sum("quantity"))
        .order_by("-total_deducted")[:5]
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="inventiq_report_{now:%Y%m%d}.csv"'

    writer = csv.writer(response)
    writer.writerow(["INVENTIQ Executive Report", f"{now:%Y-%m-%d}"])
    writer.writerow([])
    writer.writerow(["Total Inventory Value (PHP)", f"{total_inventory_value:.2f}"])
    writer.writerow(["Monthly Expenditure (PHP)", f"{monthly_expenditure:.2f}"])
    writer.writerow(["Spoilage & Waste Rate (%)", f"{spoilage_rate}"])
    writer.writerow([])
    writer.writerow(["Top 5 Fast-Movers (This Month)"])
    writer.writerow(["Ingredient", "Total Deducted", "Unit"])
    for fm in fast_movers:
        writer.writerow([fm["ingredient__name"], f"{fm['total_deducted']}", fm["ingredient__unit"]])
    writer.writerow([])
    writer.writerow(["Supplier Fulfillment Reliability"])
    writer.writerow(["Supplier", "Avg Delay (days)", "Status"])
    for sup in Supplier.objects.filter(is_active=True)[:10]:
        delivered = ProcurementRequest.objects.filter(supplier=sup, status=ProcurementRequest.Status.DELIVERED, expected_delivery_date__isnull=False, actual_delivery_date__isnull=False)
        if delivered.exists():
            delays = [(pr.actual_delivery_date - pr.expected_delivery_date).days for pr in delivered if pr.expected_delivery_date and pr.actual_delivery_date]
            avg = sum(delays) / len(delays) if delays else 0
        else:
            avg = 0
        writer.writerow([sup.company_name, f"{avg:.1f}", "Reliable" if avg <= 2 else "Delayed"])
    return response
