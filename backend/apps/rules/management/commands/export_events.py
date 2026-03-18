from django.core.management.base import BaseCommand
import csv
import os
from django.utils.dateparse import parse_datetime
from apps.rules.models import Event


class Command(BaseCommand):
    help = 'Export recent events to CSV (stdout or file in repo)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--since',
            type=str,
            help='Only include events created since this timestamp (ISO format)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Optional output CSV file path (default: exports/events_export.csv in repo)',
        )

    def handle(self, *args, **options):
        try:
            since = options.get('since')
            output_file = options.get('output')

            if not output_file:
                exports_dir = os.path.join(os.getcwd(), 'exports')
                os.makedirs(exports_dir, exist_ok=True)
                output_file = os.path.join(exports_dir, 'events_export.csv')

            qs = Event.objects.all().order_by('-rule_triggered_at')

            if since:
                dt = parse_datetime(since)
                if dt:
                    qs = qs.filter(rule_triggered_at__gte=dt)
                else:
                    self.stdout.write(self.style.ERROR(f"Invalid --since datetime: {since}"))
                    return

            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                writer.writerow(
                    [
                        'event_uuid',
                        'rule_triggered_at',
                        'rule',
                        'acknowledged',
                        'trigger_device_serial_id',
                        'trigger_context',
                    ]
                )

                for event in qs:
                    writer.writerow(
                        [
                            event.event_uuid,
                            event.rule_triggered_at,
                            event.rule.name,
                            event.acknowledged,
                            event.trigger_device_serial_id,
                            event.trigger_context,
                        ]
                    )

            self.stdout.write(self.style.SUCCESS(f"Exported {qs.count()} events to {output_file}"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error exporting events: {e}"))
