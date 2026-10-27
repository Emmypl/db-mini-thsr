"""Create tables and import CSV data if the database is not initialized."""

import csv
import logging

import psycopg
from psycopg import sql  # safely build SQL containing table and column names

from app.core import config  # path settings such as SCHEMA_FILE and DATA_DIR
from app.core.database import get_connection  # open a database connection

# Logger named "db_init", shown in each log line
logger = logging.getLogger("db_init")

# Tables to import, read in order from data/<table>.csv
# With foreign keys, referenced tables must come first (e.g. users before orders)
TABLES = ["users"]


def is_initialized(conn: psycopg.Connection) -> bool:
    """Check whether the database has already been initialized."""
    # An existing users table means initialization already succeeded;
    # to_regclass() returns NULL when the table does not exist
    row = conn.execute("SELECT to_regclass('users') IS NOT NULL AS ok").fetchone()
    return row["ok"]


def import_csv(conn: psycopg.Connection, table: str) -> None:
    """Import data/<table>.csv into the table with the same name."""
    path = config.DATA_DIR / f"{table}.csv"
    # utf-8-sig strips the BOM that Excel adds at the start of the file
    with path.open(encoding="utf-8-sig", newline="") as f:
        # The first row is the column names, and the rest are data.
        # Trim column names and values, and turn empty values into None (NULL).
        # Skip rows with no values, such as blank lines or ",," left by Excel
        reader = csv.reader(f)
        columns = [name.strip() for name in next(reader)]
        rows = [
            [value.strip() or None for value in row]
            for row in reader
            if any(value.strip() for value in row)
        ]

    # Build: INSERT INTO table (col1, col2, ...) VALUES (%s, %s, ...)
    # sql.Identifier quotes names, preventing SQL injection and keyword clashes
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),  # table name
        sql.SQL(", ").join(map(sql.Identifier, columns)),  # list of column names
        sql.SQL(", ").join(sql.Placeholder() * len(columns)),  # one %s per column
    )

    # A cursor runs SQL on the connection. We need one here because
    # executemany() (run the query once per row) only exists on cursors
    with conn.cursor() as cur:
        cur.executemany(query, rows)
    logger.info("import %s: %d rows", path.name, len(rows))


def main() -> None:
    # Configure log output (same format as in app/__init__.py)
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Open a database connection; it is closed automatically when leaving the block
    with get_connection() as conn:
        if is_initialized(conn):
            logger.info("database already initialized, skip")
            return

        # Start a transaction: if any step fails, all changes are rolled back,
        # so we never end up with tables created but data only half imported
        with conn.transaction():
            logger.info("run %s", config.SCHEMA_FILE.name)
            # Run schema.sql to create all tables
            conn.execute(config.SCHEMA_FILE.read_text(encoding="utf-8"))

            # Import each table's CSV in the order of TABLES
            for table in TABLES:
                import_csv(conn, table)

    logger.info("database initialized")


# Only call main() when executed directly with `python db_init.py`
if __name__ == "__main__":
    main()
