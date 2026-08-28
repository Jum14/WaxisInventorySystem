from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import Profile
from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest


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
    ingredients = list(Ingredient.objects.all())
    return {
        "ingredients": ingredients,
        "total": len(ingredients),
        "low": sum(i.status == "LOW" for i in ingredients),
        "critical": sum(i.status in {"CRITICAL", "OUT"} for i in ingredients),
    }


@login_required
def manager_dashboard(request):
    summary = _inventory_summary()
    return render(request, "dashboard/manager.html", {
        **summary,
        "pending": ProcurementRequest.objects.filter(status="PENDING").count(),
        "transactions": StockTransaction.objects.select_related("ingredient", "user")[:8],
    })


@login_required
def owner_dashboard(request):
    summary = _inventory_summary()
    return render(request, "dashboard/owner.html", {
        **summary,
        "pending": ProcurementRequest.objects.filter(status="PENDING").count(),
        "transactions": StockTransaction.objects.select_related("ingredient", "user")[:10],
    })


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
