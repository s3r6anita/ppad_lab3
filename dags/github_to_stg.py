import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import closing
from datetime import timedelta

import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.providers.postgres.hooks.postgres import PostgresHook
from psycopg2.extras import Json, execute_values


LOG = logging.getLogger(__name__)
CONFIG_PATH = "/opt/airflow/config/repositories.json"
API_ROOT = "https://api.github.com"
MAX_ISSUE_PAGES = 500


def read_repositories():
    with open(CONFIG_PATH, encoding="utf-8") as file:
        repositories = json.load(file).get("repositories")

    if not isinstance(repositories, list) or not repositories:
        raise ValueError("INVALID_REPOSITORY_LIST")

    for name in repositories:
        if not isinstance(name, str):
            raise ValueError("INVALID_REPOSITORY_NAME")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            raise ValueError("INVALID_REPOSITORY_NAME")

    if len({name.lower() for name in repositories}) != len(repositories):
        raise ValueError("DUPLICATE_REPOSITORIES")

    return repositories


def github_get(url, token):
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.github.com"
    ):
        raise ValueError("UNEXPECTED_API_URL")

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ppad-lab3",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError("UNEXPECTED_HTTP_STATUS")

            payload = json.load(response)
            link = response.headers.get("Link", "")
            remaining = response.headers.get("X-RateLimit-Remaining")
            LOG.info("GitHub response received; remaining=%s", remaining)

    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"GITHUB_HTTP_{error.code}"
        ) from None
    except urllib.error.URLError:
        raise RuntimeError("GITHUB_NETWORK_ERROR") from None

    next_url = None
    for match in re.finditer(r'<([^>]+)>;\s*rel="([^"]+)"', link):
        if "next" in match.group(2).split():
            next_url = match.group(1)
            break

    return payload, next_url


def collect_repository(name, token):
    repository_url = f"{API_ROOT}/repos/{name}"
    repository, _ = github_get(repository_url, token)

    if not isinstance(repository, dict) or "id" not in repository:
        raise ValueError("INVALID_REPOSITORY_RESPONSE")
    if not repository.get("has_issues"):
        raise ValueError("ISSUES_DISABLED")

    url = (
        f"{repository_url}/issues"
        "?state=all&per_page=100&sort=created&direction=asc"
    )
    issues = {}
    visited = set()
    page_count = 0

    while url:
        if url in visited:
            raise RuntimeError("PAGINATION_LOOP")
        if page_count >= MAX_ISSUE_PAGES:
            raise RuntimeError("ISSUE_PAGE_LIMIT_EXCEEDED")

        visited.add(url)
        payload, next_url = github_get(url, token)

        if not isinstance(payload, list):
            raise ValueError("INVALID_ISSUES_RESPONSE")

        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("INVALID_ISSUE_OBJECT")

            issue_id = item.get("id")
            if type(issue_id) is not int:
                raise ValueError("INVALID_ISSUE_ID")

            issues[issue_id] = (item, url)

        page_count += 1
        LOG.info(
            "%s: page=%s, unique_items=%s",
            name,
            page_count,
            len(issues),
        )
        url = next_url

    return repository, repository_url, issues, page_count


def load_one_repository(connection, batch_id, name, token):
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status
                FROM stg.repository_loads
                WHERE batch_id = %s AND repository_full_name = %s
                """,
                (batch_id, name),
            )
            row = cursor.fetchone()

            if row and row[0] == "success":
                LOG.info("%s: already loaded, skipping", name)
                return

            cursor.execute(
                """
                INSERT INTO stg.repository_loads (
                    batch_id, repository_full_name, status
                )
                VALUES (%s, %s, 'running')
                ON CONFLICT (batch_id, repository_full_name)
                DO UPDATE SET
                    status = 'running',
                    started_at = clock_timestamp(),
                    finished_at = NULL,
                    error_message = NULL,
                    repository_record_count = 0,
                    issue_record_count = 0,
                    issue_page_count = 0
                """,
                (batch_id, name),
            )

    try:
        repository, source_url, issues, pages = collect_repository(
            name, token
        )

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO stg.github_repositories_raw (
                        batch_id, repository_full_name,
                        payload, source_url, http_status
                    )
                    VALUES (%s, %s, %s, %s, 200)
                    """,
                    (batch_id, name, Json(repository), source_url),
                )

                if issues:
                    rows = [
                        (
                            batch_id,
                            name,
                            issue_id,
                            Json(item),
                            page_url,
                            200,
                        )
                        for issue_id, (item, page_url) in issues.items()
                    ]
                    execute_values(
                        cursor,
                        """
                        INSERT INTO stg.github_issues_raw (
                            batch_id, repository_full_name,
                            github_issue_id, payload,
                            source_url, http_status
                        )
                        VALUES %s
                        """,
                        rows,
                        page_size=500,
                    )

                cursor.execute(
                    """
                    UPDATE stg.repository_loads
                    SET status = 'success',
                        finished_at = clock_timestamp(),
                        repository_record_count = 1,
                        issue_record_count = %s,
                        issue_page_count = %s,
                        error_message = NULL
                    WHERE batch_id = %s
                      AND repository_full_name = %s
                    """,
                    (len(issues), pages, batch_id, name),
                )

        LOG.info("%s: saved %s items, %s pages", name, len(issues), pages)

    except Exception as error:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE stg.repository_loads
                    SET status = 'failed',
                        finished_at = clock_timestamp(),
                        error_message = %s
                    WHERE batch_id = %s
                      AND repository_full_name = %s
                    """,
                    (type(error).__name__, batch_id, name),
                )
        raise


def validate_batch(cursor, batch_id, repositories):
    cursor.execute(
        """
        SELECT
            r.repository_full_name,
            r.status,
            r.repository_record_count,
            r.issue_record_count,
            r.issue_page_count,
            (
                SELECT count(*)
                FROM stg.github_repositories_raw p
                WHERE p.batch_id = r.batch_id
                  AND p.repository_full_name = r.repository_full_name
            ),
            (
                SELECT count(*)
                FROM stg.github_issues_raw i
                WHERE i.batch_id = r.batch_id
                  AND i.repository_full_name = r.repository_full_name
            )
        FROM stg.repository_loads r
        WHERE r.batch_id = %s
        """,
        (batch_id,),
    )
    rows = cursor.fetchall()

    if {row[0] for row in rows} != set(repositories):
        raise RuntimeError("BATCH_REPOSITORY_SET_MISMATCH")

    for name, status, repo_count, issue_count, pages, actual_repo, actual_issues in rows:
        if (
            status != "success"
            or repo_count != 1
            or actual_repo != 1
            or issue_count != actual_issues
            or pages < 1
        ):
            raise RuntimeError(f"BATCH_VALIDATION_FAILED: {name}")


@dag(
    dag_id="github_to_stg",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["ppad", "github", "stg"],
)
def github_to_stg():
    @task(
        retries=2,
        retry_delay=timedelta(minutes=2),
        execution_timeout=timedelta(minutes=45),
        do_xcom_push=False,
    )
    def load_github():
        repositories = read_repositories()
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if not token or token == "replace_with_github_token":
            raise ValueError("GITHUB_TOKEN_MISSING")

        context = get_current_context()
        dag_id = context["dag"].dag_id
        run_id = context["run_id"]
        batch_id = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"{dag_id}:{run_id}")
        )

        hook = PostgresHook(postgres_conn_id="github_stg")

        with closing(hook.get_conn()) as connection:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO stg.load_batches (
                            batch_id, dag_id, run_id,
                            expected_repository_count
                        )
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (dag_id, run_id) DO NOTHING
                        """,
                        (batch_id, dag_id, run_id, len(repositories)),
                    )
                    cursor.execute(
                        """
                        SELECT status, expected_repository_count
                        FROM stg.load_batches
                        WHERE batch_id = %s
                        """,
                        (batch_id,),
                    )
                    status, expected_count = cursor.fetchone()

                    if status == "success":
                        LOG.info("Batch %s already successful", batch_id)
                        return

                    if expected_count != len(repositories):
                        raise RuntimeError("BATCH_CONFIG_CHANGED")

                    cursor.execute(
                        """
                        SELECT repository_full_name
                        FROM stg.repository_loads
                        WHERE batch_id = %s
                        """,
                        (batch_id,),
                    )
                    existing = {row[0] for row in cursor.fetchall()}
                    if not existing.issubset(set(repositories)):
                        raise RuntimeError("BATCH_CONFIG_CHANGED")

                    cursor.execute(
                        """
                        UPDATE stg.load_batches
                        SET status = 'running',
                            finished_at = NULL,
                            error_message = NULL
                        WHERE batch_id = %s
                        """,
                        (batch_id,),
                    )

            LOG.info("Loading batch %s", batch_id)

            try:
                for name in repositories:
                    load_one_repository(
                        connection, batch_id, name, token
                    )

                with connection:
                    with connection.cursor() as cursor:
                        validate_batch(cursor, batch_id, repositories)
                        cursor.execute(
                            """
                            UPDATE stg.load_batches
                            SET status = 'success',
                                finished_at = clock_timestamp(),
                                error_message = NULL
                            WHERE batch_id = %s
                            """,
                            (batch_id,),
                        )

                LOG.info("Batch %s completed successfully", batch_id)

            except Exception as error:
                with connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE stg.load_batches
                            SET status = 'failed',
                                finished_at = clock_timestamp(),
                                error_message = %s
                            WHERE batch_id = %s
                            """,
                            (type(error).__name__, batch_id),
                        )
                raise

    load_github()


github_to_stg()