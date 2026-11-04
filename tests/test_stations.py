"""GET /stations contract checks against an isolated PostgreSQL schema."""

import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
for key, value in {
    "DEBUG": "false",
    "LOG_LEVEL": "WARNING",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "unused",
    "DB_USER": "unused",
    "DB_PASSWORD": "unused",
}.items():
    os.environ.setdefault(key, value)
from app import create_app  # noqa: E402


@unittest.skipUnless(
    os.environ.get("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to run PostgreSQL tests"
)
class StationApiTests(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.schema = "stations_test_" + uuid.uuid4().hex
        self.conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema))
        )
        self.conn.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema))
        )
        self.conn.execute((ROOT / "schema/schema.sql").read_text())
        self.connection_patch = patch(
            "app.services.station_service.get_connection", self.connect
        )
        self.connection_patch.start()
        self.client = create_app().test_client()

    def connect(self):
        conn = psycopg.connect(
            os.environ["TEST_DATABASE_URL"], autocommit=True, row_factory=dict_row
        )
        conn.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema))
        )
        return conn

    def tearDown(self):
        self.connection_patch.stop()
        self.conn.execute("SET search_path TO public")
        self.conn.execute(
            sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema))
        )
        self.conn.close()

    def test_empty_database_returns_json_array(self):
        response = self.client.get("/stations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.get_json(), [])

    def test_sort_by_sequence_and_exact_fields(self):
        self.conn.execute(
            "INSERT INTO stations VALUES ('AAA','South',30), ('ZZZ','北站',10), ('MMM','Middle',20)"
        )
        response = self.client.get("/stations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            [
                {"station_id": "ZZZ", "name": "北站"},
                {"station_id": "MMM", "name": "Middle"},
                {"station_id": "AAA", "name": "South"},
            ],
        )

    def test_reads_updated_database_without_login(self):
        self.conn.execute("INSERT INTO stations VALUES ('CUSTOM','Original',1)")
        self.assertEqual(self.client.get("/stations").get_json()[0]["name"], "Original")
        self.conn.execute("UPDATE stations SET name = 'Changed'")
        self.assertEqual(
            self.client.get("/stations").get_json(),
            [{"station_id": "CUSTOM", "name": "Changed"}],
        )


if __name__ == "__main__":
    unittest.main()
