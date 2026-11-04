# Database constraint checks

Run from the repository root against a test PostgreSQL 17 database:

```sh
psql "$TEST_DATABASE_URL" -X -f tests/schema_constraints.sql
```

The script creates an isolated schema inside a transaction, loads the current DDL, verifies valid records and 25 expected constraint rejections, and rolls everything back. It does not modify public tables. It exits on the first unexpected result. An existing schema named thsr_constraint_test causes a safe failure rather than deletion.

For the local test container, copy the SQL files to a fresh temporary directory in the container, preserving the tests/ and schema/ layout, and run psql with -f pointing to tests/schema_constraints.sql. The relative include loads schema/schema.sql.

Coverage includes foreign keys, seat coordinates, operating dates, timetable precision, journey order, matching trains, option compatibility and cancellation state. This is not a booking API or concurrency test. Ticket count, actual seat availability, operating weekdays and adjacency allocation still require importer/backend tests.

## CSV import integration tests

With backend dependencies installed, set TEST_DATABASE_URL to a disposable PostgreSQL 17 database and run from the repository root:

```sh
python -m unittest discover -s tests -p test_import.py -v
```

Each test creates a uniquely named schema and removes only that schema afterwards. Coverage includes public CSVs, custom station IDs and reordered headers, northbound stop order, leading zeros, weekday and weekend dates, seat generation, empty precreated schemas, rollback and retry after malformed inputs, preservation of orders on restart, safe rejection of legacy data and simultaneous initializers. The connection needs permission to create schemas. Without TEST_DATABASE_URL these integration tests are skipped, not passed.

## Station API tests

With TEST_DATABASE_URL set as above, run all Python integration tests:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
```

The station tests call the real Flask route, service and SQL repository against an isolated PostgreSQL schema. They verify HTTP 200, JSON fields, empty results, custom station IDs, Unicode names, north-to-south sorting and fresh reads without login. They do not exercise Nginx or browser rendering.

## Schedule API tests

`test_schedules.py` adds eight integration tests for response fields and sorting, both directions and skipped stops, dates without runs, inclusive time bounds at the requested station, parameter errors, overlapping versus adjoining intervals, sold-out trains and whole-journey availability, and exclusion of cancelled or unrelated bookings. Use the all-tests command above, or select `-p test_schedules.py` to run only these cases. The suite uses test ticket records directly; booking creation/concurrency is not tested by these cases.
