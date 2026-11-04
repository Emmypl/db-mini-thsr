-- Mini THSR schema for PostgreSQL 17.
-- Execute once on an empty database inside the importer's transaction.
-- This is initial DDL, not a migration for an existing users/stations database.
-- Do not add BEGIN/COMMIT here: db_init.py owns the transaction.

CREATE TABLE users (
    user_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL CHECK (btrim(name) <> ''),
    phone VARCHAR(20)
);

CREATE TABLE stations (
    station_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50) NOT NULL CHECK (btrim(name) <> ''),
    seq INTEGER NOT NULL UNIQUE CHECK (seq > 0)
);

-- Train numbers are text: leading zeros such as 0601 must survive import.
CREATE TABLE trains (
    train_no VARCHAR(20) PRIMARY KEY,
    direction CHAR(1) NOT NULL CHECK (direction IN ('S', 'N')),
    cars INTEGER NOT NULL CHECK (cars > 0)
);

CREATE TABLE train_operating_days (
    train_no VARCHAR(20) NOT NULL REFERENCES trains (train_no),
    weekday SMALLINT NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    PRIMARY KEY (train_no, weekday)
);

-- stop_seq follows travel direction, including on northbound trains.
CREATE TABLE train_stops (
    train_no VARCHAR(20) NOT NULL REFERENCES trains (train_no),
    stop_seq INTEGER NOT NULL CHECK (stop_seq > 0),
    station_id VARCHAR(10) NOT NULL REFERENCES stations (station_id),
    stop_time TIME WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (train_no, stop_seq),
    UNIQUE (train_no, station_id),
    CONSTRAINT train_stops_time_format CHECK (
        stop_time < TIME '24:00:00'
        AND EXTRACT(SECOND FROM stop_time) = 0
    )
);

CREATE TABLE seats (
    train_no VARCHAR(20) NOT NULL REFERENCES trains (train_no),
    car_no INTEGER NOT NULL CHECK (car_no > 0),
    row_no SMALLINT NOT NULL CHECK (row_no BETWEEN 1 AND 4),
    seat_letter CHAR(1) NOT NULL CHECK (seat_letter IN ('A', 'B', 'C', 'D', 'E')),
    PRIMARY KEY (train_no, car_no, row_no, seat_letter)
);

-- A stable row to lock before booking/cancelling on a particular train/date.
CREATE TABLE train_runs (
    train_no VARCHAR(20) NOT NULL REFERENCES trains (train_no),
    service_date DATE NOT NULL CHECK (
        service_date BETWEEN DATE '2026-12-01' AND DATE '2027-01-31'
    ),
    PRIMARY KEY (train_no, service_date)
);

CREATE TABLE bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(20) NOT NULL REFERENCES users (user_id),
    train_no VARCHAR(20) NOT NULL,
    service_date DATE NOT NULL,
    from_stop_seq INTEGER NOT NULL,
    to_stop_seq INTEGER NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('confirmed', 'cancelled')),
    preference VARCHAR(6) CHECK (preference IN ('window', 'aisle')),
    adjacent BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMPTZ,
    UNIQUE (booking_id, train_no),
    CONSTRAINT bookings_run_fk FOREIGN KEY (train_no, service_date)
        REFERENCES train_runs (train_no, service_date),
    CONSTRAINT bookings_departure_fk FOREIGN KEY (train_no, from_stop_seq)
        REFERENCES train_stops (train_no, stop_seq),
    CONSTRAINT bookings_arrival_fk FOREIGN KEY (train_no, to_stop_seq)
        REFERENCES train_stops (train_no, stop_seq),
    CONSTRAINT bookings_forward_segment CHECK (from_stop_seq < to_stop_seq),
    CONSTRAINT bookings_exclusive_options CHECK (NOT adjacent OR preference IS NULL),
    CONSTRAINT bookings_cancellation_state CHECK (
        (status = 'confirmed' AND cancelled_at IS NULL)
        OR (status = 'cancelled' AND cancelled_at IS NOT NULL)
    )
);

-- One row per assigned seat. Keep these rows when an order is cancelled.
-- train_no is intentionally repeated to enforce that the seat and booking
-- belong to the same train using the two composite foreign keys below.
CREATE TABLE tickets (
    booking_id UUID NOT NULL,
    train_no VARCHAR(20) NOT NULL,
    car_no INTEGER NOT NULL,
    row_no SMALLINT NOT NULL,
    seat_letter CHAR(1) NOT NULL,
    PRIMARY KEY (booking_id, car_no, row_no, seat_letter),
    CONSTRAINT tickets_booking_fk FOREIGN KEY (booking_id, train_no)
        REFERENCES bookings (booking_id, train_no),
    CONSTRAINT tickets_seat_fk FOREIGN KEY (train_no, car_no, row_no, seat_letter)
        REFERENCES seats (train_no, car_no, row_no, seat_letter)
);

CREATE INDEX bookings_user_history_idx
    ON bookings (user_id, created_at, booking_id);

CREATE INDEX bookings_confirmed_segment_idx
    ON bookings (train_no, service_date, from_stop_seq, to_stop_seq)
    WHERE status = 'confirmed';

CREATE INDEX train_stops_station_idx
    ON train_stops (station_id, train_no);

-- Rules to implement in the importer and backend, not enforced by this DDL:
-- * Generate seats only for car_no <= trains.cars.
-- * Generate runs only on the train's operating weekdays.
-- * Validate consecutive stop_seq and increasing times in travel direction.
-- * Enforce 1-5 tickets per order and quantity-specific preference/adjacency.
-- * Prevent overlapping confirmed tickets by locking train_runs FOR UPDATE,
--   then reading occupancy and inserting the entire order in one transaction.
-- * Cancellation uses the same run lock and verifies user_id after locking.
-- No global UNIQUE constraint on seat coordinates in tickets: the same seat
-- may be sold on adjacent journey intervals and on different dates.
