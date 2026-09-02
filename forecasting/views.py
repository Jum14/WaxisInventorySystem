from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Profile
from audit.services import log_action
from procurement.models import ProcurementRequest

from .models import AIProcurementAlert
from .services import generate_all_forecasts


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def forecast(request):
    rows = generate_all_forecasts(days_window=30)
    alerts_pending = AIProcurementAlert.objects.filter(status=AIProcurementAlert.Status.PENDING).select_related("ingredient")[:20]

    # Optional filter by risk
    risk_filter = request.GET.get("risk", "")
    if risk_filter:
        rows = [r for r in rows if r["risk"] == risk_filter]

    return render(request, "forecasting/dashboard.html", {
        "rows": rows,
        "alerts": alerts_pending,
        "selected_risk": risk_filter,
        "total_alerts_pending": AIProcurementAlert.objects.filter(status=AIProcurementAlert.Status.PENDING).count(),
    })


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def generate_alerts(request):
    if request.method != "POST":
        return redirect("forecasting:forecast")
    rows = generate_all_forecasts(days_window=30)
    created = 0
    for r in rows:
        if r["risk"] in {"HIGH", "MEDIUM"} and r["reorder"] > 0:
            # Avoid duplicate pending alerts for same ingredient
            exists = AIProcurementAlert.objects.filter(
                ingredient=r["ingredient"], status=AIProcurementAlert.Status.PENDING
            ).exists()
            if exists:
                continue
            reason = f"Predicted stockout in {r['days']} days ({r['daily']}/day usage)"
            if r["ingredient"].status in {"CRITICAL", "OUT"}:
                reason = f"Critical stock: {r['ingredient'].quantity} {r['ingredient'].unit} remaining. " + reason
            AIProcurementAlert.objects.create(
                ingredient=r["ingredient"],
                suggested_quantity=r["reorder"],
                predicted_stockout_date=r["stockout_date"],
                daily_usage=r["daily"],
                days_until_stockout=r["days"],
                risk=r["risk"],
                reason=reason,
                created_by=request.user,
            )
            created += 1
    log_action(request.user, "GENERATE", "Forecasting", "", f"Generated {created} AI alerts.")
    messages.success(request, f"Generated {created} new procurement alerts (HIGH/MEDIUM risk).")
    return redirect("forecasting:forecast")


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def alerts_list(request):
    alerts = AIProcurementAlert.objects.select_related("ingredient", "created_by").order_by("-created_at")[:100]
    return render(request, "forecasting/alerts.html", {"alerts": alerts})


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def alert_approve(request, pk):
    alert = get_object_or_404(AIProcurementAlert, pk=pk)
    # Convert to ProcurementRequest
    req = ProcurementRequest.objects.create(
        ingredient=alert.ingredient,
        supplier=getattr(alert.ingredient, "supplier_fk", None),
        requested_quantity=alert.suggested_quantity,
        priority=ProcurementRequest.Priority.CRITICAL if alert.risk == "HIGH" else ProcurementRequest.Priority.HIGH,
        reason=f"AI Alert: {alert.reason}",
        requested_by=request.user,
        auto_generated=True,
    )
    alert.status = AIProcurementAlert.Status.CONVERTED
    alert.save(update_fields=["status", "updated_at"])
    log_action(request.user, "CONVERT", "Forecasting", alert.pk, f"Alert converted to PR-{req.pk:04d}")
    messages.success(request, f"Alert converted to procurement request PR-{req.pk:04d}.")
    return redirect("forecasting:forecast")


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def alert_reject(request, pk):
    alert = get_object_or_404(AIProcurementAlert, pk=pk)
    alert.status = AIProcurementAlert.Status.REJECTED
    alert.save(update_fields=["status", "updated_at"])
    log_action(request.user, "REJECT", "Forecasting", alert.pk, "AI alert rejected.")
    messages.success(request, "Alert rejected.")
    return redirect("forecasting:forecast")