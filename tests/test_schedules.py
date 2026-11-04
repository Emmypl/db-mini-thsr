"""GET /schedules contract checks against an isolated PostgreSQL schema."""

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
class ScheduleApiTests(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.schema = "schedules_test_" + uuid.uuid4().hex
        self.conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema))
        )
        self.conn.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema))
        )
        self.conn.execute((ROOT / "schema/schema.sql").read_text())
        self.connection_patch = patch(
            "app.services.schedule_service.get_connection", self.connect
        )
        self.connection_patch.start()
        self.client = create_app().test_client()
        self.conn.execute("INSERT INTO users VALUES ('U', 'Passenger', NULL)")
        self.conn.execute(
            "INSERT INTO stations VALUES ('A','North',1),('B','Middle',2),('C','South',3),('X','Unserved',4)"
        )
        self.conn.execute(
            "INSERT INTO trains VALUES ('0001','S',1),('0002','S',1),('0003','N',1),('0004','S',1)"
        )
        self.conn.execute(
            "INSERT INTO train_stops VALUES ('0001',1,'A','06:00'),('0001',2,'B','06:30'),('0001',3,'C','07:00'),('0002',1,'A','06:00'),('0002',2,'B','06:40'),('0002',3,'C','07:10'),('0003',1,'C','08:00'),('0003',2,'B','08:30'),('0003',3,'A','09:00'),('0004',1,'A','05:00'),('0004',2,'C','06:00')"
        )
        self.conn.execute(
            "INSERT INTO train_runs SELECT train_no, DATE '2026-12-07' FROM trains"
        )
        self.conn.execute("INSERT INTO train_runs VALUES ('0001','2026-12-08')")
        self.conn.execute(
            "INSERT INTO seats SELECT train_no,1,1,letter FROM trains CROSS JOIN (VALUES ('A'),('B')) AS letters(letter)"
        )

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

    def search(self, **overrides):
        params = {"date": "2026-12-07", "from_station_id": "A", "to_station_id": "C"}
        params.update(overrides)
        return self.client.get("/schedules", query_string=params)

    def book(
        self,
        start=1,
        end=2,
        letter="A",
        day="2026-12-07",
        train="0001",
        cancelled=False,
    ):
        booking = self.conn.execute(
            "INSERT INTO bookings (user_id,train_no,service_date,from_stop_seq,to_stop_seq) VALUES ('U',%s,%s,%s,%s) RETURNING booking_id",
            (train, day, start, end),
        ).fetchone()[0]
        self.conn.execute(
            "INSERT INTO tickets VALUES (%s,%s,1,1,%s)", (booking, train, letter)
        )
        if cancelled:
            self.conn.execute(
                "UPDATE bookings SET status='cancelled',cancelled_at=CURRENT_TIMESTAMP WHERE booking_id=%s",
                (booking,),
            )

    def remaining(self, **kwargs):
        response = self.search(**kwargs)
        self.assertEqual(response.status_code, 200)
        return next(
            r["remain_seats"] for r in response.get_json() if r["train_no"] == "0001"
        )

    def test_order_and_response_contract(self):
        response = self.search()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        result = response.get_json()
        self.assertEqual([r["train_no"] for r in result], ["0004", "0001", "0002"])
        self.assertEqual(
            result[1],
            {
                "train_no": "0001",
                "date": "2026-12-07",
                "departure_time": "06:00",
                "arrival_time": "07:00",
                "remain_seats": 2,
            },
        )

    def test_northbound_and_unserved_station(self):
        result = self.search(from_station_id="C", to_station_id="A").get_json()
        self.assertEqual([r["train_no"] for r in result], ["0003"])
        self.assertEqual(result[0]["departure_time"], "08:00")
        self.assertEqual(self.search(to_station_id="X").get_json(), [])
        self.assertNotIn(
            "0004", [r["train_no"] for r in self.search(to_station_id="B").get_json()]
        )

    def test_dates_without_runs_and_outside_period(self):
        self.assertEqual(
            [r["train_no"] for r in self.search(date="2026-12-08").get_json()], ["0001"]
        )
        for day in ["2026-12-09", "2026-11-30", "2027-02-01"]:
            response = self.search(date=day)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), [])

    def test_inclusive_filters_at_requested_station(self):
        result = self.search(
            from_station_id="B", departure_time_from="06:30", departure_time_to="06:30"
        ).get_json()
        self.assertEqual([r["train_no"] for r in result], ["0001"])
        self.assertEqual(result[0]["departure_time"], "06:30")
        self.assertEqual(
            [r["train_no"] for r in self.search(departure_time_to="05:00").get_json()],
            ["0004"],
        )
        self.assertEqual(
            [
                r["train_no"]
                for r in self.search(departure_time_from="06:00").get_json()
            ],
            ["0001", "0002"],
        )

    def test_invalid_parameters(self):
        cases = [
            dict(date=""),
            dict(date="2026-2-01"),
            dict(date="2026-02-30"),
            dict(date="20261207"),
            dict(from_station_id=""),
            dict(to_station_id="MISSING"),
            dict(to_station_id="A"),
            dict(from_station_id="A' OR 1=1 --"),
            dict(departure_time_from="24:00"),
            dict(departure_time_to="06:00:00"),
            dict(departure_time_to=""),
            dict(departure_time_from="07:00", departure_time_to="06:00"),
        ]
        for params in cases:
            with self.subTest(params=params):
                response = self.search(**params)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.get_json()["error"]["code"], "INVALID_PARAMETER"
                )
        self.assertEqual(self.client.get("/schedules").status_code, 422)

    def test_overlap_and_adjoining_intervals(self):
        self.book(start=1, end=2)
        self.assertEqual(self.remaining(), 1)
        self.assertEqual(self.remaining(to_station_id="B"), 1)
        self.assertEqual(self.remaining(from_station_id="B"), 2)
        # Two adjoining tickets on one seat still subtract only one seat for A->C.
        self.book(start=2, end=3)
        self.assertEqual(self.remaining(), 1)

    def test_whole_journey_not_minimum_segment_capacity(self):
        self.book(start=1, end=2, letter="A")
        self.book(start=2, end=3, letter="B")
        self.assertEqual(self.remaining(to_station_id="B"), 1)
        self.assertEqual(self.remaining(from_station_id="B"), 1)
        self.assertEqual(self.remaining(), 0)
        self.assertIn("0001", [r["train_no"] for r in self.search().get_json()])

    def test_cancelled_other_dates_and_other_trains_do_not_block(self):
        self.book(start=1, end=3, cancelled=True)
        self.book(start=1, end=3, day="2026-12-08")
        self.book(start=1, end=3, train="0002")
        self.assertEqual(self.remaining(), 2)


if __name__ == "__main__":
    unittest.main()
