import argparse
import getpass
import os

import psycopg
from load_cdm import build_all_marts, read_dds_state
from psycopg.rows import dict_row


def main():
    parser = argparse.ArgumentParser(
        description="Dry-run and check in-memory CDM transformations against DDS."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15432)
    parser.add_argument("--database", default="ppad_dwh")
    parser.add_argument("--user", default="ppad_cdm_loader")
    args = parser.parse_args()

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
        application_name="ppad_cdm_transform_check",
        options="-c timezone=UTC",
        row_factory=dict_row,
    ) as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT batch_id, stg_started_at, processed_at
                FROM dds.processed_batches
                ORDER BY stg_started_at, batch_id
            """)
            batches = cursor.fetchall()
            if not batches:
                raise RuntimeError("NO_PROCESSED_DDS_BATCHES")

            latest_batch_id = batches[-1]["batch_id"]
            all_repos, current_repos, all_issues, current_issues = (
                read_dds_state(cursor)
            )
            marts = build_all_marts(
                current_repos,
                current_issues,
                all_repos,
                all_issues,
                latest_batch_id,
            )

            summary = marts["summary"]
            history = marts["history"]
            monthly = marts["monthly"]
            contributors = marts["contributors"]
            labels = marts["labels"]
            lifecycle = marts["lifecycle"]

            if len(summary) != len(current_repos):
                raise ValueError("SUMMARY_COUNT_MISMATCH")
            if len(history) != len(all_repos):
                raise ValueError("HISTORY_COUNT_MISMATCH")
            if len(lifecycle) != len(current_issues):
                raise ValueError("LIFECYCLE_COUNT_MISMATCH")

            sum_items = sum(s["total_items_count"] for s in summary)
            if sum_items != len(current_issues):
                raise ValueError(
                    f"SUMMARY_ITEMS_MISMATCH: sum={sum_items} vs current_issues={len(current_issues)}"
                )

            sum_monthly = sum(m["created_count"] for m in monthly)
            if sum_monthly != len(current_issues):
                raise ValueError(
                    f"MONTHLY_CREATED_MISMATCH: sum={sum_monthly} vs current_issues={len(current_issues)}"
                )

            sum_contrib = sum(c["total_items_count"] for c in contributors)
            if sum_contrib != len(current_issues):
                raise ValueError(
                    f"CONTRIBUTOR_ITEMS_MISMATCH: sum={sum_contrib} vs current_issues={len(current_issues)}"
                )

            print(f"batches={len(batches)}")
            print(
                f"current_repos={len(current_repos)} all_repo_versions={len(all_repos)}"
            )
            print(
                f"current_issues={len(current_issues)} all_issue_versions={len(all_issues)}"
            )
            print(f"summary_rows={len(summary)}")
            print(f"history_rows={len(history)}")
            print(f"monthly_rows={len(monthly)}")
            print(f"contributor_rows={len(contributors)}")
            print(f"label_rows={len(labels)}")
            print(f"lifecycle_rows={len(lifecycle)}")

    print("CDM_TRANSFORM_OK")


if __name__ == "__main__":
    main()
