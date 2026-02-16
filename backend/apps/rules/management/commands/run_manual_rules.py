from django.core.management.base import BaseCommand
from django.core.management import CommandError

from apps.devices.models.telemetry import Telemetry
from apps.rules.services.rule_processor import RuleProcessor


class Command(BaseCommand):
    help = 'Runs manual rule evaluation for specific or latest telemetry'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='Specific Telemetry ID to process')
        parser.add_argument(
            '--latest', action='store_true', help='Process the 10 latest telemetry records'
        )
        parser.add_argument(
            '--order',
            choices=['ts', 'created_at'],
            default='ts',
            help='Ordering field for --latest (default: ts)',
        )
        parser.add_argument('--device', type=int, help='Filter by device id')
        parser.add_argument('--device_metric', type=int, help='Filter by device_metric id')

    def handle(self, *args, **options):
        telemetry_id = options.get('id')
        order_field = options.get('order')
        device_id = options.get('device')
        device_metric_id = options.get('device_metric')

        if telemetry_id:
            try:
                t = Telemetry.objects.get(id=telemetry_id)
                self.stdout.write(self.style.SUCCESS(f"Processing telemetry {t.id}..."))
                RuleProcessor.run(t)
            except Telemetry.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Telemetry with ID {telemetry_id} not found"))
                return

        elif options['latest']:
            qs = Telemetry.objects.all()
            if device_id:
                qs = qs.filter(device_metric__device_id=device_id)
            if device_metric_id:
                qs = qs.filter(device_metric_id=device_metric_id)

            if not qs.exists():
                raise CommandError(
                    f"No telemetry found for device_id={device_id} "
                    f"or device_metric_id={device_metric_id}"
                )

            latest_items = qs.order_by(f'-{order_field}')[:10]

            errors = []
            for t in latest_items:
                try:
                    self.stdout.write(
                        f"Processing telemetry {t.id} (device: {t.device_metric.device.id}, "
                        f"metric: {t.device_metric.id})..."
                    )
                    RuleProcessor.run(t)
                except Exception as e:
                    errors.append((t.id, str(e)))
                    self.stderr.write(self.style.ERROR(f"Error processing telemetry {t.id}: {e}"))

            if errors:
                self.stdout.write(self.style.WARNING(f"Finished with {len(errors)} errors."))
