import re
from datetime import date, time

from app.core.database import get_connection
from app.repositories.schedule_repository import ScheduleRepository
from app.responses.schedule import ScheduleResponse


class ScheduleService:
    def search(self, params) -> list[ScheduleResponse]:
        raw_date = params.get("date", "")
        origin = params.get("from_station_id", "")
        destination = params.get("to_station_id", "")
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw_date):
            raise ValueError("date must use YYYY-MM-DD")
        day = date.fromisoformat(raw_date)
        if not origin or not destination or origin == destination:
            raise ValueError("Two different station IDs are required")
        bounds = []
        for key in ("departure_time_from", "departure_time_to"):
            value = params.get(key)
            if value is None:
                bounds.append(None)
            elif re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
                bounds.append(time.fromisoformat(value))
            else:
                raise ValueError(f"{key} must use HH:MM")
        earliest, latest = bounds
        if earliest is not None and latest is not None and earliest > latest:
            raise ValueError(
                "Earliest departure must not be later than latest departure"
            )
        with get_connection() as conn:
            repository = ScheduleRepository(conn)
            if not repository.stations_exist(origin, destination):
                raise ValueError("Unknown station ID")
            rows = repository.search(day, origin, destination, earliest, latest)
        return [
            ScheduleResponse(
                train_no=row["train_no"],
                date=row["service_date"].isoformat(),
                departure_time=row["departure_time"].strftime("%H:%M"),
                arrival_time=row["arrival_time"].strftime("%H:%M"),
                remain_seats=row["remain_seats"],
            )
            for row in rows
        ]
