import os
import unittest

import psycopg
from psycopg.rows import dict_row

from dags.dds_to_cdm import (
    execute_cdm_quality_check,
    execute_dds_to_cdm,
    execute_stg_to_dds,
)
from scripts.setup_metabase_dashboard import METABASE_CARDS, render_html_report


class TestDdsToCdmDag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host = os.environ.get("PGHOST", "127.0.0.1")
        cls.port = int(os.environ.get("PGPORT", "5432"))
        cls.dbname = os.environ.get("PGDATABASE", "ppad_cdm_verify")
        cls.dds_user = os.environ.get("DDS_LOADER_USER", "ppad_dds_loader")
        cls.cdm_user = os.environ.get("CDM_LOADER_USER", "ppad_cdm_loader")
        cls.bi_user = os.environ.get("BI_READER_USER", "ppad_bi_reader")
        cls.dds_password = os.environ.get("DDS_LOADER_PASSWORD")
        cls.cdm_password = os.environ.get("CDM_LOADER_PASSWORD")
        cls.bi_password = os.environ.get("BI_READER_PASSWORD")

        cls.sql_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "sql", "17_check_cdm_quality.sql"
            )
        )
        cls.bi_sql_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "sql", "18_metabase_bi_queries.sql"
            )
        )

        cls.live_db_available = False
        try:
            with psycopg.connect(
                host=cls.host,
                port=cls.port,
                dbname=cls.dbname,
                user=cls.cdm_user,
                password=cls.cdm_password,
                connect_timeout=3,
            ):
                cls.live_db_available = True
        except psycopg.Error:
            cls.live_db_available = False

    def test_sql_files_exist(self):
        self.assertTrue(
            os.path.exists(self.sql_path),
            f"Expected {self.sql_path} to exist",
        )
        self.assertTrue(
            os.path.exists(self.bi_sql_path),
            f"Expected {self.bi_sql_path} to exist",
        )

    def test_metabase_cards_definitions(self):
        self.assertEqual(len(METABASE_CARDS), 8)
        for idx, card in enumerate(METABASE_CARDS, start=1):
            self.assertIn("name", card)
            self.assertIn("description", card)
            self.assertIn("query", card)
            self.assertIn("display", card)
            self.assertIn("size_x", card)
            self.assertIn("size_y", card)
            self.assertTrue(
                card["query"].strip().upper().startswith("SELECT"),
                f"Card {card['name']} must start with SELECT",
            )

    def test_metabase_queries_as_bi_reader_against_live_db(self):
        if not self.live_db_available:
            self.skipTest("Live ppad_cdm_verify database not available on localhost")

        with psycopg.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.bi_user,
            password=self.bi_password,
            connect_timeout=5,
            options="-c timezone=UTC",
        ) as conn:
            conn.read_only = True
            with conn.cursor() as cursor:
                for card in METABASE_CARDS:
                    cursor.execute(card["query"])
                    rows = cursor.fetchall()
                    self.assertGreater(
                        len(rows),
                        0,
                        f"Expected query for card '{card['name']}' to return rows",
                    )

    def test_end_to_end_against_live_verify_db(self):
        if not self.live_db_available:
            self.skipTest("Live ppad_cdm_verify database not available on localhost")

        dds_processed = execute_stg_to_dds(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.dds_user,
            password=self.dds_password,
        )
        self.assertIsInstance(dds_processed, int)
        self.assertGreaterEqual(dds_processed, 0)

        cdm_processed = execute_dds_to_cdm(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.cdm_user,
            password=self.cdm_password,
        )
        self.assertIsInstance(cdm_processed, int)
        self.assertGreaterEqual(cdm_processed, 0)

        results = execute_cdm_quality_check(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.cdm_user,
            password=self.cdm_password,
            sql_path=self.sql_path,
        )
        self.assertEqual(len(results), 9)
        for check_name, dds_val, cdm_val, status in results:
            self.assertEqual(
                status,
                "OK",
                f"Check {check_name} did not pass: dds={dds_val}, cdm={cdm_val}, status={status}",
            )

    def test_render_html_report_against_live_db(self):
        if not self.live_db_available:
            self.skipTest("Live ppad_cdm_verify database not available on localhost")

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with psycopg.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.bi_user,
                password=self.bi_password,
                connect_timeout=5,
                options="-c timezone=UTC",
                row_factory=dict_row,
            ) as conn, conn.cursor() as cursor:
                render_html_report(cursor, tmp_path)

            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 500)
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Аналитика репозиториев Kotlin Multiplatform", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()

