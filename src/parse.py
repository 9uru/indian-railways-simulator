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

    df = pd.read_csv(filename, dtype=dtype, low_memory=False).dropna()

    # Parse the Time column outside the loop
    df["Time"] = pd.to_datetime(df["Time"], format="%H:%M:%S").dt.time

    # Initialize dictionaries
    trains_by_number: Dict[int, Train] = {}
    stations_by_code: Dict[str, Station] = {}

    # Group by 'Train No' to process each train separately
    grouped = df.groupby("Train No")

    for train_no, train_info in grouped:
        train_info["Type_Rank"] = train_info["Type"].map({"Arrival": 0, "Departure": 1})
        train_info = train_info.sort_values(by=["SEQ", "Type_Rank"]).drop(columns=["Type_Rank"])
        if train_no == "22989":
            print(train_info)

        train = Train(
            train_no=train_info.iloc[0]["Train No"],
            train_name=train_info.iloc[0]["Train Name"],
            events=[]
        )

        for i in range(len(train_info)):
            row = train_info.iloc[i]
            prev_row = train_info.iloc[i - 1] if i > 0 else None
            next_row = train_info.iloc[i + 1] if i < len(train_info) - 1 else None

            station_code = row["Station Code"]

            if station_code not in stations_by_code:
                stations_by_code[station_code] = Station(
                    station_code=station_code,
                    station_name=row["Station Name"],
                    events=[]
                )

            if row["Type"] == "Arrival":
                source_station = prev_row["Station Name"] if prev_row is not None else None
                destination_station = row["Station Name"]
            elif row["Type"] == "Departure":
                source_station = row["Station Name"]
                destination_station = next_row["Station Name"] if next_row is not None else None
            event = Event(
                train_no=row["Train No"],
                train_name=row["Train Name"],
                time=row["Time"],
                event_type=EventType(row["Type"]),
                source_station=source_station,
                destination_station=destination_station,
                distance=None,
            )

            train.events.append(event)
            stations_by_code[station_code].events.append(event)

            if row["Station Name"] != row["Destination Station Name"] and row["Type"] == "Departure":
                transit_event = Event(
                    train_no=row["Train No"],
                    train_name=row["Train Name"],
                    time=row["Time"],
                    event_type=EventType.TRANSIT,
                    source_station=row["Station Name"],
                    destination_station=next_row["Station Name"] if next_row is not None else None,
                    distance=next_row["Distance"] if next_row is not None else None,
                )
                train.events.append(transit_event)

        trains_by_number[int(train_no)] = train

    # Sort events of stations by time
    for station in stations_by_code.values():
        station.events = sorted(station.events, key=lambda x: x.time)

    return trains_by_number, stations_by_code

if __name__ == "__main__":
    start = time.perf_counter()
    trains_by_number, stations_by_code = load_data("data/data_reorged.csv")
    stop = time.perf_counter()
    print(f"Time taken to load data: {stop - start:.3f} seconds")
    print("*" * 100)
    print(f"Events of Train Number: {22989}")
    print("*" * 100)
    for event in trains_by_number[22989].events:
        print(event)
    print("*" * 100)
    print("*" * 100)
    print("Events of BLR station")
    for event in stations_by_code["BLR"].events:
        print(event)
    print("*" * 100)