from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random 

from apps.users.models import User, UserRole
from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event

class Command(BaseCommand):
    help = "Seed the database with initial data."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force seeding even if data exists')

    def handle(self, *args, **options):
        force = options['force']

        if Device.objects.exists() and not force:
            self.stdout.write(self.style.WARNING('Data already exists (devices found). Skipping seed. Use --force to override.'))
            return  

        self.stdout.write(self.style.SUCCESS("Seeding the database..."))

        # Create a test user with CLIENT role
        user_client, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'password': 'testpassword',  
                'role': UserRole.CLIENT.value,
            }
        )
        if created:
            user_client.set_password('testpassword') 
            user_client.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {user_client.username}'))
        else:
            self.stdout.write(self.style.NOTICE(f'User {user_client.username} already exists, using it.'))

        # Create a test user with ADMIN role
        user_admin, created = User.objects.get_or_create(
            username='adminuser',
            defaults={
                'email': 'admin@example.com',
                'password': 'adminpassword',
                'role': UserRole.ADMIN.value,
            }
        )
        if created:
            user_admin.set_password('adminpassword')
            user_admin.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {user_admin.username}'))
        else:
            self.stdout.write(self.style.NOTICE(f'Admin user {user_admin.username} already exists, using it.'))

        # Create metrics
        temperature_metric, _ = Metric.objects.get_or_create(
            metric_type='temperature',
            defaults={'data_type': 'numeric'}
        )
        humidity_metric, _ = Metric.objects.get_or_create(
            metric_type='humidity',
            defaults={'data_type': 'numeric'}
        )
        self.stdout.write(self.style.SUCCESS('Created metrics: temperature and humidity'))

        # Create devices 
        device1 = Device.objects.create(
            serial_id=f'SN-10002000',
            name='Test Device 1',
            description='Sample IoT sensor for temperature',
            user=user_client,
            is_active=True
        )
        device2 = Device.objects.create(
            serial_id=f'SN-10002001',
            name='Test Device 2',
            description='Sample IoT sensor for humidity',
            user=user_client,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS(f'Created devices: {device1.name} and {device2.name}'))

        # Create device-metric associations
        dm_temp1 = DeviceMetric.objects.create(device=device1, metric=temperature_metric)
        dm_hum1 = DeviceMetric.objects.create(device=device2, metric=humidity_metric)
        self.stdout.write(self.style.SUCCESS('Created device_metrics links'))

        # Create telemetry data
        now = timezone.now()
        for i in range(5):
            Telemetry.objects.create(
                device_metric=dm_temp1,
                value_jsonb={'t': 'numeric', 'v': str(random.uniform(20, 80))},  
                ts=now - timedelta(minutes=i * 10)
            )   
            Telemetry.objects.create(
                device_metric=dm_hum1,
                value_jsonb={'t': 'numeric', 'v': str(random.uniform(40, 60))},
                ts=now - timedelta(minutes=i * 10)
            )
        self.stdout.write(self.style.SUCCESS('Created 10 telemetry rows (5 for each device)'))
        
        # Create sample rules
        rule_high_temp, _ = Rule.objects.get_or_create(
            name='High Temperature Alert',
            defaults={
                'description': 'Trigger when temperature > 28°C for more than 10 minutes',
                'condition': {
                    "type": "threshold",
                    "metric": "temperature",
                    "operator": ">",
                    "value": 28,
                    "duration_minutes": 10
                },
                'action': {
                    "type": "notify",
                    "channel": "email",
                    "message": "Temperature too high in {device_name}: {value}°C"
                },
                'is_active': True,
                'device_metric': dm_temp1
            }
        )

        rule_low_humidity, _ = Rule.objects.get_or_create(
            name='Low Humidity Warning',
            defaults={
                'description': 'Alert when humidity drops below 30%',
                'condition': {
                    "type": "threshold",
                    "metric": "humidity",
                    "operator": "<",
                    "value": 30,
                    "duration_minutes": 5
                },
                'action': {
                    "type": "log",
                    "level": "warning",
                    "message": "Low humidity detected: {value}%"
                },
                'is_active': True,
                'device_metric': dm_hum1
            }
        )
        self.stdout.write(self.style.SUCCESS('Created 2 sample rules'))

        #Create event logs for actions taken by rules
        base_time = now - timedelta(hours=2)

        # Events for rule high_temp
        for i in range(3):
            Event.objects.create(
                timestamp=base_time + timedelta(minutes=15 * i),
                rule=rule_high_temp,
                created_at=timezone.now()
            )

        # Events for rule low_humidity
        for i in range(2):
            Event.objects.create(
                timestamp=base_time + timedelta(minutes=30 + 20 * i),
                rule=rule_low_humidity,
                created_at=timezone.now()
            )

        self.stdout.write(self.style.SUCCESS('Created 5 sample events (rule triggers)'))


        self.stdout.write(self.style.SUCCESS("Database seeded successfully."))