import datetime

import pytest

import src.cli as cli_module
import src.parse as parse_module
from src.parse import load_data, scheduled_datetime
from src.types import Event, EventType


CSV_HEADER = (
    "Train No,Train Name,SEQ,Station Code,Station Name,Time,Distance,"
    "Source Station,Source Station Name,Destination Station,"
    "Destination Station Name,Type\n"
)


def write_timetable(tmp_path, rows):
    path = tmp_path / "timetable.csv"
    path.write_text(CSV_HEADER + "\n".join(rows) + "\n")
    return path


@pytest.mark.parametrize(
    ("event_time", "day_offset", "use_day_offset", "expected"),
    [
        (
            datetime.time(23, 30),
            0,
            True,
            datetime.datetime(2026, 5, 1, 23, 30),
        ),
        (
            datetime.time(1, 15),
            1,
            True,
            datetime.datetime(2026, 5, 2, 1, 15),
        ),
        (
            datetime.time(1, 15),
            1,
            False,
            datetime.datetime(2026, 5, 1, 1, 15),
        ),
    ],
)
def test_scheduled_datetime(event_time, day_offset, use_day_offset, expected):
    event = Event(
        train_no="123",
        train_name="Test Train",
        time=event_time,
        event_type=EventType.ARRIVAL,
        day_offset=day_offset,
    )

    assert scheduled_datetime(
        event, datetime.date(2026, 5, 1), use_day_offset
    ) == expected


def fixed_service_date(monkeypatch):
    date_type = datetime.date

    class FixedDate(date_type):
        @classmethod
        def today(cls):
            return cls(2026, 5, 1)

    monkeypatch.setattr(parse_module.datetime, "date", FixedDate)


def test_simulate_events_sorts_out_of_order_events(monkeypatch):
    events = [
        Event("123", "Late", datetime.time(23, 30), EventType.ARRIVAL),
        Event(
            "123",
            "Early next day",
            datetime.time(1, 0),
            EventType.ARRIVAL,
            day_offset=1,
        ),
    ]
    fixed_service_date(monkeypatch)
    emitted = []
    monkeypatch.setattr(
        parse_module, "print", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        parse_module,
        "print_formatted_text",
        lambda value, **kwargs: emitted.append(str(value)),
    )
    monkeypatch.setattr(parse_module.time, "sleep", lambda seconds: None)

    parse_module.simulate_events(events, cadence=1)

    event_output = [line for line in emitted if "Train number" in line]
    assert "Late" in event_output[0]
    assert "Early next day" in event_output[1]


@pytest.mark.parametrize(
    ("use_day_offsets", "expected_day"),
    [(True, datetime.date(2026, 5, 2)), (False, datetime.date(2026, 5, 1))],
)
def test_simulate_events_respects_day_offset_flag(
    monkeypatch, use_day_offsets, expected_day
):
    event = Event(
        "123",
        "Overnight",
        datetime.time(1, 0),
        EventType.ARRIVAL,
        day_offset=1,
    )
    fixed_service_date(monkeypatch)
    clock_values = []
    monkeypatch.setattr(parse_module, "print", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(
        parse_module,
        "print_formatted_text",
        lambda value, **kwargs: clock_values.append(str(value)),
    )
    monkeypatch.setattr(parse_module.time, "sleep", lambda seconds: None)

    parse_module.simulate_events([event], cadence=1, use_day_offsets=use_day_offsets)

    assert any(str(expected_day) in value for value in clock_values)


def test_simulate_events_uses_skip_cadence_between_event_times(monkeypatch):
    events = [
        Event("123", "First", datetime.time(10, 0), EventType.ARRIVAL),
        Event("123", "Second", datetime.time(10, 2), EventType.ARRIVAL),
    ]
    fixed_service_date(monkeypatch)
    monkeypatch.setattr(
        parse_module, "print", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        parse_module, "print_formatted_text", lambda *args, **kwargs: None
    )
    sleeps = []
    monkeypatch.setattr(parse_module.time, "sleep", sleeps.append)

    parse_module.simulate_events(events, cadence=2)

    assert sleeps == [10.0, 10.0]


def test_parse_main_forwards_to_cli(monkeypatch):
    monkeypatch.setattr(cli_module, "load_data", lambda filename: ({}, {}))
    monkeypatch.setattr(cli_module, "prompt", lambda *args, **kwargs: "quit")

    parse_module.main()


def test_load_data_skips_terminal_placeholder_events(tmp_path):
    path = write_timetable(
        tmp_path,
        [
            "107,SWV-MAO,1,SWV,SAWANTWADI R,00:00:00,0,SWV,SAWANTWADI ROAD,MAO,MADGOAN JN.,Arrival",
            "107,SWV-MAO,1,SWV,SAWANTWADI R,10:25:00,0,SWV,SAWANTWADI ROAD,MAO,MADGOAN JN.,Departure",
            "107,SWV-MAO,2,THVM,THIVIM,11:06:00,32,SWV,SAWANTWADI ROAD,MAO,MADGOAN JN.,Arrival",
            "107,SWV-MAO,2,THVM,THIVIM,11:08:00,32,SWV,SAWANTWADI ROAD,MAO,MADGOAN JN.,Departure",
            "107,SWV-MAO,3,MAO,MADGOAN JN.,12:10:00,78,SWV,SAWANTWADI ROAD,MAO,MADGOAN JN.,Arrival",
            "107,SWV-MAO,3,MAO,MADGOAN JN.,00:00:00,78,SWV,SAWANTWADI ROAD,MAO,MADGOAN JN.,Departure",
        ],
    )

    trains, stations = load_data(str(path))

    events = trains[107].events
    assert events[0].event_type == EventType.DEPARTURE
    assert events[0].station_code == "SWV"
    assert events[0].source_station_code == "SWV"
    assert events[0].destination_station_code == "THVM"
    assert events[0].source_station == "SAWANTWADI R"
    assert events[-1].event_type == EventType.ARRIVAL
    assert events[-1].station_code == "MAO"
    assert events[-1].source_station_code == "THVM"
    assert events[-1].destination_station_code == "MAO"
    assert events[-1].destination_station == "MADGOAN JN."
    assert all(event.source_station is not None for event in events)
    assert all(event.destination_station is not None for event in events)
    assert [event.event_type for event in stations["SWV"].events] == [
        EventType.DEPARTURE
    ]
    assert [event.event_type for event in stations["MAO"].events] == [EventType.ARRIVAL]


def test_load_data_tracks_overnight_day_offsets_and_segment_distances(tmp_path):
    path = write_timetable(
        tmp_path,
        [
            "22989,BDTS MHV,1,BDTS,BANDRA,11:45:00,0,BDTS,BANDRA,MHV,MAHUVA,Arrival",
            "22989,BDTS MHV,1,BDTS,BANDRA,11:45:00,0,BDTS,BANDRA,MHV,MAHUVA,Departure",
            "22989,BDTS MHV,2,BTD,BOTAD,23:14:00,686,BDTS,BANDRA,MHV,MAHUVA,Arrival",
            "22989,BDTS MHV,2,BTD,BOTAD,23:16:00,686,BDTS,BANDRA,MHV,MAHUVA,Departure",
            "22989,BDTS MHV,3,RLA,RAJULA ROAD,01:53:00,827,BDTS,BANDRA,MHV,MAHUVA,Arrival",
            "22989,BDTS MHV,3,RLA,RAJULA ROAD,01:55:00,827,BDTS,BANDRA,MHV,MAHUVA,Departure",
            "22989,BDTS MHV,4,MHV,MAHUVA,03:20:00,881,BDTS,BANDRA,MHV,MAHUVA,Arrival",
            "22989,BDTS MHV,4,MHV,MAHUVA,03:20:00,881,BDTS,BANDRA,MHV,MAHUVA,Departure",
        ],
    )

    trains, _ = load_data(str(path))

    events = trains[22989].events
    rajula_arrival = next(
        event
        for event in events
        if event.event_type == EventType.ARRIVAL
        and event.destination_station == "RAJULA ROAD"
    )
    transit_to_rajula = next(
        event
        for event in events
        if event.event_type == EventType.TRANSIT
        and event.destination_station == "RAJULA ROAD"
    )
    transit_to_mahuva = next(
        event
        for event in events
        if event.event_type == EventType.TRANSIT
        and event.destination_station == "MAHUVA"
    )

    assert rajula_arrival.day_offset == 1
    assert rajula_arrival.station_code == "RLA"
    assert transit_to_rajula.distance == 141.0
    assert transit_to_rajula.source_station_code == "BTD"
    assert transit_to_rajula.destination_station_code == "RLA"
    assert transit_to_mahuva.distance == 54.0
    assert scheduled_datetime(
        rajula_arrival, datetime.date(2026, 5, 1)
    ) == datetime.datetime(2026, 5, 2, 1, 53)
