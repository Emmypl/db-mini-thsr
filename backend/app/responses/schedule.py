from dataclasses import dataclass


@dataclass
class ScheduleResponse:
    train_no: str
    date: str
    departure_time: str
    arrival_time: str
    remain_seats: int
