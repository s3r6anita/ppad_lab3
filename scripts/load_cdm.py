import argparse
import getpass
import os
from typing import Any

import psycopg
from cdm_transform import (
    build_activity_monthly,
    build_contributor_activity,
    build_issue_lifecycle_current,
    build_label_analytics,
    build_repository_summary,
    build_repository_version_history,
)
from psycopg import sql
from psycopg.rows import dict_row

LOCK_NAMESPACE = 741203
LOCK_RESOURCE = 2


def read_dds_state(cursor) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cursor.execute("""
        SELECT
            repository_version_id, github_repository_id, full_name, description,
            language, stars_count, forks_count, open_issues_count, archived,
            source_created_at, source_updated_at, valid_from, valid_to,
            is_current, source_batch_id
        FROM dds.repositories_scd2
        ORDER BY github_repository_id, valid_from, repository_version_id
    """)
    all_repos = cursor.fetchall()
    current_repos = [r for r in all_repos if r["is_current"]]

    cursor.execute("""
        SELECT
            issue_version_id, github_issue_id, github_repository_id, issue_number,
            title, state, is_pull_request, author_id, author_login,
            source_created_at, source_updated_at, source_closed_at,
            labels, assignees, valid_from, valid_to, is_current, source_batch_id
        FROM dds.issues_scd2
        ORDER BY github_issue_id, valid_from, issue_version_id
    """)
    all_issues = cursor.fetchall()
    current_issues = [i for i in all_issues if i["is_current"]]
    return all_repos, current_repos, all_issues, current_issues


def build_all_marts(
    current_repos: list[dict[str, Any]], current_issues: list[dict[str, Any]],
    all_repos: list[dict[str, Any]], all_issues: list[dict[str, Any]], batch_id: Any,
) -> dict[str, list[dict[str, Any]]]:
    return {
        "summary": build_repository_summary(current_repos, current_issues, all_repos, all_issues, batch_id),
        "history": build_repository_version_history(all_repos, batch_id),
        "monthly": build_activity_monthly(current_issues, current_repos, batch_id),
        "contributors": build_contributor_activity(current_issues, current_repos, batch_id),
        "labels": build_label_analytics(current_issues, current_repos, batch_id),
        "lifecycle": build_issue_lifecycle_current(current_issues, current_repos, all_issues, batch_id),
    }


def insert_rows(cursor, table_name: str, rows: list[dict[str, Any]]):
    if not rows:
        return
    table = sql.Identifier("cdm", table_name)
    columns = list(rows[0].keys())
    column_idents = sql.SQL(", ").join(sql.Identifier(col) for col in columns)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)

    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        table, column_idents, placeholders
    )
    for row in rows:
        cursor.execute(query, [row[col] for col in columns])


def process_pending_batches(connection):
    with connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            cursor.execute("""
                SELECT p.batch_id, p.stg_started_at, p.processed_at AS dds_processed_at
                FROM dds.processed_batches p
                WHERE NOT EXISTS (
                    SELECT 1 FROM cdm.processed_batches c WHERE c.batch_id = p.batch_id
                )
                ORDER BY p.stg_started_at, p.batch_id
            """)
            new_batches = cursor.fetchall()
            if not new_batches:
                return 0

            latest_batch_id = new_batches[-1]["batch_id"]
            all_repos, current_repos, all_issues, current_issues = read_dds_state(cursor)
            if not current_repos:
                raise ValueError("NO_CURRENT_REPOSITORIES")

            current_repo_ids = {r["github_repository_id"] for r in current_repos}
            orphans = [
                i["github_issue_id"]
                for i in current_issues
                if i["github_repository_id"] not in current_repo_ids
            ]
            if orphans:
                raise ValueError(
                    f"ORPHAN_CURRENT_ISSUES: {len(orphans)} issues reference unknown repositories"
                )

            marts = build_all_marts(
                current_repos, current_issues, all_repos, all_issues, latest_batch_id
            )

            for tbl in ("issue_lifecycle_current", "label_analytics", "contributor_activity", "activity_monthly", "repository_version_history", "repository_summary"):
                cursor.execute(f"DELETE FROM cdm.{tbl}")

            insert_rows(cursor, "repository_summary", marts["summary"])
            insert_rows(cursor, "repository_version_history", marts["history"])
            insert_rows(cursor, "activity_monthly", marts["monthly"])
            insert_rows(cursor, "contributor_activity", marts["contributors"])
            insert_rows(cursor, "label_analytics", marts["labels"])
            insert_rows(cursor, "issue_lifecycle_current", marts["lifecycle"])

            for b in new_batches:
                cursor.execute(
                    """
                    INSERT INTO cdm.processed_batches (
                        batch_id, stg_started_at, dds_processed_at,
                        repository_summary_count, repository_history_count,
                        activity_monthly_count, contributor_activity_count,
                        label_analytics_count, issue_lifecycle_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        b["batch_id"], b["stg_started_at"], b["dds_processed_at"],
                        len(marts["summary"]), len(marts["history"]), len(marts["monthly"]),
                        len(marts["contributors"]), len(marts["labels"]), len(marts["lifecycle"]),
                    ),
                )

            print(
                f"COMMITTED: new_batches={len(new_batches)}; "
                f"summary={len(marts['summary'])}, history={len(marts['history'])}, "
                f"monthly={len(marts['monthly'])}, contrib={len(marts['contributors'])}, "
                f"labels={len(marts['labels'])}, lifecycle={len(marts['lifecycle'])}",
                flush=True,
            )
            return len(new_batches)


def load_cdm(connection):
    acquired = connection.execute(
        "SELECT pg_try_advisory_lock(%s, %s) AS acquired",
        (LOCK_NAMESPACE, LOCK_RESOURCE),
    ).fetchone()["acquired"]

    if not acquired:
        raise RuntimeError("CDM_LOADER_ALREADY_RUNNING")

    try:
        return process_pending_batches(connection)
    finally:
        connection.execute(
            "SELECT pg_advisory_unlock(%s, %s)",
            (LOCK_NAMESPACE, LOCK_RESOURCE),
        )


def main():
    parser = argparse.ArgumentParser(
        description="Load DDS tables into CDM analytical marts."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15432)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", default="ppad_cdm_loader")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.apply:
        parser.error("Writing requires explicit --apply")

    password = (
        os.environ["PGPASSWORD"]
        if "PGPASSWORD" in os.environ
        else os.environ.get("CDM_LOADER_PASSWORD")
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
        application_name="ppad_dds_to_cdm",
        options="-c timezone=UTC",
        autocommit=True,
        row_factory=dict_row,
    ) as connection:
        print(f"database={connection.info.dbname}", flush=True)
        processed = load_cdm(connection)

    print(f"processed_batches={processed}")
    print("CDM_LOAD_OK")


if __name__ == "__main__":
    main()
