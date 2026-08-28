from django.shortcuts import render
from accounts.decorators import role_required
from accounts.models import Profile
from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest

@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def reports(request):
    ingredients = Ingredient.objects.all()
    transactions = StockTransaction.objects.select_related("ingredient", "user")
    procurements = ProcurementRequest.objects.select_related("ingredient")

    return render(request, "reports/dashboard.html", {
        "ingredients": ingredients,
        "transactions": transactions[:100],
        "procurements": procurements[:50],
        "total_ingredients": ingredients.count(),
        "total_transactions": transactions.count(),
        "total_procurements": procurements.count(),
    })