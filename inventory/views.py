from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Profile
from audit.services import log_action
from .forms import IngredientForm, StockDeductionForm
from .models import Ingredient, StockTransaction

def can_manage_inventory(user):
    role = getattr(getattr(user, "profile", None), "role", None)
    return role in {
        Profile.Role.DEVELOPER,
        Profile.Role.OWNER,
        Profile.Role.MANAGER,
    }

@login_required
def inventory_list(request):
    ingredients = Ingredient.objects.select_related("supplier_fk").all()
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")

    if q:
        ingredients = ingredients.filter(
            Q(name__icontains=q) | Q(supplier__icontains=q) | Q(supplier_fk__company_name__icontains=q)
        )
    if category:
        ingredients = ingredients.filter(category=category)

    ingredients = list(ingredients)
    if status:
        ingredients = [item for item in ingredients if item.status == status]

    # HTMX partial search - return only table rows
    if request.htmx:
        return render(request, "inventory/_list_rows.html", {
            "ingredients": ingredients,
        })

    return render(request, "inventory/list.html", {
        "ingredients": ingredients,
        "categories": Ingredient.Category.choices,
        "selected_category": category,
        "selected_status": status,
        "query": q,
        "can_manage": can_manage_inventory(request.user),
    })


@login_required
def inventory_search_partial(request):
    """HTMX endpoint for live search autocomplete - returns filtered rows as HTML fragment."""
    q = request.GET.get("q", "").strip()
    qs = Ingredient.objects.select_related("supplier_fk").order_by("name")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(supplier__icontains=q) | Q(supplier_fk__company_name__icontains=q))[:10]
    else:
        qs = qs[:10]
    return render(request, "inventory/_search_results.html", {"ingredients": qs, "query": q})

@login_required
def ingredient_detail(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    transactions = ingredient.transactions.select_related("user")[:50]
    return render(request, "inventory/detail.html", {
        "ingredient": ingredient,
        "transactions": transactions,
        "can_manage": can_manage_inventory(request.user),
    })

@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def ingredient_create(request):
    form = IngredientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ingredient = form.save()
        log_action(
            request.user, "CREATE", "Inventory", ingredient.pk,
            f"Ingredient {ingredient.name} created."
        )
        messages.success(request, f"{ingredient.name} added to inventory.")
        return redirect("inventory")
    return render(request, "inventory/form.html", {"form": form, "title": "Add Ingredient"})

@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def ingredient_edit(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    form = IngredientForm(request.POST or None, instance=ingredient)
    if request.method == "POST" and form.is_valid():
        ingredient = form.save()
        log_action(
            request.user, "UPDATE", "Inventory", ingredient.pk,
            f"Ingredient {ingredient.name} updated."
        )
        messages.success(request, "Ingredient updated.")
        return redirect("ingredient_detail", pk=ingredient.pk)
    return render(request, "inventory/form.html", {"form": form, "title": "Edit Ingredient", "ingredient": ingredient})

@login_required
def transactions(request):
    qs = StockTransaction.objects.select_related("ingredient", "user")
    role = getattr(getattr(request.user, "profile", None), "role", None)
    if role == Profile.Role.CREW:
        qs = qs.filter(user=request.user)
    return render(request, "inventory/transactions.html", {"transactions": qs[:300]})

@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER, Profile.Role.CREW)
def deduct_stock(request):
    form = StockDeductionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ingredient_id = form.cleaned_data["ingredient"].pk
        amount = form.cleaned_data["quantity"]
        reason = form.cleaned_data["reason"]

        with transaction.atomic():
            ingredient = Ingredient.objects.select_for_update().get(pk=ingredient_id)
            if amount > ingredient.quantity:
                form.add_error("quantity", f"Only {ingredient.quantity} {ingredient.unit} is currently available.")
            else:
                previous = ingredient.quantity
                ingredient.quantity = ingredient.quantity - amount
                ingredient.save(update_fields=["quantity", "updated_at"])

                # Map reason to transaction_type for SDG 12 tracking
                tx_type = StockTransaction.Type.DEDUCTED
                if reason in ("SPOILAGE_WASTE", "DAMAGED"):
                    tx_type = StockTransaction.Type.SPOILAGE
                # Also detect if ingredient hit zero for AI variance logging
                hit_zero = ingredient.quantity == 0
                actual_zero_date = None
                if hit_zero:
                    from django.utils import timezone
                    actual_zero_date = timezone.now().date()

                StockTransaction.objects.create(
                    ingredient=ingredient,
                    user=request.user,
                    transaction_type=tx_type,
                    quantity=amount,
                    previous_stock=previous,
                    remaining_stock=ingredient.quantity,
                    reason=reason,
                    notes=reason.replace("_", " ").title(),
                )
                # Log AI variance if hit zero
                if hit_zero and actual_zero_date:
                    try:
                        from forecasting.models import AIProcurementAlert
                        pending = AIProcurementAlert.objects.filter(
                            ingredient=ingredient, predicted_stockout_date__isnull=False, actual_zero_date__isnull=True
                        ).order_by("-created_at").first()
                        if pending:
                            pending.actual_zero_date = actual_zero_date
                            pending.save(update_fields=["actual_zero_date", "variance_days", "updated_at"])
                    except Exception:
                        pass

                log_action(
                    request.user,
                    "STOCK DEDUCTION",
                    "Inventory",
                    ingredient.pk,
                    f"{ingredient.name}: {previous} {ingredient.unit} -> {ingredient.quantity} {ingredient.unit}; quantity deducted: {amount} {ingredient.unit}.",
                )

                if ingredient.status in {"LOW", "CRITICAL", "OUT"}:
                    messages.warning(
                        request,
                        f"{ingredient.name} is now {ingredient.status_label.lower()}.",
                    )
                else:
                    messages.success(request, "Stock deduction recorded successfully.")

                return redirect("transactions")

    return render(request, "inventory/deduct.html", {"form": form})