from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class Command(BaseCommand):
    help = "Setup admin users, groups and permissions for development"

    def handle(self, *args, **options):
        self.stdout.write("Setting up admin users and permissions...")

        # Create superuser if not exists
        if not User.objects.filter(username="admin_from_script").exists():
            User.objects.create_superuser(
                username="admin_from_script",
                email="admin_from_script@example.com",
                password="admin123",
            )
            self.stdout.write(
                self.style.SUCCESS("Created superuser: admin_from_script / admin123")
            )  # ← І тут
        else:
            self.stdout.write("Superuser 'admin_from_script' already exists")  # ← І тут

        # Create groups and permissions
        self.create_viewer_group()
        self.create_operator_group()
        self.create_admin_group()

        # Create test users
        self.create_test_users()

        self.stdout.write(self.style.SUCCESS("\nAdmin setup completed successfully!"))
        self.stdout.write("\nAvailable users:")
        self.stdout.write("  - admin_from_script / admin123 (Superuser)")
        self.stdout.write("  - viewer_user / viewer123 (Viewer - read only)")
        self.stdout.write("  - operator_user / operator123 (Operator - can add/edit)")
        self.stdout.write("  - admin_user / admin123 (Admin - full access)")

    def create_viewer_group(self):
        """Viewer: Read-only access to all models"""
        group, created = Group.objects.get_or_create(name="Viewer")

        if created:
            from apps.devices.models import Device, Telemetry, Metric, DeviceMetric
            from apps.rules.models import Rule, Event

            models = [Device, Telemetry, Metric, DeviceMetric, Rule, Event]

            for model in models:
                content_type = ContentType.objects.get_for_model(model)
                permission = Permission.objects.get(
                    codename=f"view_{model._meta.model_name}",
                    content_type=content_type,
                )
                group.permissions.add(permission)

            self.stdout.write(
                self.style.SUCCESS("Created group: Viewer (read-only access)")
            )
        else:
            self.stdout.write("Group 'Viewer' already exists")

    def create_operator_group(self):
        """Operator: Can view, add, change but not delete. Can run admin actions."""
        group, created = Group.objects.get_or_create(name="Operator")

        if created:
            from apps.devices.models import Device, Telemetry, Metric, DeviceMetric
            from apps.rules.models import Rule, Event

            models = [Device, Telemetry, Metric, DeviceMetric, Rule, Event]

            for model in models:
                content_type = ContentType.objects.get_for_model(model)

                # Add view, add, change permissions
                for action in ["view", "add", "change"]:
                    permission = Permission.objects.get(
                        codename=f"{action}_{model._meta.model_name}",
                        content_type=content_type,
                    )
                    group.permissions.add(permission)

            self.stdout.write(
                self.style.SUCCESS("Created group: Operator (view, add, change access)")
            )
        else:
            self.stdout.write("Group 'Operator' already exists")

    def create_admin_group(self):
        """Admin: Full access to all models"""
        group, created = Group.objects.get_or_create(name="Admin")

        if created:
            from apps.devices.models import Device, Telemetry, Metric, DeviceMetric
            from apps.rules.models import Rule, Event

            models = [Device, Telemetry, Metric, DeviceMetric, Rule, Event]

            for model in models:
                content_type = ContentType.objects.get_for_model(model)

                # Add all permissions
                for action in ["view", "add", "change", "delete"]:
                    permission = Permission.objects.get(
                        codename=f"{action}_{model._meta.model_name}",
                        content_type=content_type,
                    )
                    group.permissions.add(permission)

            self.stdout.write(self.style.SUCCESS("Created group: Admin (full access)"))
        else:
            self.stdout.write("Group 'Admin' already exists")

    def create_test_users(self):
        """Create test users for each role"""
        users_data = [
            {
                "username": "viewer_user",
                "email": "viewer@example.com",
                "password": "viewer123",
                "group": "Viewer",
            },
            {
                "username": "operator_user",
                "email": "operator@example.com",
                "password": "operator123",
                "group": "Operator",
            },
            {
                "username": "admin_user",
                "email": "admin_user@example.com",
                "password": "admin123",
                "group": "Admin",
            },
        ]

        for user_data in users_data:
            username = user_data["username"]
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=user_data["email"],
                    password=user_data["password"],
                )
                user.is_staff = True
                user.save()

                group = Group.objects.get(name=user_data["group"])
                user.groups.add(group)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created user: {username} / {user_data['password']} (group: {user_data['group']})"
                    )
                )
            else:
                self.stdout.write(f"User '{username}' already exists")
