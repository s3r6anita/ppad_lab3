import logging
import os
import sys
from datetime import timedelta

import psycopg
from psycopg.rows import dict_row

try:
    import pendulum
    from airflow.decorators import dag, task
    from airflow.providers.postgres.hooks.postgres import PostgresHook
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False


LOG = logging.getLogger(__name__)

SCRIPTS_DIR = os.environ.get(
    "SCRIPTS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")),
)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DEFAULT_QUALITY_SQL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "sql", "17_check_cdm_quality.sql")
)


def execute_stg_to_dds(host, port, dbname, user, password):
    from load_dds import load_pending

    with psycopg.connect(
        host=host,
        port=port or 5432,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=10,
        application_name="airflow_stg_to_dds",
        options="-c timezone=UTC",
        autocommit=True,
        row_factory=dict_row,
    ) as connection:
        processed = load_pending(connection)
        LOG.info("DDS load complete: processed_batches=%s", processed)
        return processed


def execute_dds_to_cdm(host, port, dbname, user, password):
    from load_cdm import load_cdm

    with psycopg.connect(
        host=host,
        port=port or 5432,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=10,
        application_name="airflow_dds_to_cdm",
        options="-c timezone=UTC",
        autocommit=True,
        row_factory=dict_row,
    ) as connection:
        processed = load_cdm(connection)
        LOG.info("CDM load complete: processed_batches=%s", processed)
        return processed


def execute_cdm_quality_check(host, port, dbname, user, password, sql_path=None):
    if sql_path is None:
        sql_path = os.environ.get("QUALITY_SQL_PATH", DEFAULT_QUALITY_SQL_PATH)

    if not os.path.exists(sql_path):
        fallback = "/opt/airflow/sql/17_check_cdm_quality.sql"
        if os.path.exists(fallback):
            sql_path = fallback
        else:
            raise FileNotFoundError(f"Quality SQL file not found: {sql_path}")

    LOG.info("Running CDM quality checks from %s", sql_path)
    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()

    query = "\n".join(
        line
        for line in content.splitlines()
        if not line.strip().upper().startswith(("BEGIN", "SET LOCAL", "COMMIT"))
    )

    with psycopg.connect(
        host=host,
        port=port or 5432,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=10,
        application_name="airflow_cdm_quality_check",
        options="-c timezone=UTC",
    ) as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()

            if len(results) != 9:
                raise RuntimeError(
                    f"Expected 9 CDM quality checks, got {len(results)}"
                )

            failed_checks = []
            for row in results:
                check_name, dds_val, cdm_val, status = row
                LOG.info(
                    "Check: %s | DDS: %s | CDM: %s | Status: %s",
                    check_name,
                    dds_val,
                    cdm_val,
                    status,
                )
                if status != "OK":
                    failed_checks.append(
                        f"{check_name} (status={status}, dds={dds_val}, cdm={cdm_val})"
                    )

            if failed_checks:
                raise RuntimeError(
                    f"CDM quality check failed for: {', '.join(failed_checks)}"
                )

    LOG.info("All CDM quality checks passed successfully (OK).")
    return results


if AIRFLOW_AVAILABLE:
    @dag(
        dag_id="dds_to_cdm",
        start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
        schedule=None,
        catchup=False,
        max_active_runs=1,
        tags=["ppad", "dds", "cdm", "bi"],
    )
    def dds_to_cdm():
        @task(
            retries=1,
            retry_delay=timedelta(minutes=1),
            execution_timeout=timedelta(minutes=20),
            do_xcom_push=False,
        )
        def load_stg_to_dds():
            LOG.info("Connecting to DDS loader...")
            conn_params = PostgresHook.get_connection("github_dds")
            processed = execute_stg_to_dds(
                host=conn_params.host,
                port=conn_params.port or 5432,
                dbname=conn_params.schema,
                user=conn_params.login,
                password=conn_params.password,
            )
            LOG.info("DDS load task finished with %s batches", processed)

        @task(
            retries=1,
            retry_delay=timedelta(minutes=1),
            execution_timeout=timedelta(minutes=20),
            do_xcom_push=False,
        )
        def load_dds_to_cdm():
            LOG.info("Connecting to CDM loader...")
            conn_params = PostgresHook.get_connection("github_cdm")
            processed = execute_dds_to_cdm(
                host=conn_params.host,
                port=conn_params.port or 5432,
                dbname=conn_params.schema,
                user=conn_params.login,
                password=conn_params.password,
            )
            LOG.info("CDM load task finished with %s batches", processed)

        @task(
            retries=1,
            retry_delay=timedelta(minutes=1),
            execution_timeout=timedelta(minutes=5),
            do_xcom_push=False,
        )
        def verify_cdm_quality():
            sql_path = os.environ.get(
                "QUALITY_SQL_PATH",
                DEFAULT_QUALITY_SQL_PATH,
            )
            LOG.info("Connecting to CDM quality checker...")
            conn_params = PostgresHook.get_connection("github_cdm")
            execute_cdm_quality_check(
                host=conn_params.host,
                port=conn_params.port or 5432,
                dbname=conn_params.schema,
                user=conn_params.login,
                password=conn_params.password,
                sql_path=sql_path,
            )

        t1 = load_stg_to_dds()
        t2 = load_dds_to_cdm()
        t3 = verify_cdm_quality()

        t1 >> t2 >> t3


    dds_to_cdm()
