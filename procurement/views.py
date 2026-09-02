from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Profile
from audit.services import log_action
from inventory.models import Ingredient, StockTransaction

from .forms import ProcurementForm
from .models import ProcurementRequest
from .services import generate_po_email


MANAGEMENT = (
    Profile.Role.DEVELOPER,
    Profile.Role.OWNER,
    Profile.Role.MANAGER,
)


@role_required(*MANAGEMENT)
def procurement_list(request):
    requests = ProcurementRequest.objects.select_related(
        "ingredient", "supplier", "requested_by", "approved_by"
    )

    return render(request, "procurement/list.html", {
        "requests": requests[:300],
        "pending": requests.filter(status=ProcurementRequest.Status.PENDING).count(),
        "approved": requests.filter(status=ProcurementRequest.Status.APPROVED).count(),
        "ordered": requests.filter(status=ProcurementRequest.Status.ORDERED).count(),
        "delivered": requests.filter(status=ProcurementRequest.Status.DELIVERED).count(),
    })


@role_required(*MANAGEMENT)
def create_request(request):
    initial = {}
    ing_id = request.GET.get("ingredient")
    qty = request.GET.get("qty")
    if ing_id:
        initial["ingredient"] = ing_id
    if qty:
        initial["requested_quantity"] = qty
    # Auto-fill supplier from ingredient's supplier_fk if not supplied
    if ing_id and not request.POST.get("supplier"):
        try:
            ing = Ingredient.objects.select_related("supplier_fk").get(pk=ing_id)
            if ing.supplier_fk:
                initial["supplier"] = ing.supplier_fk
        except Ingredient.DoesNotExist:
            pass

    form = ProcurementForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.requested_by = request.user
        # If supplier blank but ingredient has linked supplier, auto-assign
        if not obj.supplier and obj.ingredient and getattr(obj.ingredient, "supplier_fk", None):
            obj.supplier = obj.ingredient.supplier_fk
        obj.save()

        log_action(
            request.user,
            "CREATE",
            "Procurement",
            obj.pk,
            f"Procurement request created for {obj.ingredient.name} qty {obj.requested_quantity}.",
        )

        messages.success(request, "Procurement request created.")
        return redirect("procurement")

    return render(request, "procurement/procurement.html", {"form": form})


@role_required(*MANAGEMENT)
def approve(request, pk):
    obj = get_object_or_404(ProcurementRequest, pk=pk)
    obj.status = ProcurementRequest.Status.APPROVED
    obj.approved_by = request.user
    obj.save(update_fields=["status", "approved_by", "updated_at"])

    log_action(request.user, "APPROVE", "Procurement", obj.pk, "Request approved.")
    messages.success(request, "Procurement request approved.")

    return redirect("procurement")


@role_required(*MANAGEMENT)
def reject(request, pk):
    obj = get_object_or_404(ProcurementRequest, pk=pk)
    obj.status = ProcurementRequest.Status.REJECTED
    obj.approved_by = request.user
    obj.save(update_fields=["status", "approved_by", "updated_at"])

    log_action(request.user, "REJECT", "Procurement", obj.pk, "Request rejected.")
    messages.success(request, "Procurement request rejected.")

    return redirect("procurement")


@role_required(*MANAGEMENT)
def mark_ordered(request, pk):
    obj = get_object_or_404(ProcurementRequest, pk=pk)
    if obj.status not in [ProcurementRequest.Status.APPROVED, ProcurementRequest.Status.PENDING]:
        messages.error(request, f"Cannot mark as ordered from status {obj.get_status_display()}.")
        return redirect("procurement")
    obj.status = ProcurementRequest.Status.ORDERED
    obj.approved_by = obj.approved_by or request.user
    obj.save(update_fields=["status", "approved_by", "updated_at"])
    log_action(request.user, "ORDERED", "Procurement", obj.pk, f"Request marked ordered: {obj.ingredient.name} qty {obj.requested_quantity}.")
    messages.success(request, f"Request PR-{obj.pk:04d} marked as Ordered.")
    return redirect("procurement")


@role_required(*MANAGEMENT)
def mark_delivered(request, pk):
    obj = get_object_or_404(ProcurementRequest.objects.select_related("ingredient", "supplier"), pk=pk)
    if obj.status not in [ProcurementRequest.Status.ORDERED, ProcurementRequest.Status.APPROVED]:
        messages.error(request, f"Cannot mark as delivered from status {obj.get_status_display()}. Approve/Order first.")
        return redirect("procurement")

    # Delivered quantity defaults to requested if not set
    delivered_qty = obj.delivered_quantity if obj.delivered_quantity is not None else obj.requested_quantity
    try:
        delivered_qty = Decimal(delivered_qty)
    except Exception:
        messages.error(request, "Invalid delivered quantity.")
        return redirect("procurement")

    if request.method == "POST":
        # Allow override via POST
        posted_qty = request.POST.get("delivered_quantity")
        if posted_qty:
            try:
                delivered_qty = Decimal(posted_qty)
            except Exception:
                messages.error(request, "Invalid delivered quantity input.")
                return redirect("procurement")

    with transaction.atomic():
        ingredient = Ingredient.objects.select_for_update().get(pk=obj.ingredient_id)
        previous = ingredient.quantity
        ingredient.quantity = ingredient.quantity + delivered_qty
        ingredient.save(update_fields=["quantity", "updated_at"])

        StockTransaction.objects.create(
            ingredient=ingredient,
            user=request.user,
            transaction_type=StockTransaction.Type.ADDED,
            quantity=delivered_qty,
            previous_stock=previous,
            remaining_stock=ingredient.quantity,
            reason=f"Procurement PR-{obj.pk:04d} Delivered",
        )

        obj.status = ProcurementRequest.Status.DELIVERED
        obj.delivered_quantity = delivered_qty
        obj.approved_by = obj.approved_by or request.user
        obj.save(update_fields=["status", "delivered_quantity", "approved_by", "updated_at"])

        log_action(
            request.user,
            "DELIVERED",
            "Procurement",
            obj.pk,
            f"PR-{obj.pk:04d} delivered: {ingredient.name} +{delivered_qty} {ingredient.unit} ({previous} -> {ingredient.quantity}).",
        )

    messages.success(request, f"PR-{obj.pk:04d} delivered: {ingredient.name} restocked +{delivered_qty} {ingredient.unit}.")
    return redirect("procurement")


@role_required(*MANAGEMENT)
def po_email_draft(request, pk):
    obj = get_object_or_404(ProcurementRequest.objects.select_related("ingredient", "supplier", "requested_by"), pk=pk)
    subject, body = generate_po_email(obj)
    return render(request, "procurement/email_draft.html", {"obj": obj, "subject": subject, "body": body})
