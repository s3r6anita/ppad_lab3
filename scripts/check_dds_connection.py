import getpass

import psycopg


def main():
    password = getpass.getpass("Local PostgreSQL password: ")

    with psycopg.connect(
        host="127.0.0.1",
        port=15432,
        dbname="ppad_dds_dev",
        user="ppad_admin",
        password=password,
        connect_timeout=10,
        application_name="ppad_dds_connection_check",
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
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'btree_gist'
            """)
            extension = cursor.fetchone()
            if extension is None:
                raise RuntimeError("BTREE_GIST_MISSING")
            print(f"btree_gist={extension[0]}")

            cursor.execute("""
                SELECT conrelid::regclass::text
                FROM pg_constraint
                WHERE connamespace = 'dds'::regnamespace
                  AND contype = 'x'
                ORDER BY conrelid::regclass::text
            """)
            exclusions = {row[0] for row in cursor.fetchall()}
            expected = {
                "dds.repositories_scd2",
                "dds.issues_scd2",
            }
            if exclusions != expected:
                raise RuntimeError("DDS_EXCLUSION_CONSTRAINTS_MISMATCH")
            print("exclusion_constraints=OK")

            cursor.execute("""
                SELECT 'stg.load_batches', count(*)
                FROM stg.load_batches
                UNION ALL
                SELECT 'stg.github_repositories_raw', count(*)
                FROM stg.github_repositories_raw
                UNION ALL
                SELECT 'stg.github_issues_raw', count(*)
                FROM stg.github_issues_raw
                UNION ALL
                SELECT 'dds.repositories_scd2', count(*)
                FROM dds.repositories_scd2
                UNION ALL
                SELECT 'dds.issues_scd2', count(*)
                FROM dds.issues_scd2
                UNION ALL
                SELECT 'dds.processed_batches', count(*)
                FROM dds.processed_batches
                ORDER BY 1
            """)
            for table_name, count in cursor.fetchall():
                print(f"{table_name}={count}")

    print("DDS_CONNECTION_OK")


if __name__ == "__main__":
    main()
