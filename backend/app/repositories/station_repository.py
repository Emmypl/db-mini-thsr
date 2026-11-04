from typing import Any

import psycopg


class StationRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def list_all(self) -> list[dict[str, Any]]:
        return self.conn.execute(
            "SELECT station_id, name FROM stations ORDER BY seq"
        ).fetchall()
