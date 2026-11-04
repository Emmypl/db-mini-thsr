from datetime import date, time

import psycopg


class ScheduleRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def stations_exist(self, origin: str, destination: str) -> bool:
        row = self.conn.execute(
            "SELECT count(*) AS count FROM stations WHERE station_id IN (%s, %s)",
            (origin, destination),
        ).fetchone()
        return row["count"] == 2

    def search(
        self,
        day: date,
        origin: str,
        destination: str,
        earliest: time | None,
        latest: time | None,
    ) -> list[dict]:
        # Count seats free for the WHOLE journey, not minimum capacity per segment.
        # NOT EXISTS counts each physical seat once even if it has several tickets.
        return self.conn.execute(
            """
            SELECT r.train_no, r.service_date,
                   departure.stop_time AS departure_time,
                   arrival.stop_time AS arrival_time,
                   (
                       SELECT count(*) FROM seats s
                       WHERE s.train_no = r.train_no
                         AND NOT EXISTS (
                             SELECT 1 FROM bookings b
                             JOIN tickets t ON t.booking_id = b.booking_id
                                           AND t.train_no = b.train_no
                             WHERE b.train_no = r.train_no
                               AND b.service_date = r.service_date
                               AND b.status = 'confirmed'
                               AND t.car_no = s.car_no
                               AND t.row_no = s.row_no
                               AND t.seat_letter = s.seat_letter
                               AND b.from_stop_seq < arrival.stop_seq
                               AND departure.stop_seq < b.to_stop_seq
                         )
                   ) AS remain_seats
            FROM train_runs r
            JOIN train_stops departure ON departure.train_no = r.train_no
            JOIN train_stops arrival ON arrival.train_no = r.train_no
            WHERE r.service_date = %s
              AND departure.station_id = %s
              AND arrival.station_id = %s
              AND departure.stop_seq < arrival.stop_seq
              AND (%s::time IS NULL OR departure.stop_time >= %s::time)
              AND (%s::time IS NULL OR departure.stop_time <= %s::time)
            ORDER BY departure.stop_time, r.train_no
            """,
            (day, origin, destination, earliest, earliest, latest, latest),
        ).fetchall()
