from django.core.management.base import BaseCommand
from apps.devices.models.telemetry import Telemetry
from apps.rules.services.rule_processor import RuleProcessor

class Command(BaseCommand):
    help = 'Runs manual rule evaluation for specific or latest telemetry'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='Specific Telemetry ID to process')
        parser.add_argument('--latest', action='store_true', help='Process the 10 latest telemetry records')

    def handle(self, *args, **options):
        telemetry_id = options['id']
        
        if telemetry_id:
            try:
                t = Telemetry.objects.get(id=telemetry_id)
                self.stdout.write(self.style.SUCCESS(f"Processing telemetry {t.id}..."))
                RuleProcessor.run(t)
            except Telemetry.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Telemetry with ID {telemetry_id} not found"))
                return

        elif options['latest']:
            latest_items = Telemetry.objects.order_by('-ts')[:10] # or by created_by ??????
            for t in latest_items:
                self.stdout.write(f"Processing telemetry {t.id} (device: {t.device_metric})...")
                RuleProcessor.run(t)
        
        else:
            self.stdout.write(self.style.WARNING("Please provide --id <int> or --latest flag"))

        self.stdout.write(self.style.SUCCESS("Finished manual rule evaluation pass."))