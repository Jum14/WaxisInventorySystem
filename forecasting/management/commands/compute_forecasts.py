from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditLog
from forecasting.models import AIProcurementAlert
from forecasting.services import generate_all_forecasts


class Command(BaseCommand):
    help = "Compute forecasts for all ingredients and generate AI procurement alerts for HIGH/MEDIUM risk items. Intended for cron: 0 2 * * * python manage.py compute_forecasts"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Window days for daily usage calc")
        parser.add_argument("--dry-run", action="store_true", help="Don't create, just report")

    def handle(self, *args, **options):
        days = options["days"]
        dry = options["dry_run"]
        rows = generate_all_forecasts(days_window=days)
        created = 0
        skipped = 0
        for r in rows:
            if r["risk"] in {"HIGH", "MEDIUM"} and r["reorder"] > 0:
                exists = AIProcurementAlert.objects.filter(
                    ingredient=r["ingredient"], status=AIProcurementAlert.Status.PENDING
                ).exists()
                if exists:
                    skipped += 1
                    continue
                if dry:
                    self.stdout.write(f"[DRY] Would create alert {r['ingredient'].name} risk {r['risk']} qty {r['reorder']} days {r['days']}")
                else:
                    AIProcurementAlert.objects.create(
                        ingredient=r["ingredient"],
                        suggested_quantity=r["reorder"],
                        predicted_stockout_date=r["stockout_date"],
                        daily_usage=r["daily"],
                        days_until_stockout=r["days"],
                        risk=r["risk"],
                        reason=f"Auto: stockout in {r['days']} days ({r['daily']}/day)",
                    )
                    created += 1
        if not dry:
            AuditLog.objects.create(
                action="CRON_FORECAST",
                module="Forecasting",
                details=f"compute_forecasts created {created} alerts (skipped {skipped} dup) at {timezone.now():%Y-%m-%d %H:%M}",
            )
        self.stdout.write(self.style.SUCCESS(f"Forecasts computed: {len(rows)} ingredients, {created} new alerts, {skipped} skipped duplicate pending."))
