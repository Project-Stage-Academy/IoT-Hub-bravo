import psycopg
import os
from django.db import DatabaseError
from celery import shared_task


def fetch_chunks(cur):
    sql_query = """
        SELECT chunk_name
        FROM timescaledb_information.chunks
        WHERE hypertable_name = %s
        ORDER BY chunk_name;
    """

    try:
        cur.execute(sql_query, ("telemetries",))
        chunks = cur.fetchall()

        result = []
        for chunk_name in chunks:
            print(f"{chunk_name}")
            result.append(chunk_name)
        return result
    except DatabaseError as e:
        print(f"Database error: {e}")


def get_job_id(cur):
    sql_query = """
       SELECT job_id, proc_name, config
       FROM timescaledb_information.jobs
       WHERE hypertable_name = %s
       AND proc_name = 'policy_retention';
    """

    try:
        cur.execute(sql_query, ("telemetries",))
        retention_id = cur.fetchone()

        if retention_id:
            job_id, proc_name, config = retention_id
            print(f"Found job_id: {job_id}, proc_name: {proc_name}, config: {config}")
            return job_id
        else:
            print(
                "No job found for hypertable 'telemetries' with proc_name 'policy_retention'"
            )
    except psycopg.DatabaseError as e:
        print(f"Database error: {e}")


def run_retention(cur, retention_id):
    sql_query = f"""
        CALL run_job({retention_id});
    """
    try:
        cur.execute(sql_query)
        print(f"Retention job with ID {retention_id} executed successfully.")
    except DatabaseError as e:
        print(f"Database error during retention: {e}")


@shared_task
def delete_chunks():
    dbname = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST", "db")

    conn = psycopg.connect(
        dbname=dbname, user=user, password=password, host=host, autocommit=True
    )
    cur = conn.cursor()

    before = fetch_chunks(cur)
    retention_id = get_job_id(cur)
    run_retention(cur, retention_id)
    after = fetch_chunks(cur)

    cur.close()
    conn.close()

    return {
        "before": before,
        "after": after,
    }


if __name__ == "__main__":
    delete_chunks()
