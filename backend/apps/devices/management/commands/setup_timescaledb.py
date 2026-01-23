from django.core.management.base import BaseCommand
from django.db import connection
from django.db import connection, transaction

class Command(BaseCommand):
    help = 'Setup TimescaleDB for telemetry table (hypertable, compression, retention)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force setup even if already configured')

    def handle(self, *args, **options):
        force = options.get('force', False)

        # Check if 'telemetries' is already a hypertable
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'telemetries'
            """)
            is_already_hypertable = cursor.fetchone() is not None

        # If already hypertable and not forcing, exit
        if is_already_hypertable and not force:
            self.stdout.write(self.style.WARNING(
                "Table 'telemetries' is already a hypertable. "
                "Use --force to re-apply settings."
            ))
            return

        self.stdout.write(self.style.NOTICE("Starting TimescaleDB setup..."))

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Enable TimescaleDB extension
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                    self.stdout.write(self.style.SUCCESS("TimescaleDB extension enabled."))

                    # Drop existing primary key
                    cursor.execute("""
                        ALTER TABLE telemetries
                        DROP CONSTRAINT IF EXISTS telemetries_pkey;
                    """)
                    self.stdout.write(self.style.SUCCESS("Dropped old primary key (if existed)."))

                    # Create hypertable
                    cursor.execute("""
                        SELECT create_hypertable(
                            'telemetries',
                            'ts',
                            chunk_time_interval => INTERVAL '7 days',
                            create_default_indexes => TRUE,
                            if_not_exists => TRUE,
                            migrate_data => TRUE
                        );
                    """)
                    self.stdout.write(self.style.SUCCESS("Hypertable created / converted."))

                    # Enable compression
                    cursor.execute("""
                        ALTER TABLE telemetries SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'device_metric_id',
                            timescaledb.compress_orderby = 'ts DESC'
                        );
                    """)
                    self.stdout.write(self.style.SUCCESS("Compression enabled."))

                    # Add compression policy
                    cursor.execute("""
                        SELECT add_compression_policy(
                            'telemetries',
                            INTERVAL '30 days',
                            if_not_exists => TRUE
                        );
                    """)
                    self.stdout.write(self.style.SUCCESS("Compression policy: 30 days"))

                    # Add retention policy
                    cursor.execute("""
                        SELECT add_retention_policy(
                            'telemetries',
                            INTERVAL '1 year',
                            if_not_exists => TRUE
                        );
                    """)
                    self.stdout.write(self.style.SUCCESS("Retention policy: 1 year"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during setup: {str(e)}"))
            raise

        self.stdout.write(self.style.SUCCESS("\nTimescaleDB setup completed successfully!"))
        self.stdout.write(self.style.NOTICE(
            "You can check status with:\n"
            "SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'telemetries';"
        ))