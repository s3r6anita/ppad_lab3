import argparse
import getpass
import os
from collections import Counter

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from dds_transform import issue_row, repository_row


LOCK_NAMESPACE = 741203
LOCK_RESOURCE = 1

TABLE_KEYS = {
    "repositories_scd2": "github_repository_id",
    "issues_scd2": "github_issue_id",
}


def read_source(cursor, batch):
    batch_id = batch["batch_id"]

    if batch["finished_at"] is None:
        raise ValueError("SUCCESSFUL_BATCH_WITHOUT_FINISH")

    cursor.execute(
        """
        SELECT *
        FROM stg.repository_loads
        WHERE batch_id = %s
        """,
        (batch_id,),
    )
    loads = cursor.fetchall()
    names = {row["repository_full_name"] for row in loads}

    if (
        not loads
        or len(loads) != batch["expected_repository_count"]
        or len(names) != len(loads)
    ):
        raise ValueError("REPOSITORY_LOAD_SET_MISMATCH")

    cursor.execute(
        """
        SELECT repository_full_name, payload, http_status
        FROM stg.github_repositories_raw
        WHERE batch_id = %s
        """,
        (batch_id,),
    )
    raw_repositories = cursor.fetchall()

    cursor.execute(
        """
        SELECT repository_full_name, github_issue_id, payload, http_status
        FROM stg.github_issues_raw
        WHERE batch_id = %s
        """,
        (batch_id,),
    )
    raw_issues = cursor.fetchall()

    repo_counts = Counter(
        row["repository_full_name"] for row in raw_repositories
    )
    issue_counts = Counter(
        row["repository_full_name"] for row in raw_issues
    )

    if set(repo_counts) != names or not set(issue_counts).issubset(names):
        raise ValueError("RAW_REPOSITORY_SET_MISMATCH")

    for load in loads:
        name = load["repository_full_name"]
        if (
            load["status"] != "success"
            or load["finished_at"] is None
            or load["repository_record_count"] != 1
            or repo_counts[name] != 1
            or load["issue_record_count"] != issue_counts[name]
            or load["issue_page_count"] < 1
        ):
            raise ValueError(f"STG_COUNTERS_MISMATCH: {name}")

    repositories = {}
    repository_ids = {}

    for raw in raw_repositories:
        if raw["http_status"] != 200:
            raise ValueError("REPOSITORY_HTTP_STATUS_NOT_200")

        row = repository_row(raw["payload"])
        key = row["github_repository_id"]
        name = raw["repository_full_name"]

        if key in repositories or name in repository_ids:
            raise ValueError("DUPLICATE_REPOSITORY")

        repositories[key] = row
        repository_ids[name] = key

    issues = {}
    for raw in raw_issues:
        if raw["http_status"] != 200:
            raise ValueError("ISSUE_HTTP_STATUS_NOT_200")

        name = raw["repository_full_name"]
        row = issue_row(
            raw["payload"],
            raw["github_issue_id"],
            repository_ids[name],
        )
        key = row["github_issue_id"]
        if key in issues:
            raise ValueError("DUPLICATE_ISSUE")
        issues[key] = row

    return repositories, issues


def apply_versions(cursor, table_name, rows, batch):
    key_name = TABLE_KEYS[table_name]
    table = sql.Identifier("dds", table_name)
    key_column = sql.Identifier(key_name)

    cursor.execute(
        sql.SQL("""
            SELECT {key}, hash_diff, valid_from, is_current
            FROM {table}
        """).format(key=key_column, table=table)
    )
    history = cursor.fetchall()
    known_keys = {row[key_name] for row in history}
    current = {
        row[key_name]: row for row in history if row["is_current"]
    }

    if known_keys != set(current):
        raise ValueError(f"HISTORY_WITHOUT_CURRENT: {table_name}")

    inserted = 0
    closed = 0
    batch_time = batch["started_at"]

    for key, row in sorted(rows.items()):
        old = current.get(key)

        if old is not None:
            if batch_time < old["valid_from"]:
                raise ValueError("BACKDATED_ENTITY_VERSION")

            if old["hash_diff"] == row["hash_diff"]:
                continue

            if batch_time <= old["valid_from"]:
                raise ValueError("NON_POSITIVE_VERSION_INTERVAL")

            cursor.execute(
                sql.SQL("""
                    UPDATE {table}
                    SET valid_to = %s, is_current = false
                    WHERE {key} = %s AND is_current
                """).format(table=table, key=key_column),
                (batch_time, key),
            )
            if cursor.rowcount != 1:
                raise ValueError("CURRENT_VERSION_UPDATE_MISMATCH")
            closed += 1

        values = {
            **row,
            "valid_from": batch_time,
            "source_batch_id": batch["batch_id"],
        }
        columns = list(values)
        parameters = [
            Jsonb(values[column])
            if column in ("labels", "assignees")
            else values[column]
            for column in columns
        ]

        cursor.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                table,
                sql.SQL(", ").join(
                    sql.Identifier(column) for column in columns
                ),
                sql.SQL(", ").join(
                    sql.Placeholder() for _ in columns
                ),
            ),
            parameters,
        )
        inserted += 1

    return inserted, closed


def process_next_batch(connection):
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
            )
            cursor.execute("""
                SELECT b.*
                FROM stg.load_batches b
                WHERE b.status = 'success'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM dds.processed_batches p
                      WHERE p.batch_id = b.batch_id
                  )
                ORDER BY b.started_at, b.batch_id
                LIMIT 1
            """)
            batch = cursor.fetchone()
            if batch is None:
                return None

            cursor.execute("""
                SELECT stg_started_at, batch_id
                FROM dds.processed_batches
                ORDER BY stg_started_at DESC, batch_id DESC
                LIMIT 1
            """)
            last = cursor.fetchone()

            if last is not None:
                incoming_order = (
                    batch["started_at"], batch["batch_id"]
                )
                last_order = (
                    last["stg_started_at"], last["batch_id"]
                )
                if incoming_order <= last_order:
                    raise ValueError("LATE_BATCH_REQUIRES_REBUILD")

            repositories, issues = read_source(cursor, batch)

            repo_inserted, repo_closed = apply_versions(
                cursor, "repositories_scd2", repositories, batch
            )

            cursor.execute("""
                SELECT github_repository_id
                FROM dds.repositories_scd2
                WHERE is_current
            """)
            existing_repositories = {
                row["github_repository_id"]
                for row in cursor.fetchall()
            }
            if any(
                row["github_repository_id"] not in existing_repositories
                for row in issues.values()
            ):
                raise ValueError("DDS_ISSUE_REPOSITORY_MISSING")

            issue_inserted, issue_closed = apply_versions(
                cursor, "issues_scd2", issues, batch
            )

            cursor.execute(
                """
                INSERT INTO dds.processed_batches (
                    batch_id,
                    stg_started_at,
                    repository_record_count,
                    issue_record_count,
                    repository_versions_inserted,
                    repository_versions_closed,
                    issue_versions_inserted,
                    issue_versions_closed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    batch["batch_id"],
                    batch["started_at"],
                    len(repositories),
                    len(issues),
                    repo_inserted,
                    repo_closed,
                    issue_inserted,
                    issue_closed,
                ),
            )

            result = (
                f"run_id={batch['run_id']} "
                f"repositories: inserted={repo_inserted}, "
                f"closed={repo_closed}; "
                f"issues: inserted={issue_inserted}, "
                f"closed={issue_closed}"
            )

    return result


def load_pending(connection):
    acquired = connection.execute(
        "SELECT pg_try_advisory_lock(%s, %s) AS acquired",
        (LOCK_NAMESPACE, LOCK_RESOURCE),
    ).fetchone()["acquired"]

    if not acquired:
        raise RuntimeError("DDS_LOADER_ALREADY_RUNNING")

    processed = 0
    try:
        while True:
            result = process_next_batch(connection)
            if result is None:
                break
            print(f"COMMITTED: {result}", flush=True)
            processed += 1
    finally:
        connection.execute(
            "SELECT pg_advisory_unlock(%s, %s)",
            (LOCK_NAMESPACE, LOCK_RESOURCE),
        )

    return processed


def main():
    parser = argparse.ArgumentParser(
        description="Load successful STG batches into DDS."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15432)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", default="ppad_admin")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.apply:
        parser.error("Writing requires explicit --apply")

    password = os.environ.get("PGPASSWORD")
    if password is None:
        password = getpass.getpass("Local PostgreSQL password: ")

    with psycopg.connect(
        host=args.host,
        port=args.port,
        dbname=args.database,
        user=args.user,
        password=password,
        connect_timeout=10,
        application_name="ppad_stg_to_dds",
        options="-c timezone=UTC",
        autocommit=True,
        row_factory=dict_row,
    ) as connection:
        print(f"database={connection.info.dbname}", flush=True)
        processed = load_pending(connection)

    print(f"processed_batches={processed}")
    print("DDS_LOAD_OK")


if __name__ == "__main__":
    main()
