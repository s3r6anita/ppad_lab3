import getpass

import psycopg

from dds_transform import issue_row, repository_row


def compare(previous, current):
    new = sum(key not in previous for key in current)
    changed = sum(
        key in previous
        and previous[key]["hash_diff"] != row["hash_diff"]
        for key, row in current.items()
    )
    return new, changed


def main():
    password = getpass.getpass("Local PostgreSQL password: ")
    previous_repositories = {}
    previous_issues = {}
    batch_count = 0

    with psycopg.connect(
        host="127.0.0.1",
        port=15432,
        dbname="ppad_dds_dev",
        user="ppad_admin",
        password=password,
        connect_timeout=10,
        application_name="ppad_dds_transform_check",
        options="-c timezone=UTC",
    ) as connection:
        connection.read_only = True

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT batch_id, run_id
                FROM stg.load_batches
                WHERE status = 'success'
                ORDER BY started_at, batch_id
            """)
            batches = cursor.fetchall()

            for batch_id, run_id in batches:
                cursor.execute("""
                    SELECT repository_full_name, payload
                    FROM stg.github_repositories_raw
                    WHERE batch_id = %s
                """, (batch_id,))

                repositories = {}
                repository_ids = {}
                for name, payload in cursor.fetchall():
                    row = repository_row(payload)
                    key = row["github_repository_id"]
                    if name in repository_ids or key in repositories:
                        raise ValueError("DUPLICATE_REPOSITORY")
                    repository_ids[name] = key
                    repositories[key] = row

                cursor.execute("""
                    SELECT repository_full_name, github_issue_id, payload
                    FROM stg.github_issues_raw
                    WHERE batch_id = %s
                """, (batch_id,))

                issues = {}
                for name, issue_id, payload in cursor.fetchall():
                    if name not in repository_ids:
                        raise ValueError("ISSUE_REPOSITORY_MISSING")
                    row = issue_row(
                        payload, issue_id, repository_ids[name]
                    )
                    if issue_id in issues:
                        raise ValueError("DUPLICATE_ISSUE")
                    issues[issue_id] = row

                repo_new, repo_changed = compare(
                    previous_repositories, repositories
                )
                issue_new, issue_changed = compare(
                    previous_issues, issues
                )
                print(f"run_id={run_id}")
                print(
                    f"repositories={len(repositories)} "
                    f"new={repo_new} changed={repo_changed}"
                )
                print(
                    f"issues_and_pr={len(issues)} "
                    f"new={issue_new} changed={issue_changed}"
                )

                previous_repositories = repositories
                previous_issues = issues
                batch_count += 1

    if batch_count == 0:
        raise RuntimeError("NO_SUCCESSFUL_BATCHES")

    print(f"checked_batches={batch_count}")
    print("DDS_TRANSFORM_OK")


if __name__ == "__main__":
    main()
