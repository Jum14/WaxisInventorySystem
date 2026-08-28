from django.shortcuts import render
from accounts.decorators import role_required
from accounts.models import Profile
from inventory.models import Ingredient

@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def forecast(request):
    rows = []
    for ingredient in Ingredient.objects.all()[:50]:
        # UI prototype only: replace this calculation with the actual
        # historical-sales/Prophet service in the future.
        daily_usage = max(float(ingredient.quantity) / 7, 0.1)
        days = float(ingredient.quantity) / daily_usage
        reorder = max(float(ingredient.maximum_stock - ingredient.quantity), 0)

        risk = (
            "HIGH" if ingredient.status in {"CRITICAL", "OUT"}
            else "MEDIUM" if ingredient.status == "LOW"
            else "LOW"
        )

        rows.append({
            "ingredient": ingredient,
            "daily": round(daily_usage, 1),
            "days": round(days, 1),
            "reorder": round(reorder, 1),
            "risk": risk,
        })

    return render(request, "forecasting/dashboard.html", {"rows": rows})