# tasks.py
import os
import psycopg
from backend.conf.celery_app import app

@app.task(bind=True)
def cleanup_old_partitions(self, dry_run: bool = False, retention_days: int = 365):
    """
    Celery task для очищення старих partition/chunks та застосування retention policy.
    
    :param dry_run: якщо True, просто виводить SQL без виконання
    :param retention_days: видаляти дані старші ніж X днів
    """
    dbname = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST", "db")

    sql_drop = f"""
    DO $$
    DECLARE
        r RECORD;
    BEGIN
        FOR r IN
            SELECT tablename
            FROM pg_tables
            WHERE tablename LIKE 'telemetries_%'
              AND tablename < 'telemetries_' || TO_CHAR(now() - interval '{retention_days} days', 'YYYY_MM')
        LOOP
            EXECUTE format('DROP TABLE IF EXISTS %I CASCADE;', r.tablename);
        END LOOP;
    END $$;
    """

    sql_retention = f"""
    SELECT add_retention_policy(
        'telemetries',
        INTERVAL '{retention_days} days',
        if_not_exists => TRUE
    );
    """

    if dry_run:
        print("=== DRY RUN ===")
        print("SQL DROP old partitions:\n", sql_drop)
        print("SQL Timescale retention policy:\n", sql_retention)
        return "Dry-run complete, no changes applied."

    try:
        with psycopg.connect(dbname=dbname, user=user, password=password, host=host) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_drop)
                cur.execute(sql_retention)
        return f"Old partitions cleaned and retention policy applied (last {retention_days} days)."
    except Exception as e:
        print(f"Error during cleanup: {e}")
        raise
