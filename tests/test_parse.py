import datetime

from src.parse import load_data, scheduled_datetime
from src.types import EventType


CSV_HEADER = (
    "Train No,Train Name,SEQ,Station Code,Station Name,Time,Distance,"
    "Source Station,Source Station Name,Destination Station,"
    "Destination Station Name,Type\n"
)


def write_timetable(tmp_path, rows):
    path = tmp_path / "timetable.csv"
    path.write_text(CSV_HEADER + "\n".join(rows) + "\n")
    return path


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
    assert events[0].source_station == "SAWANTWADI R"
    assert events[-1].event_type == EventType.ARRIVAL
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
    assert transit_to_rajula.distance == 141.0
    assert transit_to_mahuva.distance == 54.0
    assert scheduled_datetime(
        rajula_arrival, datetime.date(2026, 5, 1)
    ) == datetime.datetime(2026, 5, 2, 1, 53)
