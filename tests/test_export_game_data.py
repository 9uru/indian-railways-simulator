from datetime import time

import pandas as pd
import pytest

from scripts.export_game_data import (
    is_major_station,
    major_route_stations,
    route_station_codes,
    serialize_event,
    train_number_keys,
)
from src.parse import _remove_terminal_placeholders, _segment_distance
from src.types import Event, EventType


@pytest.mark.parametrize(
    ("train_no", "expected"),
    [
        ("12345", {"12345"}),
        ("00123", {"00123", "123"}),
        ("00000", {"00000", "0"}),
        (" 123 ", {"123", "00123"}),
    ],
)
def test_train_number_keys(train_no, expected):
    assert train_number_keys(train_no) == expected


@pytest.mark.parametrize(
    ("code", "station_payload", "expected"),
    [
        ("ABC", {"ABC": {"name": "Central JN"}}, True),
        ("ABC", {"ABC": {"name": "Central Junction"}}, True),
        ("ABC", {"ABC": {"name": "Central JN."}}, True),
        ("ABC", {"ABC": {"name": "Busy Station", "eventCount": 180}}, True),
        ("ABC", {"ABC": {"name": "Small Station", "eventCount": 179}}, False),
        ("XYZ", {"ABC": {"name": "Central JN"}}, False),
    ],
)
def test_is_major_station(code, station_payload, expected):
    assert is_major_station(code, station_payload) is expected


def test_major_route_stations_filters_terminals_and_limits_results():
    route = ["ORG", "A", "B", "C", "D", "DST"]
    station_payload = {
        "ORG": {"name": "Origin Junction"},
        "A": {"name": "Minor Stop"},
        "B": {"name": "North JN"},
        "C": {"name": "Central JN"},
        "D": {"name": "South Junction"},
        "DST": {"name": "Destination Junction"},
    }

    assert major_route_stations(route, station_payload, limit=2) == [
        {"code": "B", "name": "North JN", "routeIndex": 2},
        {"code": "C", "name": "Central JN", "routeIndex": 3},
    ]


def test_serialize_event_omits_train_level_and_unused_fields():
    event = Event(
        "123",
        "Source Name",
        time(10, 0),
        EventType.DEPARTURE,
        station_code="AAA",
        source_station_code="AAA",
        destination_station_code="BBB",
    )

    serialized = serialize_event(
        event,
        {},
        ["AAA", "BBB"],
        "Origin",
        "Destination",
        [{"code": "MID", "name": "Middle JN", "routeIndex": 1}],
    )

    assert serialized["trainName"] == "Source Name"
    assert "sourceTrainName" not in serialized
    assert "majorRouteStations" not in serialized


def test_route_station_codes_skips_transits_and_duplicate_stations():
    events = [
        Event("1", "Train", time(10, 0), EventType.DEPARTURE, " aaa "),
        Event("1", "Train", time(10, 1), EventType.TRANSIT, "BBB"),
        Event("1", "Train", time(10, 2), EventType.ARRIVAL, "bbb"),
        Event("1", "Train", time(10, 3), EventType.DEPARTURE, "AAA"),
        Event("1", "Train", time(10, 4), EventType.ARRIVAL, None),
    ]

    assert route_station_codes(events) == ["AAA", "BBB"]


@pytest.mark.parametrize(
    ("distance", "next_distance", "expected"),
    [(10, 25, 15.0), (25, 10, 0.0), (10, 10, 0.0)],
)
def test_segment_distance(distance, next_distance, expected):
    row = pd.Series({"Distance": distance})
    next_row = pd.Series({"Distance": next_distance})

    assert _segment_distance(row, next_row) == expected


def test_segment_distance_returns_none_without_next_row():
    assert _segment_distance(pd.Series({"Distance": 10}), None) is None


def test_remove_terminal_placeholders_keeps_real_terminal_events():
    rows = pd.DataFrame(
        [
            {"SEQ": 1, "Type": "Arrival", "Station Code": "ORG"},
            {"SEQ": 1, "Type": "Departure", "Station Code": "ORG"},
            {"SEQ": 2, "Type": "Arrival", "Station Code": "MID"},
            {"SEQ": 2, "Type": "Departure", "Station Code": "MID"},
            {"SEQ": 3, "Type": "Arrival", "Station Code": "DST"},
            {"SEQ": 3, "Type": "Departure", "Station Code": "DST"},
        ]
    )

    actual = _remove_terminal_placeholders(rows)

    assert actual[["SEQ", "Type", "Station Code"]].to_dict("records") == [
        {"SEQ": 1, "Type": "Departure", "Station Code": "ORG"},
        {"SEQ": 2, "Type": "Arrival", "Station Code": "MID"},
        {"SEQ": 2, "Type": "Departure", "Station Code": "MID"},
        {"SEQ": 3, "Type": "Arrival", "Station Code": "DST"},
    ]
    assert len(rows) == 6

