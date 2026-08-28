from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Profile
from audit.services import log_action

from .forms import ProcurementForm
from .models import ProcurementRequest


MANAGEMENT = (
    Profile.Role.DEVELOPER,
    Profile.Role.OWNER,
    Profile.Role.MANAGER,
)


@role_required(*MANAGEMENT)
def procurement_list(request):
    requests = ProcurementRequest.objects.select_related(
        "ingredient", "requested_by", "approved_by"
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
    form = ProcurementForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.requested_by = request.user
        obj.save()

        log_action(
            request.user,
            "CREATE",
            "Procurement",
            obj.pk,
            "Procurement request created.",
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
