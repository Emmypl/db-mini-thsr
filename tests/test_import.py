"""Integration tests: TEST_DATABASE_URL must point to a disposable PostgreSQL."""

import os
import shutil
import sys
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

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
from db_init import initialize  # noqa: E402


@unittest.skipUnless(
    os.environ.get("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to run PostgreSQL tests"
)
class ImportTests(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(
            os.environ["TEST_DATABASE_URL"], autocommit=True, row_factory=dict_row
        )
        self.schema = "import_test_" + uuid.uuid4().hex
        self.conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema))
        )
        self.conn.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema))
        )
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        (self.data / "users.csv").write_text(
            "\ufeffuser_id,name,phone\nCUSTOM,Passenger,\n\n"
        )
        (self.data / "stations.csv").write_text(
            "station_id,name,seq\nNORTH,North,1\nMID,Middle,2\nSOUTH,South,3\n"
        )
        # Deliberately reordered headers and custom station IDs.
        (self.data / "timetable.csv").write_text(
            "train_no,direction,days,cars,SOUTH,NORTH,MID\n0007,N,67,2,08:00,09:00,\n0008,S,12345,1,11:00,10:00,10:30\n"
        )

    def tearDown(self):
        self.conn.execute("SET search_path TO public")
        self.conn.execute(
            sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema))
        )
        self.conn.close()
        self.temp.cleanup()

    def load(self):
        return initialize(self.conn, self.data, ROOT / "schema/schema.sql")

    def scalar(self, query):
        return next(iter(self.conn.execute(query).fetchone().values()))

    def test_custom_data_and_restart_preserves_booking(self):
        self.assertTrue(self.load())
        self.assertEqual(self.scalar("SELECT count(*) FROM seats"), 60)
        self.assertEqual(
            self.scalar("SELECT count(*) FROM train_runs WHERE train_no = '0007'"), 18
        )
        self.assertEqual(
            self.scalar("SELECT count(*) FROM train_runs WHERE train_no = '0008'"), 44
        )
        self.assertEqual(
            self.scalar(
                "SELECT count(*) FROM train_runs WHERE extract(isodow FROM service_date) NOT IN (6,7) AND train_no = '0007'"
            ),
            0,
        )
        stops = self.conn.execute(
            "SELECT station_id, stop_seq FROM train_stops WHERE train_no = '0007' ORDER BY stop_seq"
        ).fetchall()
        self.assertEqual(
            stops,
            [
                {"station_id": "SOUTH", "stop_seq": 1},
                {"station_id": "NORTH", "stop_seq": 2},
            ],
        )
        self.assertEqual(
            str(self.scalar("SELECT max(service_date) FROM train_runs")), "2027-01-31"
        )
        self.assertEqual(
            str(self.scalar("SELECT min(service_date) FROM train_runs")), "2026-12-01"
        )
        booking = self.conn.execute(
            "INSERT INTO bookings (user_id, train_no, service_date, from_stop_seq, to_stop_seq) VALUES ('CUSTOM','0007','2026-12-05',1,2) RETURNING booking_id"
        ).fetchone()["booking_id"]
        self.conn.execute("INSERT INTO tickets VALUES (%s, '0007',1,1,'A')", (booking,))
        # Restart must not even reread CSVs once initialization is complete.
        (self.data / "timetable.csv").unlink()
        self.assertFalse(self.load())
        self.assertEqual(self.scalar("SELECT count(*) FROM tickets"), 1)
        self.assertEqual(self.scalar("SELECT booking_id FROM bookings"), booking)
        self.assertEqual(self.scalar("SELECT count(*) FROM seats"), 60)

    def test_concurrent_startup_imports_once(self):
        barrier = Barrier(2)

        def start():
            with psycopg.connect(
                os.environ["TEST_DATABASE_URL"], autocommit=True, row_factory=dict_row
            ) as conn:
                conn.execute(
                    sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema))
                )
                barrier.wait(timeout=10)
                return initialize(conn, self.data, ROOT / "schema/schema.sql")

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: start(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.scalar("SELECT count(*) FROM trains"), 2)
        self.assertEqual(self.scalar("SELECT count(*) FROM seats"), 60)

    def test_empty_precreated_schema(self):
        self.conn.execute((ROOT / "schema/schema.sql").read_text())
        self.assertTrue(self.load())

    def test_public_dataset(self):
        for name in ("users.csv", "stations.csv", "timetable.csv"):
            shutil.copy(ROOT / "data" / name, self.data / name)
        self.assertTrue(self.load())
        self.assertEqual(self.scalar("SELECT count(*) FROM trains"), 22)
        self.assertEqual(
            self.scalar("SELECT count(*) FROM seats"),
            self.scalar("SELECT sum(cars) * 20 FROM trains"),
        )
        self.assertEqual(
            self.scalar(
                "SELECT count(*) FROM train_runs r WHERE NOT EXISTS (SELECT 1 FROM train_operating_days d WHERE d.train_no = r.train_no AND d.weekday = extract(isodow FROM r.service_date))"
            ),
            0,
        )

    def test_bad_csv_rolls_back_everything_then_retry(self):
        path = self.data / "timetable.csv"
        valid = path.read_text()
        invalids = [
            valid.replace("10:30", "09:30"),
            valid.replace(",67,", ",68,"),
            valid.replace(",67,", ",66,"),
            valid.replace(",2,", ",0,"),
            valid.replace("08:00", "24:00"),
            valid.replace("SOUTH,NORTH,MID", "UNKNOWN,NORTH,MID"),
            valid + "broken,row\n",
            valid + valid.splitlines()[1] + "\n",
        ]
        for invalid in invalids:
            with self.subTest(invalid=invalid):
                path.write_text(invalid)
                with self.assertRaises((ValueError, psycopg.IntegrityError)):
                    self.load()
                self.assertIsNone(self.scalar("SELECT to_regclass('users')"))
        path.write_text(valid)
        self.assertTrue(self.load())

    def test_legacy_schema_is_preserved(self):
        self.conn.execute(
            "CREATE TABLE users (user_id text); INSERT INTO users VALUES ('keep')"
        )
        with self.assertRaisesRegex(RuntimeError, "legacy"):
            self.load()
        self.assertEqual(self.scalar("SELECT user_id FROM users"), "keep")

    def test_populated_unmarked_schema_is_preserved(self):
        self.conn.execute((ROOT / "schema/schema.sql").read_text())
        self.conn.execute("INSERT INTO users (user_id,name) VALUES ('keep','Keep')")
        with self.assertRaisesRegex(RuntimeError, "marker"):
            self.load()
        self.assertEqual(self.scalar("SELECT user_id FROM users"), "keep")


if __name__ == "__main__":
    unittest.main()
