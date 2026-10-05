# load data from csv and convert to python objects
import datetime
import time
import warnings
from typing import Dict, List, Tuple

import pandas as pd
from prompt_toolkit import HTML, print_formatted_text
from src.types import Event, Station, Train
from src.types import EventType


def scheduled_datetime(
    event: Event, service_date: datetime.date, use_day_offset: bool = True
) -> datetime.datetime:
    day_offset = event.day_offset if use_day_offset else 0
    return datetime.datetime.combine(
        service_date + datetime.timedelta(days=day_offset), event.time
    )


def _remove_terminal_placeholders(train_info: pd.DataFrame) -> pd.DataFrame:
    first_seq = train_info["SEQ"].min()
    last_seq = train_info["SEQ"].max()
    terminal_placeholder = (
        (train_info["SEQ"] == first_seq) & (train_info["Type"] == "Arrival")
    ) | ((train_info["SEQ"] == last_seq) & (train_info["Type"] == "Departure"))
    return train_info.loc[~terminal_placeholder].copy()


def _segment_distance(row: pd.Series, next_row: pd.Series | None) -> float | None:
    if next_row is None:
        return None
    return max(0.0, float(next_row["Distance"]) - float(row["Distance"]))


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
        "Type": str,
    }

    df = pd.read_csv(filename, dtype=dtype, low_memory=False)
    missing_columns = [c for c in dtype if c not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Missing required CSV columns: {', '.join(missing_columns)}"
        )

    dropped_count = len(df) - df.dropna().shape[0]
    df = df.dropna()
    if dropped_count:
        warnings.warn(f"Dropped {dropped_count} row(s) with missing values")
    if df.empty:
        raise ValueError("No data rows remain after validation")

    # Parse the Time column outside the loop
    parsed_time = pd.to_datetime(
        df["Time"], format="%H:%M:%S", errors="coerce"
    )
    bad_time_count = int(parsed_time.isna().sum())
    if bad_time_count:
        warnings.warn(
            f"{bad_time_count} row(s) had unparseable Time values"
        )
    df["Time"] = parsed_time.dt.time

    # Initialize dictionaries
    trains_by_number: Dict[int, Train] = {}
    stations_by_code: Dict[str, Station] = {}

    # Group by 'Train No' to process each train separately
    grouped = df.groupby("Train No")

    for train_no, train_info in grouped:
        train_info = train_info.copy()
        train_info["Type_Rank"] = train_info["Type"].map({"Arrival": 0, "Departure": 1})
        train_info = train_info.sort_values(by=["SEQ", "Type_Rank"]).drop(
            columns=["Type_Rank"]
        )
        train_info = _remove_terminal_placeholders(train_info)
        if train_info.empty:
            continue

        train = Train(
            train_no=train_info.iloc[0]["Train No"],
            train_name=train_info.iloc[0]["Train Name"],
            events=[],
        )

        day_offset = 0
        previous_time = None
        for i in range(len(train_info)):
            row = train_info.iloc[i]
            prev_row = train_info.iloc[i - 1] if i > 0 else None
            next_row = train_info.iloc[i + 1] if i < len(train_info) - 1 else None
            if previous_time is not None and row["Time"] < previous_time:
                day_offset += 1
            previous_time = row["Time"]

            station_code = row["Station Code"]

            if station_code not in stations_by_code:
                stations_by_code[station_code] = Station(
                    station_code=station_code,
                    station_name=row["Station Name"],
                    events=[],
                )

            if row["Type"] == "Arrival":
                source_station = (
                    prev_row["Station Name"] if prev_row is not None else None
                )
                source_station_code = (
                    prev_row["Station Code"] if prev_row is not None else None
                )
                destination_station = row["Station Name"]
                destination_station_code = row["Station Code"]
            elif row["Type"] == "Departure":
                source_station = row["Station Name"]
                source_station_code = row["Station Code"]
                destination_station = (
                    next_row["Station Name"] if next_row is not None else None
                )
                destination_station_code = (
                    next_row["Station Code"] if next_row is not None else None
                )
            event = Event(
                train_no=row["Train No"],
                train_name=row["Train Name"],
                time=row["Time"],
                event_type=EventType(row["Type"]),
                station_code=row["Station Code"],
                source_station=source_station,
                source_station_code=source_station_code,
                destination_station=destination_station,
                destination_station_code=destination_station_code,
                distance=None,
                day_offset=day_offset,
            )

            train.events.append(event)
            stations_by_code[station_code].events.append(event)

            if (
                row["Station Name"] != row["Destination Station Name"]
                and row["Type"] == "Departure"
            ):
                transit_event = Event(
                    train_no=row["Train No"],
                    train_name=row["Train Name"],
                    time=row["Time"],
                    event_type=EventType.TRANSIT,
                    station_code=row["Station Code"],
                    source_station=row["Station Name"],
                    source_station_code=row["Station Code"],
                    destination_station=(
                        next_row["Station Name"] if next_row is not None else None
                    ),
                    destination_station_code=(
                        next_row["Station Code"] if next_row is not None else None
                    ),
                    distance=_segment_distance(row, next_row),
                    day_offset=day_offset,
                )
                train.events.append(transit_event)

        trains_by_number[int(train_no)] = train

    # Sort station events chronologically: day_offset first, then wall-clock time
    for station in stations_by_code.values():
        station.events = sorted(
            station.events, key=lambda x: (x.day_offset, x.time)
        )

    return trains_by_number, stations_by_code


def simulate_events(events: List[Event], cadence: float, use_day_offsets: bool = True):
    if not events:
        return

    service_date = datetime.date.today()
    # Self-sort by absolute scheduled datetime so simulation always starts at the
    # earliest event, regardless of the order the caller supplied.
    events = sorted(
        events, key=lambda e: scheduled_datetime(e, service_date, use_day_offsets)
    )
    simulated_time = scheduled_datetime(events[0], service_date, use_day_offsets)
    event_index = 0
    last_output_length = 0
    cadence_normal = cadence
    cadence_skip = 3 * cadence
    while event_index < len(events):
        output = f"<ansigreen>{simulated_time}:</ansigreen>"
        print(f"\r{' ' * last_output_length}\r", end="")  # Clear the previous line
        print_formatted_text(HTML(output), end=" ")
        last_output_length = len(output)

        current_event = events[event_index]
        event_time = scheduled_datetime(current_event, service_date, use_day_offsets)
        emitted_event = False
        while event_time <= simulated_time:
            print_formatted_text(HTML(f"{current_event}"))
            cadence = cadence_normal
            event_index += 1
            emitted_event = True
            if event_index >= len(events):
                break
            current_event = events[event_index]
            event_time = scheduled_datetime(
                current_event, service_date, use_day_offsets
            )
        if emitted_event:
            continue
        cadence = cadence_skip
        time.sleep(60.0 / cadence)
        simulated_time += datetime.timedelta(minutes=1)


def main():
    from src.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
