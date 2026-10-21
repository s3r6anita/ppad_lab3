import argparse
import getpass
import os

import psycopg


def main():
    parser = argparse.ArgumentParser(
        description="Check CDM connection and table counts."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15432)
    parser.add_argument("--database", default="ppad_dwh")
    parser.add_argument("--user", default="ppad_cdm_loader")
    args = parser.parse_args()

    password = (
        os.environ.get("PGPASSWORD")
        or os.environ.get("CDM_LOADER_PASSWORD")
        or os.environ.get("BI_READER_PASSWORD")
    )
    if password is None:
        password = getpass.getpass("Local PostgreSQL password: ")

    with psycopg.connect(
        host=args.host,
        port=args.port,
        dbname=args.database,
        user=args.user,
        password=password,
        connect_timeout=10,
        application_name="ppad_cdm_connection_check",
        options="-c timezone=UTC",
    ) as connection:
        connection.read_only = True

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    current_database(),
                    current_user,
                    current_setting('TimeZone'),
                    current_setting('transaction_read_only')
            """)
            database, user, timezone, read_only = cursor.fetchone()

            print(f"database={database}")
            print(f"user={user}")
            print(f"timezone={timezone}")
            print(f"transaction_read_only={read_only}")

            cursor.execute("""
                SELECT 'cdm.processed_batches', count(*)
                FROM cdm.processed_batches
                UNION ALL
                SELECT 'cdm.repository_summary', count(*)
                FROM cdm.repository_summary
                UNION ALL
                SELECT 'cdm.repository_version_history', count(*)
                FROM cdm.repository_version_history
                UNION ALL
                SELECT 'cdm.activity_monthly', count(*)
                FROM cdm.activity_monthly
                UNION ALL
                SELECT 'cdm.contributor_activity', count(*)
                FROM cdm.contributor_activity
                UNION ALL
                SELECT 'cdm.label_analytics', count(*)
                FROM cdm.label_analytics
                UNION ALL
                SELECT 'cdm.issue_lifecycle_current', count(*)
                FROM cdm.issue_lifecycle_current
                ORDER BY 1
            """)
            for table_name, count in cursor.fetchall():
                print(f"{table_name}={count}")

    print("CDM_CONNECTION_OK")


if __name__ == "__main__":
    main()
