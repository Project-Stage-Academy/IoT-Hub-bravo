import json
import tempfile
import os
from pathlib import Path

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.users.models import UserRole
from django.apps import apps
import sys

User = get_user_model()


class Command(BaseCommand):
    """
    Seed development data using Django fixtures.

    - Creates default users
    - Dynamically assigns devices to client users
    - Loads fixtures in a strict dependency order
    - Uses temporary fixtures to keep Git clean
    """

    help = "Seeds dev data using temporary fixtures."

    USERS_DATA = [
        {
            "username": "dev_admin",
            "email": "dev.admin@example.com",
            "password": os.getenv("DEV_ADMIN_PASSWORD" ,"DevSecurePass"),
            "is_staff": True,
            "is_superuser": True,
            "role": UserRole.ADMIN.value,
        },
        {
            "username": "alex_client",
            "email": "alex.smith@example.com",
            "password": os.getenv("DEV_CLIENT_ALEX_PASSWORD", "ClientAccess1"),
            "is_staff": False,
            "is_superuser": False,
            "role": UserRole.CLIENT.value,
        },
        {
            "username": "jordan_client",
            "email": "j.doe@example.com",
            "password": os.getenv("DEV_CLIENT_JORDAN_PASSWORD", "ClientAccess2!"),
            "is_staff": False,
            "is_superuser": False,
            "role": UserRole.CLIENT.value,
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing seeded data and recreate it from fixtures",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the seed process without writing anything to the database",
        )

    def handle(self, *args, **options):
        self.force = options["force"]
        self.dry_run = options["dry_run"]

        

        self.stdout.write(self.style.MIGRATE_HEADING("--- Dev Seeding Started ---"))

        if self.dry_run:
            self.stdout.write(self.style.WARNING("Dry-run mode enabled"))

        try:
            with transaction.atomic():    
                if not self._ensure_safe_to_seed():
                    return
                
                users = self._create_users()
                self._load_fixtures(users)

                if self.dry_run:
                    transaction.set_rollback(True)
                    self.stdout.write(self.style.WARNING("\n[DRY-RUN] All database changes have been rolled back."))
        except CommandError:
            raise
        except Exception as e:
            raise CommandError(f"Seeding failed: {e}")

        if not self.dry_run:
            self.stdout.write(self.style.SUCCESS("--- Seed Completed Successfully ---"))

    def _create_users(self):
        """Create or update predefined users."""
        created = []

        for data in self.USERS_DATA:
            user = self._upsert_user(**data)
            if user:
                created.append(user)

        return created

    def _upsert_user(self, username, email, password, is_staff, is_superuser, role):
        """Create or update a single user."""

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "is_active": True,
                "role": role,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            status = "Created"
        else:
            status = "Already exists"

        self.stdout.write(f"{status} user: {username}")
        return user

    def _load_fixtures(self, users):
        """
        Load fixtures in the correct dependency order.
        Only devices fixture is dynamically generated.
        """
        clients = [u for u in users if not u.is_superuser]

        if len(clients) < 2:
            raise CommandError("At least two client users are required")

        # Metrics
        self._loaddata("01_metrics.json")

        # Devices (dynamic users)
        devices_tmp = None
        try:
            devices_tmp = self._prepare_devices_fixture(clients)
            self._loaddata(devices_tmp)

            # Device_metrics & telemetries
            self._loaddata("03_device_metrics.json")
            self._loaddata("04_telemetries.json")

            # Rules & events
            self._loaddata("01_rules.json")
            self._loaddata("02_events.json")

        finally:
            if devices_tmp:
                Path(devices_tmp).unlink(missing_ok=True)

    def _prepare_devices_fixture(self, clients) -> str:
        """
        Prepare a temporary devices fixture with assigned user IDs.
        """
        devices_app = apps.get_app_config("devices")
        source = Path(devices_app.path) / "fixtures" / "02_devices.json"

        if not source.exists():
            raise CommandError("02_devices.json not found in devices fixtures")

        try:
            with open(source, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise CommandError("Invalid JSON in 02_devices.json") from exc

        half = len(data) // 2
        for i, obj in enumerate(data):
            obj["fields"]["user"] = clients[0].id if i < half else clients[1].id

        tmp = tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False)
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.flush()

        return tmp.name

    def _loaddata(self, fixture):
        """Load a single fixture via Django loaddata."""
        self.stdout.write(f"Loading fixture: {Path(fixture).name}")
        try:
            call_command("loaddata", fixture, verbosity=1)
        except Exception as exc:
            raise CommandError(f"Failed loading fixture {fixture}: {exc}") from exc

    def _ensure_safe_to_seed(self):
        """
        Prevent accidental seeding into non-empty database.
        """

        has_users = User.objects.exists()
        if has_users and not self.force:
            self.stdout.write(
                self.style.WARNING("Database is not empty. Use --force to overwrite existing data.")
            )
            if self.dry_run:
                self.stdout.write(self.style.NOTICE("[DRY-RUN] Simulation ended: real execution would stop here."))
            return False
        
        if has_users and self.force:
            prefix = "[DRY-RUN] Would clean" if self.dry_run else "Cleaning"
            self.stdout.write(self.style.WARNING(f"{prefix} existing data due to --force..."))

            self._cleanup_db()
            return True
        return True

    def _cleanup_db(self):
        """
        Remove existing seeded data before re-seeding.
        Executed only with --force and NOT in dry-run.
        """
        self.stdout.write(self.style.WARNING("Cleaning existing data..."))

        models_to_clear = [
            "rules.Event",
            "rules.Rule",
            "devices.Telemetry",
            "devices.DeviceMetric",
            "devices.Device",
            "devices.Metric",
            "users.User",
        ]

        for model_path in models_to_clear:
            app_label, model_name = model_path.split(".")
            model = apps.get_model(app_label, model_name)
            deleted, _ = model.objects.all().delete()
            self.stdout.write(f"  - {model_name}: {deleted} rows deleted")
