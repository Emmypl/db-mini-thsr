CREATE TABLE users (
    user_id VARCHAR(20) PRIMARY KEY,
    name    VARCHAR(50) NOT NULL CHECK (btrim(name) <> ''),
    phone   VARCHAR(20)
);

-- TODO: add stations table --
CREATE TABLE stations (
    station_id VARCHAR(10) PRIMARY KEY,
    name       VARCHAR(50) NOT NULL,
    seq        INT NOT NULL UNIQUE
);

CREATE TABLE trains (
    train_no  VARCHAR(20) PRIMARY KEY,
    direction CHAR(1)     NOT NULL CHECK (direction IN ('S', 'N')),
    cars      INTEGER     NOT NULL CHECK (cars > 0)
);

CREATE TABLE train_operating_days (
    train_no VARCHAR(20) NOT NULL REFERENCES trains (train_no) ON DELETE CASCADE,
    weekday  SMALLINT    NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    PRIMARY KEY (train_no, weekday)
);

CREATE TABLE train_stops (
    train_no   VARCHAR(20) NOT NULL REFERENCES trains (train_no) ON DELETE CASCADE,
    stop_seq   INTEGER     NOT NULL CHECK (stop_seq >= 1),
    station_id VARCHAR(10) NOT NULL REFERENCES stations (station_id),
    stop_time  TIME        NOT NULL,
    PRIMARY KEY (train_no, stop_seq),
);

CREATE INDEX idx_train_stops_station ON train_stops (station_id);

CREATE TABLE train_runs (
    train_no     VARCHAR(20) NOT NULL REFERENCES trains (train_no) ON DELETE CASCADE,
    service_date DATE        NOT NULL,
    PRIMARY KEY (train_no, service_date)
);
CREATE INDEX idx_train_runs_date ON train_runs (service_date);

CREATE TABLE seats (
    train_no    VARCHAR(20) NOT NULL REFERENCES trains (train_no) ON DELETE CASCADE,
    car_no      INTEGER     NOT NULL CHECK (car_no >= 1),
    row_no      SMALLINT    NOT NULL CHECK (row_no BETWEEN 1 AND 4),
    seat_letter CHAR(1)     NOT NULL CHECK (seat_letter IN ('A', 'B', 'C', 'D', 'E')),
    PRIMARY KEY (train_no, car_no, row_no, seat_letter)
);

CREATE TABLE bookings (
    booking_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       VARCHAR(20) NOT NULL REFERENCES users (user_id),
    train_no      VARCHAR(20) NOT NULL,
    service_date  DATE        NOT NULL,
    from_stop_seq INTEGER     NOT NULL,
    to_stop_seq   INTEGER     NOT NULL,
    status        VARCHAR(10) NOT NULL DEFAULT 'confirmed'
                  CHECK (status IN ('confirmed', 'cancelled')),
    preference    VARCHAR(6)  CHECK (preference IN ('window', 'aisle')),
    adjacent      BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    cancelled_at  TIMESTAMPTZ,

    CHECK (from_stop_seq < to_stop_seq),
    CHECK (NOT (preference IS NOT NULL AND adjacent)),
    CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL)),

    UNIQUE (booking_id, train_no),
    FOREIGN KEY (train_no, service_date) REFERENCES train_runs (train_no, service_date),
    FOREIGN KEY (train_no, from_stop_seq) REFERENCES train_stops (train_no, stop_seq),
    FOREIGN KEY (train_no, to_stop_seq)   REFERENCES train_stops (train_no, stop_seq)
);
CREATE INDEX idx_bookings_user ON bookings (user_id, created_at DESC);
-- speeds up the overlap check: only active orders of one run are scanned
CREATE INDEX idx_bookings_active_run
    ON bookings (train_no, service_date, from_stop_seq, to_stop_seq)
    WHERE status = 'confirmed';

CREATE TABLE tickets (
    booking_id  UUID        NOT NULL,
    train_no    VARCHAR(20) NOT NULL,
    car_no      INTEGER     NOT NULL,
    row_no      SMALLINT    NOT NULL,
    seat_letter CHAR(1)     NOT NULL,
    PRIMARY KEY (booking_id, train_no, car_no, row_no, seat_letter),
    FOREIGN KEY (booking_id, train_no) REFERENCES bookings (booking_id, train_no) ON DELETE CASCADE,
    FOREIGN KEY (train_no, car_no, row_no, seat_letter)
        REFERENCES seats (train_no, car_no, row_no, seat_letter)
);
-- lets "which tickets use this seat?" (availability query) use an index
CREATE INDEX idx_tickets_seat ON tickets (train_no, car_no, row_no, seat_letter);
