import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import Profile
from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest

from .services import dashboard_context
from procurement.services import generate_executive_summary
from forecasting.services import generate_all_forecasts


@login_required
def home(request):
    """Route each authenticated user to the dashboard for their role."""
    role = getattr(getattr(request.user, "profile", None), "role", None)

    if role == Profile.Role.DEVELOPER:
        return redirect("/admin/")
    if role == Profile.Role.OWNER:
        return owner_dashboard(request)
    if role == Profile.Role.MANAGER:
        return manager_dashboard(request)
    return crew_dashboard(request)


def _inventory_summary():
    ingredients = list(Ingredient.objects.select_related("supplier_fk").all())
    return {
        "ingredients": ingredients,
        "total": len(ingredients),
        "low": sum(i.status == "LOW" for i in ingredients),
        "critical": sum(i.status in {"CRITICAL", "OUT"} for i in ingredients),
    }


def _chart_data(distribution):
    labels = [d["category"] for d in distribution]
    counts = [d["count"] for d in distribution]
    # Map friendly labels
    label_map = {"DRY": "Dry", "CHILLED": "Chilled", "FROZEN": "Frozen"}
    labels = [label_map.get(l, l) for l in labels]
    return json.dumps({"labels": labels, "counts": counts})


@login_required
def manager_dashboard(request):
    ctx = dashboard_context()
    ai_summary = None
    if request.GET.get("ai") == "1":
        snap = {"total": ctx["total"], "low": ctx["low"], "critical": ctx["critical"], "pending": ctx["pending"], "distribution": ctx["distribution"]}
        ai_summary = generate_executive_summary(snap)
    return render(request, "dashboard/manager.html", {
        "ingredients": ctx["ingredients"],
        "total": ctx["total"],
        "low": ctx["low"],
        "critical": ctx["critical"],
        "pending": ctx["pending"],
        "ordered": ctx["ordered"],
        "transactions": ctx["recent"],
        "distribution": ctx["distribution"],
        "chart_data": _chart_data(ctx["distribution"]),
        "weekly_movements": ctx["weekly_movements"],
        "ai_summary": ai_summary,
    })


@login_required
def owner_dashboard(request):
    ctx = dashboard_context()
    # Owner always gets AI summary (cached per request)
    snap = {"total": ctx["total"], "low": ctx["low"], "critical": ctx["critical"], "pending": ctx["pending"], "distribution": ctx["distribution"]}
    # Only call Gemini if ?ai param or on demand to save quota - here auto on owner
    ai_summary = None
    if request.GET.get("ai") != "0":
        try:
            ai_summary = generate_executive_summary(snap)
        except Exception:
            ai_summary = None
    # Forecast highlights for owner
    try:
        forecast_rows = generate_all_forecasts()[:5]
    except Exception:
        forecast_rows = []
    return render(request, "dashboard/owner.html", {
        "ingredients": ctx["ingredients"],
        "total": ctx["total"],
        "low": ctx["low"],
        "critical": ctx["critical"],
        "pending": ctx["pending"],
        "ordered": ctx["ordered"],
        "transactions": StockTransaction.objects.select_related("ingredient", "user").order_by("-created_at")[:10],
        "distribution": ctx["distribution"],
        "chart_data": _chart_data(ctx["distribution"]),
        "weekly_movements": ctx["weekly_movements"],
        "ai_summary": ai_summary,
        "forecast_highlights": forecast_rows,
    })


@login_required
def ai_summary_view(request):
    ctx = dashboard_context()
    snap = {"total": ctx["total"], "low": ctx["low"], "critical": ctx["critical"], "pending": ctx["pending"], "distribution": ctx["distribution"]}
    summary = generate_executive_summary(snap)
    if request.htmx:
        return render(request, "dashboard/_ai_summary.html", {"ai_summary": summary})
    messages.info(request, summary)
    return redirect("dashboard:home")


@login_required
def crew_dashboard(request):
    transactions = StockTransaction.objects.filter(
        user=request.user
    ).select_related("ingredient")[:10]

    low = [
        i for i in Ingredient.objects.all()
        if i.status in {"LOW", "CRITICAL", "OUT"}
    ]

    return render(request, "dashboard/crew.html", {
        "transactions": transactions,
        "low": low,
        "today_count": StockTransaction.objects.filter(user=request.user).count(),
    })
