from django.shortcuts import render
from accounts.decorators import role_required
from accounts.models import Profile
from .models import AuditLog

@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def logs(request):
    logs_qs = AuditLog.objects.select_related("user").all()[:300]
    return render(request, "audit/logs.html", {"logs": logs_qs})