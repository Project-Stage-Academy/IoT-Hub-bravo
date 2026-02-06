from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.devices.models.telemetry import Telemetry
from apps.rules.services.rule_processor import RuleProcessor


class Command(BaseCommand):
    help = "Run RuleProcessor for recent telemetry"

    def handle(self, *args, **options):
        self.stdout.write("Starting RuleProcessor...")

        # telemetry last min
        since = timezone.now() - timezone.timedelta(minutes=1)

        telemetry_qs = Telemetry.objects.filter(
            created_at__gte=since
        ).order_by("created_at")

        count = 0
        processor = RuleProcessor()

        for telemetry in telemetry_qs:
            processor.run(telemetry)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Processed {count} telemetry events")
        )
