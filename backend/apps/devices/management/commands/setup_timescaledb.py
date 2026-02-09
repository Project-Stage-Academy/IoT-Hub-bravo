from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.utils import DatabaseError, OperationalError
from django.conf import settings

import traceback
import sys


class Command(BaseCommand):
    help = "Setup TimescaleDB for telemetry table (hypertable, compression, retention)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force setup even if already configured as hypertable",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be executed without making any changes",
        )

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.NOTICE("DRY-RUN mode: no changes will be applied"))

        # ────────────────────────────────────────────────
        # Check TimescaleDB extension availability & status
        # ────────────────────────────────────────────────
        extension_available = False
        extension_installed = False

        try:
            with connection.cursor() as cursor:
                # 1. Is extension available at all?
                cursor.execute(
                    """
                    SELECT 1
                    FROM pg_available_extensions
                    WHERE name = 'timescaledb'
                """
                )
                extension_available = cursor.fetchone() is not None

                if not extension_available:
                    self.stdout.write(
                        self.style.ERROR(
                            "TimescaleDB extension is not available in this PostgreSQL instance.\n"
                            "Please install TimescaleDB first."
                        )
                    )
                    sys.exit(1)

                # 2. Is it already installed?
                cursor.execute(
                    """
                    SELECT extversion
                    FROM pg_extension
                    WHERE extname = 'timescaledb'
                """
                )
                extension_installed = cursor.fetchone() is not None

                if not extension_installed:
                    self.stdout.write(
                        self.style.NOTICE(
                            "TimescaleDB extension is available but not yet enabled."
                        )
                    )

        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f"Cannot check TimescaleDB availability: {e}"))
            sys.exit(1)

        # ────────────────────────────────────────────────
        # Check if 'telemetries' is already a hypertable
        # ────────────────────────────────────────────────
        is_already_hypertable = False

        if extension_installed:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT 1
                        FROM timescaledb_information.hypertables
                        WHERE hypertable_schema = 'public'
                          AND hypertable_name = 'telemetries'
                    """
                    )
                    is_already_hypertable = cursor.fetchone() is not None
            except DatabaseError:
                # view does not exist or other issue → assume not hypertable
                pass

        if is_already_hypertable and not force:
            self.stdout.write(
                self.style.WARNING(
                    "Table 'telemetries' is already a hypertable. "
                    "Use --force to re-apply settings."
                )
            )
            return

        self.stdout.write(self.style.NOTICE("Starting TimescaleDB setup..."))

        # ────────────────────────────────────────────────
        # SQL steps (executed only if not dry-run)
        # ────────────────────────────────────────────────
        sql_steps = [
            (
                "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;",
                "TimescaleDB extension enabled.",
            ),
            # (
            #     "ALTER TABLE telemetries DROP CONSTRAINT IF EXISTS telemetries_pkey;",
            #     "Dropped old primary key constraint (if existed).",
            # ),
            (
                """
                SELECT create_hypertable(
                    'telemetries',
                    'ts',
                    chunk_time_interval => INTERVAL '7 days',
                    create_default_indexes => TRUE,
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
                """.strip(),
                "Hypertable created or converted.",
            ),
            (
                """
                ALTER TABLE telemetries SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'device_metric_id',
                    timescaledb.compress_orderby = 'ts DESC'
                );
                """.strip(),
                "Compression enabled (segment: device_metric_id, order: ts DESC).",
            ),
            (
                """
                SELECT add_compression_policy(
                    'telemetries',
                    INTERVAL '30 days',
                    if_not_exists => TRUE
                );
                """.strip(),
                "Compression policy added: after 30 days.",
            ),
            (
                """
                SELECT add_retention_policy(
                    'telemetries',
                    INTERVAL '1 year',
                    if_not_exists => TRUE
                );
                """.strip(),
                "Retention policy added: keep data for 1 year.",
            ),
        ]

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    for sql, success_message in sql_steps:
                        if dry_run:
                            # Show cleaned SQL without extra indentation
                            cleaned_sql = "\n".join(
                                line.strip() for line in sql.splitlines() if line.strip()
                            )
                            self.stdout.write(
                                self.style.HTTP_INFO(f"Would execute:\n{cleaned_sql}")
                            )
                            continue

                        cursor.execute(sql)
                        self.stdout.write(self.style.SUCCESS(success_message))

        except (DatabaseError, OperationalError) as e:
            self.stdout.write(self.style.ERROR(f"Database error during setup: {e}"))
            if settings.DEBUG:
                self.stdout.write(self.style.ERROR("Full traceback:\n" + traceback.format_exc()))
            raise

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
            if settings.DEBUG:
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
            raise

        # ────────────────────────────────────────────────
        # Final messages
        # ────────────────────────────────────────────────
        if dry_run:
            self.stdout.write(self.style.NOTICE("\nDry run completed — no changes were made."))
        else:
            self.stdout.write(self.style.SUCCESS("\nTimescaleDB setup completed successfully!"))
            self.stdout.write(
                self.style.NOTICE(
                    "You can verify status with:\n"
                    "SELECT * FROM timescaledb_information.hypertables "
                    "WHERE hypertable_name = 'telemetries';"
                )
            )
