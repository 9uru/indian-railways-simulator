# load data from csv and convert to python objects
import datetime
import time
from typing import Dict, List, Tuple
import pandas as pd
from src.types import Event, Station, Train
from src.types import EventType

def load_data(filename: str) -> Tuple[Dict[int, Train], Dict[str, Station]]:
    """
    Load data from csv file into object types
    """
    dtype = {
        "Train No": str,
        "Train Name": str,
        "SEQ": int,
        "Station Code": str,
        "Station Name": str,
        "Time": str,
        "Distance": float,
        "Source Station": str,
        "Source Station Name": str,
        "Destination Station": str,
        "Destination Station Name": str,
        "Type": str
    }

    df = pd.read_csv(filename, dtype=dtype, low_memory=False)
    df = df.dropna()
    trains_by_number = {}
    stations_by_code = {}
    unique_trains = pd.unique(df["Train No"])

    for train_no in unique_trains:
        train_info = df[df["Train No"] == train_no]
        train_info = train_info.sort_values("SEQ", ascending=True)
        train = None  # Initialize train variable here

        for i in range(len(train_info)):
            row = train_info.iloc[i]
            prev_row = train_info.iloc[i - 1] if i > 0 else None
            next_row = train_info.iloc[i + 1] if i < len(train_info) - 1 else None

            station_code = row["Station Code"]
            station = stations_by_code.get(station_code, Station(
                station_code=station_code,
                station_name=row["Station Name"],
                events=[],
            ))

            if i == 0:
                train = Train(
                    train_no=row["Train No"],
                    train_name=row["Train Name"],
                    events=[],
                )

            event = Event(
                train_no=row["Train No"],
                train_name=row["Train Name"],
                time=datetime.datetime.strptime(row["Time"], "%H:%M:%S").time(),
                event_type=EventType(row["Type"]),
                source_station=prev_row["Station Name"] if prev_row is not None and row["Type"] == "Arrival" else None,
                destination_station=next_row["Station Name"] if row["Type"] == "Departure" and next_row is not None else None,
                distance=None,
            )
            train.events.append(event)
            station.events.append(event)
            stations_by_code[station_code] = station

            if row["Station Name"] != row["Destination Station Name"] and row["Type"] == "Departure":
                # Add transit
                event = Event(
                    train_no=row["Train No"],
                    train_name=row["Train Name"],
                    time=datetime.datetime.strptime(row["Time"], "%H:%M:%S").time(),
                    event_type=EventType.TRANSIT,
                    source_station=row["Station Name"],
                    destination_station=next_row["Station Name"] if next_row is not None else None,
                    distance=row["Distance"],
                )
                train.events.append(event)

        trains_by_number[row["Train No"]] = train

    # Sort events of stations by time
    for _, station in stations_by_code.items():
        station.events = sorted(station.events, key=lambda x: x.time)

    return trains_by_number, stations_by_code

if __name__ == "__main__":
    start = time.perf_counter()
    trains_by_number, stations_by_code = load_data("data/data_reorged.csv")
    end = time.perf_counter()
    print(f"Elapsed time: {end - start}")
    print(f"Events of Train Number: {"22989"}")
    print(trains_by_number["22989"].events)
    print(stations_by_code["BLR"].events)