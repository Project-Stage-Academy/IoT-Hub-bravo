import psycopg
import os
from django.db import DatabaseError
from celery import shared_task


def fetch_chunks(cur):
    sql_query = """
        SELECT chunk_name, is_compressed
        FROM timescaledb_information.chunks
        WHERE hypertable_name = %s
        ORDER BY chunk_name;
    """

    try:
        cur.execute(sql_query, ("telemetries",))
        chunks = cur.fetchall()
        result = []
        for chunk_name, is_compressed in chunks:
            print(
                f"{chunk_name} -> {'COMPRESSED' if is_compressed else 'NOT COMPRESSED'}"
            )
            result.append((chunk_name, is_compressed))
        return result
    except DatabaseError as e:
        print(f"Database error: {e}")


def get_job_id(cur):
    sql_query = """
       SELECT job_id, proc_name, config
       FROM timescaledb_information.jobs
       WHERE hypertable_name = %s
       AND proc_name = 'policy_compression';
    """

    try:
        cur.execute(sql_query, ("telemetries",))
        compress_id = cur.fetchone()

        if compress_id:
            job_id, proc_name, config = compress_id
            print(f"Found job_id: {job_id}, proc_name: {proc_name}, config: {config}")
            return job_id
        else:
            print(
                "No job found for hypertable 'telemetries' with proc_name 'policy_compression'"
            )
    except DatabaseError as e:
        print(f"Database error: {e}")


def run_compression(cur, compress_id):
    sql_query = f"""
        CALL run_job({compress_id});
    """

    try:
        cur.execute(sql_query)
        print(f"Compression job with ID {compress_id} executed successfully.")
    except DatabaseError as e:
        print(f"Database error during compression: {e}")


@shared_task
def compress_chunks():
    dbname = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST", "db")

    conn = psycopg.connect(
        dbname=dbname, user=user, password=password, host=host, autocommit=True
    )
    cur = conn.cursor()

    before = fetch_chunks(cur)
    compress_id = get_job_id(cur)
    run_compression(cur, compress_id)
    after = fetch_chunks(cur)

    cur.close()
    conn.close()
    return {
        "before": before,
        "after": after,
    }


if __name__ == "__main__":
    compress_chunks()
