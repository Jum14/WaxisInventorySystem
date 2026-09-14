from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Profile
from audit.services import log_action

from .forms import SupplierForm
from .models import Supplier

MANAGEMENT = (Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)


@role_required(*MANAGEMENT)
def supplier_list(request):
    qs = Supplier.objects.all()
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")

    if q:
        qs = qs.filter(
            Q(company_name__icontains=q)
            | Q(contact_person__icontains=q)
            | Q(email__icontains=q)
        )
    if category:
        qs = qs.filter(category=category)
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)

    # HTMX partial for autocomplete/search
    if request.htmx:
        return render(request, "suppliers/_list_rows.html", {"suppliers": qs})

    return render(
        request,
        "suppliers/list.html",
        {
            "suppliers": qs,
            "categories": Supplier.Category.choices,
            "selected_category": category,
            "selected_status": status,
            "query": q,
        },
    )


@role_required(*MANAGEMENT)
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        supplier = form.save()
        log_action(request.user, "CREATE", "Suppliers", supplier.pk, f"Supplier {supplier.company_name} created.")
        messages.success(request, f"Supplier '{supplier.company_name}' added.")
        return redirect("suppliers:list")
    return render(request, "suppliers/form.html", {"form": form, "title": "Add Supplier"})


@role_required(*MANAGEMENT)
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        supplier = form.save()
        log_action(request.user, "UPDATE", "Suppliers", supplier.pk, f"Supplier {supplier.company_name} updated.")
        messages.success(request, "Supplier updated.")
        return redirect("suppliers:list")
    return render(request, "suppliers/form.html", {"form": form, "title": "Edit Supplier", "supplier": supplier})


@role_required(*MANAGEMENT)
def supplier_toggle(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = not supplier.is_active
    supplier.save(update_fields=["is_active", "updated_at"])
    status = "activated" if supplier.is_active else "deactivated"
    log_action(request.user, "TOGGLE", "Suppliers", supplier.pk, f"Supplier {status}.")
    messages.success(request, f"Supplier '{supplier.company_name}' {status}.")
    return redirect("suppliers:list")


@role_required(*MANAGEMENT)
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == "POST":
        name = supplier.company_name
        supplier.delete()
        log_action(request.user, "DELETE", "Suppliers", pk, f"Supplier {name} deleted.")
        messages.success(request, f"Supplier '{name}' deleted.")
        return redirect("suppliers:list")
    return render(request, "suppliers/confirm_delete.html", {"supplier": supplier})
