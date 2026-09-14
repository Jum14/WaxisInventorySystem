import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile
from audit.models import AuditLog
from forecasting.models import AIProcurementAlert
from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest
from reports.models import AIVarianceLog
from suppliers.models import Supplier


DEMO_TAG = "DEMO_SEED"
DEMO_INGREDIENTS = [
    ("Chicken Wings", "FROZEN", Decimal("180"), "kg", 20, 50),
    ("Chicken Thigh", "FROZEN", Decimal("160"), "kg", 20, 50),
    ("Fresh Vegetables", "CHILLED", Decimal("85"), "kg", 10, 30),
    ("Dairy Milk", "CHILLED", Decimal("75"), "L", 15, 40),
    ("Rice", "DRY", Decimal("45"), "kg", 30, 100),
    ("Cooking Oil", "DRY", Decimal("95"), "L", 15, 40),
    ("Flour", "DRY", Decimal("60"), "kg", 20, 60),
    ("Spices", "DRY", Decimal("250"), "kg", 5, 15),
    ("Bottled Water", "CHILLED", Decimal("12"), "pcs", 30, 100),
    ("Packaging Box", "DRY", Decimal("8"), "pcs", 50, 200),
    ("Sauce", "DRY", Decimal("110"), "kg", 10, 30),
    ("Ice", "FROZEN", Decimal("20"), "kg", 20, 80),
]

DEMO_SUPPLIERS = [
    ("Waxi Meat Co", "MEAT", 2, "john@waximeat.ph", "Juan Dela Cruz"),
    ("Fresh Produce PH", "PRODUCE", 1, "fresh@produce.ph", "Maria Santos"),
    ("Dairy Direct", "DAIRY", 2, "dairy@direct.ph", "Ana Reyes"),
    ("Dry Goods Central", "DRY", 3, "dry@goods.ph", "Pedro Lim"),
    ("Cold Chain Frozen", "FROZEN", 2, "cold@chain.ph", "Chen Wu"),
]


class Command(BaseCommand):
    help = "Hybrid seed demo: 5 suppliers, 12 ingredients, 40 transactions (30d), 8 procurement, 3 AI alerts + variance. Idempotent. Use --clear to remove demo data."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Remove demo seed data (notes=DEMO_SEED)")
        parser.add_argument("--count-only", action="store_true", help="Just show demo counts")

    def handle(self, *args, **options):
        if options["count_only"]:
            self.count_demo()
            return
        if options["clear"]:
            self.clear_demo()
            return
        self.seed_demo()

    def count_demo(self):
        demo_by_name = Ingredient.objects.filter(name__in=[n for n, *_ in DEMO_INGREDIENTS]).count()
        demo_tx = StockTransaction.objects.filter(notes=DEMO_TAG).count()
        demo_pr = ProcurementRequest.objects.filter(notes=DEMO_TAG).count()
        demo_alerts = AIProcurementAlert.objects.filter(reason__contains=DEMO_TAG).count()
        demo_var = AIVarianceLog.objects.filter(alert__reason__contains=DEMO_TAG).count()
        self.stdout.write(f"Demo Ingredients (by name): {demo_by_name}")
        self.stdout.write(f"Demo Transactions (notes=DEMO_SEED): {demo_tx}")
        self.stdout.write(f"Demo Procurement (notes=DEMO_SEED): {demo_pr}")
        self.stdout.write(f"Demo Alerts: {demo_alerts} VarianceLogs: {demo_var}")

    def clear_demo(self):
        # Ingredients: delete by demo names only if they were created by seed (check unit_cost matches demo to avoid deleting real)
        demo_names = [n for n, *_ in DEMO_INGREDIENTS]
        # Only delete transactions/procurement tagged, not ingredients permanently? Keep ingredients but clear demo tx
        tx_deleted, _ = StockTransaction.objects.filter(notes=DEMO_TAG).delete()
        pr_deleted, _ = ProcurementRequest.objects.filter(notes=DEMO_TAG).delete()
        var_deleted, _ = AIVarianceLog.objects.filter(ingredient__name__in=demo_names).delete()
        alert_deleted, _ = AIProcurementAlert.objects.filter(reason__contains=DEMO_TAG).delete()
        # Optionally delete suppliers that are demo-only and have no non-demo relations
        sup_demo_names = [n for n, *_ in DEMO_SUPPLIERS]
        for sname in sup_demo_names:
            try:
                sup = Supplier.objects.get(company_name=sname)
                # Only delete if no non-demo ingredients/transactions left
                if not Ingredient.objects.filter(supplier_fk=sup).exclude(name__in=demo_names).exists() and not ProcurementRequest.objects.filter(supplier=sup).exclude(notes=DEMO_TAG).exists():
                    # Keep supplier for demo? Actually clear means remove demo suppliers
                    sup.delete()
                    self.stdout.write(f"Deleted supplier {sname}")
                else:
                    self.stdout.write(f"Kept supplier {sname} (has live relations)")
            except Supplier.DoesNotExist:
                pass
        # Delete demo ingredients only if they have no non-demo transactions left
        for n in demo_names:
            try:
                ing = Ingredient.objects.get(name=n)
                if not StockTransaction.objects.filter(ingredient=ing).exclude(notes=DEMO_TAG).exists() and not ProcurementRequest.objects.filter(ingredient=ing).exclude(notes=DEMO_TAG).exists():
                    ing.delete()
                    self.stdout.write(f"Deleted demo ingredient {n}")
            except Ingredient.DoesNotExist:
                pass
        self.stdout.write(self.style.WARNING(f"Cleared demo: {tx_deleted} tx, {pr_deleted} pr, {alert_deleted} alerts, {var_deleted} variance logs"))

    def seed_demo(self):
        now = timezone.now()
        # Ensure developer user for FK
        try:
            dev = User.objects.get(username="developer")
        except User.DoesNotExist:
            dev = User.objects.filter(is_superuser=True).first()
            if not dev:
                dev = User.objects.create_user("developer", "dev@waxis.local", "admin123")
                Profile.objects.update_or_create(user=dev, defaults={"role": Profile.Role.DEVELOPER})

        # 1. Suppliers idempotent
        sup_map = {}
        for name, cat, lead, email, contact in DEMO_SUPPLIERS:
            sup, created = Supplier.objects.get_or_create(
                company_name=name,
                defaults={"category": cat, "lead_time_days": lead, "email": email, "contact_person": contact, "is_active": True, "notes": DEMO_TAG}
            )
            if not created:
                # Update to demo values but keep if already live
                sup.category = cat
                sup.lead_time_days = lead
                sup.email = email
                sup.contact_person = contact
                sup.is_active = True
                sup.save(update_fields=["category", "lead_time_days", "email", "contact_person", "is_active", "updated_at"])
            sup_map[name] = sup
            self.stdout.write(f"{'Created' if created else 'Updated'} supplier {name}")

        # 2. Ingredients
        ing_map = {}
        # Map supplier assignment
        sup_assign = {
            "Chicken Wings": "Waxi Meat Co",
            "Chicken Thigh": "Waxi Meat Co",
            "Fresh Vegetables": "Fresh Produce PH",
            "Dairy Milk": "Dairy Direct",
            "Rice": "Dry Goods Central",
            "Cooking Oil": "Dry Goods Central",
            "Flour": "Dry Goods Central",
            "Spices": "Dry Goods Central",
            "Bottled Water": "Fresh Produce PH",
            "Packaging Box": "Dry Goods Central",
            "Sauce": "Dry Goods Central",
            "Ice": "Cold Chain Frozen",
        }
        for name, cat, cost, unit, min_s, max_s in DEMO_INGREDIENTS:
            sup = sup_map.get(sup_assign.get(name))
            # Demo quantities: mid-range
            qty = Decimal(str(random.randint(int(min_s), int(max_s))))
            # For some, make low/critical for demo: Fresh Vegetables low, Chicken Wings mid
            if name == "Fresh Vegetables":
                qty = Decimal("4")  # low vs min 10
            if name == "Spices":
                qty = Decimal("2")  # critical vs min 5
            ing, created = Ingredient.objects.get_or_create(
                name=name,
                defaults={
                    "category": cat,
                    "quantity": qty,
                    "unit": unit,
                    "minimum_stock": Decimal(str(min_s)),
                    "maximum_stock": Decimal(str(max_s)),
                    "unit_cost": cost,
                    "supplier_fk": sup,
                    "supplier": sup.company_name if sup else "",
                }
            )
            if not created:
                # Update demo-relevant fields idempotently; preserve quantity if already low? But ensure unit_cost set
                ing.category = cat
                ing.unit = unit
                ing.minimum_stock = Decimal(str(min_s))
                ing.maximum_stock = Decimal(str(max_s))
                ing.unit_cost = cost
                ing.supplier_fk = sup
                # Only reset quantity if it was 0 (to keep demo low items low)
                if ing.quantity == 0:
                    ing.quantity = qty
                ing.save(update_fields=["category", "unit", "minimum_stock", "maximum_stock", "unit_cost", "supplier_fk", "quantity", "updated_at"])
            else:
                # Tag via supplier? Ingredient has no notes, but we can use supplier field already set
                pass
            ing_map[name] = ing
            self.stdout.write(f"{'Created' if created else 'Updated'} ingredient {name} qty {ing.quantity} cost {cost}")

        # 3. Clear old demo transactions/procurement to avoid dup on re-run (by notes tag)
        StockTransaction.objects.filter(notes=DEMO_TAG).delete()
        ProcurementRequest.objects.filter(notes=DEMO_TAG).delete()
        AIProcurementAlert.objects.filter(reason__contains=DEMO_TAG).delete()

        # 3a. StockTransactions 40 spread last 30d
        tx_specs = []
        # 25 NORMAL_USAGE deducted
        fast_names = ["Chicken Wings", "Rice", "Cooking Oil", "Flour", "Sauce"]
        for i in range(25):
            name = random.choice(fast_names)
            ing = ing_map[name]
            qty = Decimal(str(random.randint(3, 6)))
            tx_specs.append((name, qty, "NORMAL_USAGE", "DEDUCTED"))
        # 10 SPOILAGE_WASTE
        waste_names = ["Fresh Vegetables", "Dairy Milk", "Ice"]
        for i in range(10):
            name = random.choice(waste_names)
            ing = ing_map[name]
            qty = Decimal(str(random.randint(1, 3)))
            tx_specs.append((name, qty, "SPOILAGE_WASTE", "SPOILAGE"))
        # 5 DAMAGED
        for i in range(5):
            name = "Packaging Box"
            ing = ing_map[name]
            qty = Decimal(str(random.randint(5, 10)))
            tx_specs.append((name, qty, "DAMAGED", "SPOILAGE"))
        # Shuffle and spread dates
        random.shuffle(tx_specs)
        for idx, (name, qty, reason, tx_type) in enumerate(tx_specs):
            ing = ing_map[name]
            # Spread over last 30 days, ensure some in current month for fast_movers (last 15)
            days_ago = random.randint(0, 30)
            # Bias 60% to last 10 days for fast-movers visibility
            if random.random() < 0.6:
                days_ago = random.randint(0, 10)
            ts = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            # Ensure remaining_stock logic plausible: previous - qty, but not negative
            prev = ing.quantity + qty  # dummy prev higher
            # Create with explicit created_at via update after create (auto_now_add overrides, so create then update)
            tx = StockTransaction.objects.create(
                ingredient=ing,
                user=dev,
                transaction_type=tx_type,
                quantity=qty,
                previous_stock=prev,
                remaining_stock=prev - qty,
                reason=reason,
                notes=DEMO_TAG,
            )
            # Hack created_at to spread
            StockTransaction.objects.filter(pk=tx.pk).update(created_at=ts)

        self.stdout.write(self.style.SUCCESS(f"Created {len(tx_specs)} demo StockTransactions ({DEMO_TAG}) spread 30d"))

        # 4. ProcurementRequests 8 for monthly_expenditure + supplier reliability
        # 5 delivered with expected/actual dates
        delivered_specs = [
            ("Chicken Wings", "Waxi Meat Co", Decimal("20"), Decimal("175"), -4, -1),  # expected 4d ago, actual 1d ago => 3d delay
            ("Rice", "Dry Goods Central", Decimal("30"), Decimal("45"), -6, -1),  # 5d delay
            ("Fresh Vegetables", "Fresh Produce PH", Decimal("10"), Decimal("85"), -3, -2),  # 1d delay
            ("Dairy Milk", "Dairy Direct", Decimal("15"), Decimal("75"), -5, -3),  # 2d delay
            ("Cooking Oil", "Dry Goods Central", Decimal("12"), Decimal("95"), -2, -2),  # 0d reliable
        ]
        for name, sup_name, qty, price, exp_delta, act_delta in delivered_specs:
            ing = ing_map[name]
            sup = sup_map[sup_name]
            exp = (now + timedelta(days=exp_delta)).date()
            act = (now + timedelta(days=act_delta)).date()
            pr = ProcurementRequest.objects.create(
                ingredient=ing,
                supplier=sup,
                requested_quantity=qty,
                delivered_quantity=qty,
                expected_delivery_date=exp,
                expected_date=exp,  # legacy alias
                actual_delivery_date=act,
                unit_price=price,
                priority=ProcurementRequest.Priority.HIGH if "Chicken" in name else ProcurementRequest.Priority.NORMAL,
                status=ProcurementRequest.Status.DELIVERED,
                reason=f"Demo restock {name}",
                requested_by=dev,
                approved_by=dev,
                notes=DEMO_TAG,
            )
            # Set created_at to this month
            ProcurementRequest.objects.filter(pk=pr.pk).update(created_at=now - timedelta(days=random.randint(1, 5)))

        # 2 ordered
        ordered_specs = [
            ("Flour", "Dry Goods Central", Decimal("25"), Decimal("60"), 2),
            ("Ice", "Cold Chain Frozen", Decimal("30"), Decimal("20"), 3),
        ]
        for name, sup_name, qty, price, exp_in in ordered_specs:
            ing = ing_map[name]
            sup = sup_map[sup_name]
            exp = (now + timedelta(days=exp_in)).date()
            pr = ProcurementRequest.objects.create(
                ingredient=ing,
                supplier=sup,
                requested_quantity=qty,
                expected_delivery_date=exp,
                expected_date=exp,
                unit_price=price,
                priority=ProcurementRequest.Priority.NORMAL,
                status=ProcurementRequest.Status.ORDERED,
                reason=f"Demo ordered {name}",
                requested_by=dev,
                notes=DEMO_TAG,
            )
            ProcurementRequest.objects.filter(pk=pr.pk).update(created_at=now - timedelta(days=2))

        # 1 pending AI auto_generated
        pr = ProcurementRequest.objects.create(
            ingredient=ing_map["Spices"],
            supplier=sup_map["Dry Goods Central"],
            requested_quantity=Decimal("8"),
            expected_delivery_date=(now + timedelta(days=5)).date(),
            unit_price=Decimal("250"),
            priority=ProcurementRequest.Priority.CRITICAL,
            status=ProcurementRequest.Status.PENDING,
            reason="AI auto: predicted stockout in 2 days",
            requested_by=dev,
            auto_generated=True,
            notes=DEMO_TAG,
        )
        ProcurementRequest.objects.filter(pk=pr.pk).update(created_at=now - timedelta(days=1))
        self.stdout.write(self.style.SUCCESS("Created 8 demo ProcurementRequests (5 delivered, 2 ordered, 1 pending)"))

        # 5. AIProcurementAlerts 3 with variance
        alert_specs = [
            ("Chicken Wings", now.date() - timedelta(days=2), now.date(), "HIGH", Decimal("20")),
            ("Fresh Vegetables", now.date() - timedelta(days=1), now.date() - timedelta(days=1), "MEDIUM", Decimal("15")),
            ("Spices", now.date() + timedelta(days=2), None, "HIGH", Decimal("10")),
        ]
        for name, pred, actual, risk, qty in alert_specs:
            ing = ing_map[name]
            alert = AIProcurementAlert.objects.create(
                ingredient=ing,
                suggested_quantity=qty,
                predicted_stockout_date=pred,
                actual_zero_date=actual,
                daily_usage=Decimal("2.5"),
                days_until_stockout=Decimal("2"),
                risk=risk,
                reason=f"{DEMO_TAG} AI predicted {pred} demo",
                status=AIProcurementAlert.Status.PENDING if not actual else AIProcurementAlert.Status.CONVERTED,
                created_by=dev,
            )
            if actual:
                # variance auto via save()
                pass
            # Create variance log for delivered variance
            if actual:
                AIVarianceLog.objects.create(
                    alert=alert,
                    ingredient=ing,
                    predicted_stockout_date=pred,
                    actual_zero_date=actual,
                    predicted_quantity=qty,
                )
        self.stdout.write(self.style.SUCCESS("Created 3 AI alerts + 2 variance logs"))

        # Audit
        AuditLog.objects.create(
            action="SEED_DEMO",
            module="Reports",
            details=f"Seed demo created by {dev.username} at {now:%Y-%m-%d %H:%M} - 12 ing, 40 tx, 8 pr, 3 alerts",
        )
        self.stdout.write(self.style.SUCCESS("Seed demo complete. Run with --clear to remove. Counts:"))
        self.count_demo()
