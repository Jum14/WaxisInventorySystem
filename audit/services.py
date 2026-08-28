from .models import AuditLog

def log_action(user, action, module, object_id="", details="", status="SUCCESS"):
    return AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        object_id=str(object_id),
        details=details,
        status=status,
    )