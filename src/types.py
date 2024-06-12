

from dataclasses import dataclass
import datetime
from enum import Enum, auto
from typing import List, Optional


class EventType(str, Enum):
    ARRIVAL = "Arrival"
    DEPARTURE = "Departure"
    TRANSIT = "Transit"


@dataclass
class Event:
    train_no: int
    train_name: str
    time: datetime.time
    event_type: EventType
    source_station: Optional[str] = None # only for transit
    destination_station: Optional[str] = None  # only for transit
    distance: Optional[int] = None  # only for transit


@dataclass
class Station:
    station_code: str
    station_name: str
    events: List[Event]


@dataclass
class Train:
    train_no: int
    train_name: str
    events: List[Event]

