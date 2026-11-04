\set ON_ERROR_STOP on
-- Run with psql. Everything, including the isolated schema, is rolled back.
BEGIN;
CREATE SCHEMA thsr_constraint_test;
SET LOCAL search_path TO thsr_constraint_test;
\ir ../schema/schema.sql

CREATE FUNCTION pg_temp.expect_rejection(statement TEXT, expected_state TEXT, label TEXT)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE actual_state TEXT;
BEGIN
    BEGIN
        EXECUTE statement;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS actual_state = RETURNED_SQLSTATE;
        IF actual_state = expected_state THEN
            RAISE NOTICE 'PASS: %', label;
            RETURN;
        END IF;
        RAISE EXCEPTION '%: expected SQLSTATE %, got %', label, expected_state, actual_state;
    END;
    RAISE EXCEPTION '%: invalid data was accepted', label;
END;
$$;

INSERT INTO users VALUES ('TEST-U1', 'Test Passenger', NULL);
INSERT INTO stations VALUES ('TEST-A', 'North', 1), ('TEST-B', 'Middle', 2), ('TEST-C', 'South', 3);
INSERT INTO trains VALUES ('TEST-0601', 'S', 1), ('TEST-0602', 'N', 1);
INSERT INTO train_operating_days VALUES ('TEST-0601', 1), ('TEST-0602', 1);
INSERT INTO train_stops VALUES
 ('TEST-0601', 1, 'TEST-A', '06:00'), ('TEST-0601', 2, 'TEST-B', '06:30'), ('TEST-0601', 3, 'TEST-C', '07:00'),
 ('TEST-0602', 1, 'TEST-C', '08:00'), ('TEST-0602', 2, 'TEST-A', '09:00');
INSERT INTO seats VALUES ('TEST-0601', 1, 1, 'A'), ('TEST-0602', 1, 1, 'A');
INSERT INTO train_runs VALUES ('TEST-0601', '2026-12-07'), ('TEST-0602', '2026-12-07');
INSERT INTO bookings (booking_id, user_id, train_no, service_date, from_stop_seq, to_stop_seq)
VALUES ('00000000-0000-0000-0000-000000000001', 'TEST-U1', 'TEST-0601', '2026-12-07', 1, 2);
INSERT INTO tickets VALUES ('00000000-0000-0000-0000-000000000001', 'TEST-0601', 1, 1, 'A');

SELECT pg_temp.expect_rejection($q$INSERT INTO users VALUES ('TEST-U1', 'Duplicate', NULL)$q$, '23505', 'duplicate user');
SELECT pg_temp.expect_rejection($q$INSERT INTO users VALUES ('TEST-U2', '   ', NULL)$q$, '23514', 'blank user name');
SELECT pg_temp.expect_rejection($q$INSERT INTO stations VALUES ('TEST-D', 'Other', 1)$q$, '23505', 'duplicate station sequence');
SELECT pg_temp.expect_rejection($q$INSERT INTO trains VALUES ('TEST-BAD', 'X', 1)$q$, '23514', 'invalid direction');
SELECT pg_temp.expect_rejection($q$INSERT INTO trains VALUES ('TEST-BAD', 'S', 0)$q$, '23514', 'zero cars');
SELECT pg_temp.expect_rejection($q$INSERT INTO train_operating_days VALUES ('TEST-0601', 8)$q$, '23514', 'invalid weekday');
SELECT pg_temp.expect_rejection($q$INSERT INTO train_stops VALUES ('TEST-0601', 4, 'MISSING', '07:30')$q$, '23503', 'unknown station');
SELECT pg_temp.expect_rejection($q$UPDATE train_stops SET stop_time = '24:00' WHERE train_no = 'TEST-0601' AND stop_seq = 1$q$, '23514', 'midnight overflow');
SELECT pg_temp.expect_rejection($q$UPDATE train_stops SET stop_time = '06:00:01' WHERE train_no = 'TEST-0601' AND stop_seq = 1$q$, '23514', 'seconds in timetable');
SELECT pg_temp.expect_rejection($q$INSERT INTO seats VALUES ('TEST-0601', 1, 5, 'A')$q$, '23514', 'row five');
SELECT pg_temp.expect_rejection($q$INSERT INTO seats VALUES ('TEST-0601', 1, 1, 'F')$q$, '23514', 'seat letter F');
SELECT pg_temp.expect_rejection($q$INSERT INTO train_runs VALUES ('TEST-0601', '2027-02-01')$q$, '23514', 'date outside operating period');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET user_id = 'MISSING'$q$, '23503', 'unknown booking user');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET service_date = '2026-12-08'$q$, '23503', 'nonexistent train run');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET to_stop_seq = 99$q$, '23503', 'nonexistent destination stop');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET to_stop_seq = from_stop_seq$q$, '23514', 'equal endpoints');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET from_stop_seq = 3$q$, '23514', 'reversed journey');
SELECT pg_temp.expect_rejection($q$UPDATE tickets SET train_no = 'TEST-0602'$q$, '23503', 'seat from another train');
SELECT pg_temp.expect_rejection($q$UPDATE tickets SET seat_letter = 'B'$q$, '23503', 'nonexistent seat');
SELECT pg_temp.expect_rejection($q$INSERT INTO tickets SELECT * FROM tickets$q$, '23505', 'same seat twice in an order');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET preference = 'middle'$q$, '23514', 'unsupported preference');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET preference = 'window', adjacent = true$q$, '23514', 'preference with adjacency');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET status = 'cancelled'$q$, '23514', 'cancellation without timestamp');
SELECT pg_temp.expect_rejection($q$UPDATE bookings SET cancelled_at = CURRENT_TIMESTAMP$q$, '23514', 'confirmed booking with cancellation timestamp');
SELECT pg_temp.expect_rejection($q$DELETE FROM users WHERE user_id = 'TEST-U1'$q$, '23503', 'deleting referenced user');

-- Adjoining journeys may reuse a physical seat. Cancellation retains history.
INSERT INTO bookings (booking_id, user_id, train_no, service_date, from_stop_seq, to_stop_seq)
VALUES ('00000000-0000-0000-0000-000000000002', 'TEST-U1', 'TEST-0601', '2026-12-07', 2, 3);
INSERT INTO tickets VALUES ('00000000-0000-0000-0000-000000000002', 'TEST-0601', 1, 1, 'A');
UPDATE bookings SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP
WHERE booking_id = '00000000-0000-0000-0000-000000000001';
DO $$
BEGIN
    IF (SELECT count(*) FROM tickets) <> 2
       OR (SELECT count(*) FROM bookings WHERE status = 'cancelled') <> 1 THEN
        RAISE EXCEPTION 'Cancellation did not preserve expected history';
    END IF;
    RAISE NOTICE 'PASS: valid fixtures, adjoining journeys, cancellation and retained history';
END;
$$;
ROLLBACK;
\echo All schema constraint checks passed; test schema and data were rolled back.
