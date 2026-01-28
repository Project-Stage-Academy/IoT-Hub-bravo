import os

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Command(BaseCommand):
    help = "Setup admin users, groups and permissions for development/testing only."

    def handle(self, *args, **options):
        # Gate: dev/test only (allow override via env)
        allow = _env_bool("ALLOW_SETUP_ADMIN", default=False)
        if not (settings.DEBUG or allow):
            raise CommandError(
                "setup_admin is disabled outside development/testing. "
                "Set ALLOW_SETUP_ADMIN=true to override."
            )

        self.stdout.write("Setting up admin users, groups and permissions...")

        user_model = apps.get_model("users", "User")

        try:
            with transaction.atomic():
                self._create_or_update_groups()
                self._create_superuser(user_model)
                self._create_role_users(user_model)

        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f"Admin setup failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Admin setup completed successfully."))
        self.stdout.write("Available users (passwords come from environment variables):")
        self.stdout.write("  - DEV_SUPERUSER_USERNAME (Superuser)")
        self.stdout.write("  - DEV_VIEWER_USERNAME (Viewer)")
        self.stdout.write("  - DEV_OPERATOR_USERNAME (Operator)")
        self.stdout.write("  - DEV_ADMIN_USERNAME (Admin)")

    def _create_superuser(self, user_model):
        username = os.getenv("DEV_SUPERUSER_USERNAME", "admin_from_script")
        email = os.getenv("DEV_SUPERUSER_EMAIL", "admin_from_script@example.com")
        password = os.getenv("DEV_SUPERUSER_PASSWORD")

        if not password:
            raise CommandError(
                "DEV_SUPERUSER_PASSWORD is required. "
                "Refusing to create a superuser with a hardcoded/default password."
            )

        existing_user = user_model.objects.filter(
            models.Q(username=username) | models.Q(email=email)
        ).first()

        if existing_user:
            self.stdout.write(f"Superuser '{username}' already exists.")
            if not existing_user.is_superuser:
                existing_user.is_superuser = True
                existing_user.is_staff = True
                existing_user.save(update_fields=["is_superuser", "is_staff"])
                self.stdout.write(f"Updated '{username}' to superuser.")
            return

        user_model.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser: {username}"))

    def _create_role_users(self, user_model):
        users_data = [
            {
                "username_env": "DEV_VIEWER_USERNAME",
                "email_env": "DEV_VIEWER_EMAIL",
                "password_env": "DEV_VIEWER_PASSWORD",
                "default_username": "viewer_user",
                "default_email": "viewer@example.com",
                "group": "Viewer",
            },
            {
                "username_env": "DEV_OPERATOR_USERNAME",
                "email_env": "DEV_OPERATOR_EMAIL",
                "password_env": "DEV_OPERATOR_PASSWORD",
                "default_username": "operator_user",
                "default_email": "operator@example.com",
                "group": "Operator",
            },
            {
                "username_env": "DEV_ADMIN_USERNAME",
                "email_env": "DEV_ADMIN_EMAIL",
                "password_env": "DEV_ADMIN_PASSWORD",
                "default_username": "admin_user",
                "default_email": "admin_user@example.com",
                "group": "Admin",
            },
        ]

        for item in users_data:
            username = os.getenv(item["username_env"], item["default_username"])
            email = os.getenv(item["email_env"], item["default_email"])
            password = os.getenv(item["password_env"])

            if not password:
                self.stdout.write(f"Skipping user '{username}': missing {item['password_env']}.")
                continue

            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={"email": email},
            )

            if created:
                user.set_password(password)
                user.is_staff = True
                user.save(update_fields=["password", "is_staff", "email"])
                self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))
            else:
                changed = False
                if not user.is_staff:
                    user.is_staff = True
                    changed = True
                if email and user.email != email:
                    user.email = email
                    changed = True
                if changed:
                    user.save(update_fields=["is_staff", "email"])
                self.stdout.write(f"User '{username}' already exists.")

            group = Group.objects.get(name=item["group"])
            user.groups.add(group)

    def _create_or_update_groups(self):
        """
        Creates groups and ensures permissions are up to date.
        This runs inside a transaction.atomic() in handle().
        """
        device_model = apps.get_model("devices", "Device")
        telemetry_model = apps.get_model("devices", "Telemetry")
        metric_model = apps.get_model("devices", "Metric")
        device_metric_model = apps.get_model("devices", "DeviceMetric")
        rule_model = apps.get_model("rules", "Rule")
        event_model = apps.get_model("rules", "Event")

        models = [
            device_model,
            telemetry_model,
            metric_model,
            device_metric_model,
            rule_model,
            event_model,
        ]

        self._ensure_group_permissions(name="Viewer", models=models, actions=["view"])
        self._ensure_group_permissions(
            name="Operator", models=models, actions=["view", "add", "change"]
        )
        self._ensure_group_permissions(
            name="Admin", models=models, actions=["view", "add", "change", "delete"]
        )

    def _ensure_group_permissions(self, name, models, actions):
        group, _ = Group.objects.get_or_create(name=name)

        perms = []
        missing = []

        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            for action in actions:
                codename = f"{action}_{model._meta.model_name}"

                # SAFE: don't crash if permissions are not created yet.
                perm = Permission.objects.filter(
                    codename=codename, content_type=content_type
                ).first()
                if perm is None:
                    missing.append(f"{codename} ({content_type.app_label}.{content_type.model})")
                    continue
                perms.append(perm)

        group.permissions.set(perms)

        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"Ensured group: {name} permissions with missing entries (run migrations?): "
                    + ", ".join(missing)
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Ensured group: {name} permissions."))
