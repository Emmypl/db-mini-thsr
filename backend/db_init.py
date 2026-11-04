"""Atomically import course CSVs and generate seats and dated train runs."""

import csv
import logging
import re
from datetime import date, time, timedelta
from pathlib import Path

import psycopg
from app.core import config
from app.core.database import get_connection
from psycopg import sql

logger = logging.getLogger("db_init")
START_DATE = date(2026, 12, 1)
END_DATE = date(2027, 1, 31)
TABLES = (
    "users",
    "stations",
    "trains",
    "train_operating_days",
    "train_stops",
    "seats",
    "train_runs",
    "bookings",
    "tickets",
)
# A transactional table comment marks successful import, without a tenth table.
INITIALIZED = "mini-thsr:csv-import:v1"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Accept UTF-8 BOM, surrounding whitespace and blank lines; reject bad rows."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = [value.strip() for value in next(reader, [])]
        if (
            not headers
            or any(not h for h in headers)
            or len(set(headers)) != len(headers)
        ):
            raise ValueError(f"{path.name}: missing or duplicate column names")
        rows = []
        for line, values in enumerate(reader, 2):
            if not any(value.strip() for value in values):
                continue
            if len(values) != len(headers):
                raise ValueError(f"{path.name}:{line}: wrong number of fields")
            rows.append(
                dict(zip(headers, (value.strip() for value in values), strict=True))
            )
    return headers, rows


def insert_rows(conn, table, columns, rows):
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    with conn.cursor() as cursor:
        cursor.executemany(query, rows)
    logger.info("import %s: %d rows", table, len(rows))


def import_reference(conn, data_dir):
    for table, columns in (
        ("users", ["user_id", "name", "phone"]),
        ("stations", ["station_id", "name", "seq"]),
    ):
        headers, records = read_csv(data_dir / f"{table}.csv")
        if set(headers) != set(columns):
            raise ValueError(f"{table}.csv: expected columns {columns}")
        if any(not r[columns[0]] for r in records):
            raise ValueError(f"{table}.csv: empty identifier")
        insert_rows(
            conn,
            table,
            columns,
            [tuple(r[c] or None for c in columns) for r in records],
        )


def import_timetable(conn, data_dir):
    stations = conn.execute("SELECT station_id FROM stations ORDER BY seq").fetchall()
    station_ids = [station["station_id"] for station in stations]
    metadata = {"train_no", "direction", "days", "cars"}
    headers, records = read_csv(data_dir / "timetable.csv")
    if metadata & set(station_ids) or set(headers) != metadata | set(station_ids):
        raise ValueError("timetable.csv: station columns must match stations.csv")
    for record in records:
        number, direction, days = (
            record["train_no"],
            record["direction"],
            record["days"],
        )
        if not number or direction not in ("S", "N"):
            raise ValueError(f"timetable.csv: invalid train or direction: {number!r}")
        if (
            not days
            or any(day not in "1234567" for day in days)
            or len(set(days)) != len(days)
        ):
            raise ValueError(f"{number}: invalid operating days")
        if not re.fullmatch(r"[0-9]+", record["cars"]) or int(record["cars"]) < 1:
            raise ValueError(f"{number}: cars must be a positive integer")
        cars = int(record["cars"])
        stops = []
        order = station_ids if direction == "S" else list(reversed(station_ids))
        for station in order:
            value = record[station]
            if not value:
                continue
            if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
                raise ValueError(f"{number}/{station}: invalid HH:MM time")
            stop_time = time.fromisoformat(value)
            if stops and stop_time <= stops[-1][3]:
                raise ValueError(f"{number}: times must increase in travel direction")
            stops.append((number, len(stops) + 1, station, stop_time))
        if len(stops) < 2:
            raise ValueError(f"{number}: at least two stops are required")
        insert_rows(
            conn,
            "trains",
            ["train_no", "direction", "cars"],
            [(number, direction, cars)],
        )
        insert_rows(
            conn,
            "train_operating_days",
            ["train_no", "weekday"],
            [(number, int(d)) for d in days],
        )
        insert_rows(
            conn,
            "train_stops",
            ["train_no", "stop_seq", "station_id", "stop_time"],
            stops,
        )
        insert_rows(
            conn,
            "seats",
            ["train_no", "car_no", "row_no", "seat_letter"],
            [
                (number, car, row, letter)
                for car in range(1, cars + 1)
                for row in range(1, 5)
                for letter in "ABCDE"
            ],
        )
        dates = [
            START_DATE + timedelta(days=i)
            for i in range((END_DATE - START_DATE).days + 1)
        ]
        insert_rows(
            conn,
            "train_runs",
            ["train_no", "service_date"],
            [(number, day) for day in dates if str(day.isoweekday()) in days],
        )


def initialize(conn: psycopg.Connection, data_dir: Path, schema_file: Path) -> bool:
    """Return True after import, False on restart. Never reset an existing database."""
    with conn.transaction():
        # Serialize competing startup jobs; READ COMMITTED sees the first job's commit.
        conn.execute("SELECT pg_advisory_xact_lock(724031, 1)")
        present = {
            name
            for name in TABLES
            if conn.execute("SELECT to_regclass(%s) AS table_name", (name,)).fetchone()[
                "table_name"
            ]
        }
        if present and present != set(TABLES):
            raise RuntimeError(
                "Incomplete or legacy schema: apply a reviewed migration, or use a fresh test database. No data was changed."
            )
        if present:
            marker = conn.execute(
                "SELECT obj_description('train_runs'::regclass, 'pg_class') AS marker"
            ).fetchone()["marker"]
            if marker == INITIALIZED:
                logger.info("database already initialized, skip")
                return False
            for name in TABLES:
                if conn.execute(
                    sql.SQL("SELECT EXISTS (SELECT 1 FROM {}) AS populated").format(
                        sql.Identifier(name)
                    )
                ).fetchone()["populated"]:
                    raise RuntimeError(
                        "Existing data has no completed-import marker. A reviewed migration is required; no data was changed."
                    )
        else:
            conn.execute(schema_file.read_text(encoding="utf-8"))
        import_reference(conn, data_dir)
        import_timetable(conn, data_dir)
        conn.execute(
            sql.SQL("COMMENT ON TABLE train_runs IS {}").format(
                sql.Literal(INITIALIZED)
            )
        )
    logger.info("database initialized")
    return True


def main() -> None:
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    with get_connection() as conn:
        initialize(conn, config.DATA_DIR, config.SCHEMA_FILE)


if __name__ == "__main__":
    main()
