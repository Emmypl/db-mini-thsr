from dataclasses import dataclass


@dataclass
class StationResponse:
    station_id: str
    name: str
