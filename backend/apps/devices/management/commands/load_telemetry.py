import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.devices.models import Telemetry, DeviceMetric


class Command(BaseCommand):
    help = "Generates random telemetry data for testing purposes"

    def add_arguments(self, parser):
        parser.add_argument("total", type=int, help="The number of rows to insert")

    def handle(self, *args, **options):
        total = options["total"]
        batch_size = 5000

        metrics = list(DeviceMetric.objects.select_related("metric").all())

        if not metrics:
            self.stdout.write(
                self.style.ERROR("No metrics found! Please load metric fixtures first.")
            )
            return

        self.stdout.write(f"Starting generation of {total} records...")

        created_count = 0
        while created_count < total:
            batch = []
            current_batch_size = min(batch_size, total - created_count)

            for _ in range(current_batch_size):
                dm = random.choice(metrics)
                d_type = dm.metric.data_type

                if d_type == "numeric":
                    val = {"t": "numeric", "v": str(round(random.uniform(10, 40), 2))}
                elif d_type == "bool":
                    val = {"t": "bool", "v": random.choice([True, False])}
                else:
                    val = {"t": "str", "v": random.choice(["OK", "WARN", "ERR"])}

                ts = timezone.now() - timedelta(
                    days=random.randint(0, 30), minutes=random.randint(0, 1440)
                )

                batch.append(Telemetry(device_metric=dm, value_jsonb=val, ts=ts))

            Telemetry.objects.bulk_create(batch)

            created_count += current_batch_size
            self.stdout.write(f"Progress: {created_count}/{total} records inserted...")

        self.stdout.write(self.style.SUCCESS(f"Successfully added {total} records"))
