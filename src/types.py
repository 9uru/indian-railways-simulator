

from dataclasses import dataclass
import datetime
from enum import Enum, auto
from typing import List, Optional


class EventType(str, Enum):
    ARRIVAL = "Arrival"
    DEPARTURE = "Departure"
    TRANSIT = "Transit"

    def __str__(self):
        if self.value == "Arrival":
            return "arriving"
        elif self.value == "Departure":
            return "departing"
        else:
            return "transiting"


@dataclass
class Event:
    train_no: int
    train_name: str
    time: datetime.time
    event_type: EventType
    source_station: Optional[str] = None # only for transit
    destination_station: Optional[str] = None  # only for transit
    distance: Optional[int] = None  # only for transit

    def __repr__(self):
        if self.event_type == EventType.ARRIVAL:
            return f"Train number: {self.train_no} {self.train_name} is {self.event_type} at {self.destination_station} at {self.time} from {self.source_station}"
        elif self.event_type == EventType.DEPARTURE:
            return f"Train number: {self.train_no} {self.train_name} is {self.event_type} at {self.time} to {self.destination_station} from {self.source_station}"
        else:
            return f"Train number: {self.train_no} {self.train_name} is {self.event_type} from {self.source_station} to {self.destination_station} covering {self.distance} kilometers."



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

