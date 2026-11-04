from app.core.database import get_connection
from app.repositories.station_repository import StationRepository
from app.responses.station import StationResponse


class StationService:
    def list_stations(self) -> list[StationResponse]:
        with get_connection() as conn:
            rows = StationRepository(conn).list_all()
        return [StationResponse(**row) for row in rows]
