# Mini THSR schema

`schema.sql` is the initial PostgreSQL 17 schema derived from `../design/database-design.md`. It creates nine tables and three additional indexes. It contains no sample records and no destructive reset commands.

Run it only against a new empty database, inside a transaction owned by the initialization program. For a standalone check against a disposable PostgreSQL database:

```sh
psql "$TEST_DATABASE_URL" -X -v ON_ERROR_STOP=1 --single-transaction -f schema/schema.sql
```

This file is not a migration. An existing database with `users` or `stations` requires a separate migration; do not delete data merely to apply this file.

## Implementation boundary

The DDL enforces referential integrity, valid seat letters and rows, valid operating dates, forward journey intervals, consistent cancellation state and matching trains for bookings and seats. It also restricts timetable times to minute precision below 24:00.

The importer must still load CSV records, generate seats and train runs, and validate cross-table timetable rules. The backend must enforce ticket counts, preferences and adjacency, ownership, interval availability and concurrency. This schema alone does not prevent double booking.

The existing starter importer checks only whether `users` exists. It must be updated before integrating this schema into a previously initialized application. The starter backend still imports only users and stations; importing the timetable and generating seats and train runs are follow-up tasks.

## Validation status

Validated on PostgreSQL 17 on 4 November 2026 using tests/schema_constraints.sql: all nine tables and three additional indexes were created, 25 invalid operations were rejected with the expected SQLSTATE, and valid records, adjoining journeys and cancellation with retained history succeeded. The test transaction was rolled back. Booking API behavior and concurrency remain untested.
