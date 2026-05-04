import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.parse import load_data
from src.types import Event, EventType


DEFAULT_TIMETABLE = Path("data/data_reorged.csv")
DEFAULT_COORDINATES = Path("data/external/india_railway_stations.geojson")
DEFAULT_TRAIN_NAMES = Path("data/external/indian_railway_train_names.json")
DEFAULT_OUTPUT_DIR = Path("data/processed")

COORDINATE_SOURCE = {
    "name": "Geo-referenced Indian Railways Data",
    "author": "Sankalp Sharma",
    "url": "https://gist.github.com/sankalpsharmaa/0c0587f3ae31277411960f70128d682f",
    "raw_url": "https://gist.githubusercontent.com/sankalpsharmaa/0c0587f3ae31277411960f70128d682f/raw/075361e1625bac0e8138dfbc68880c639d871e7b/india_railway_stations.geojson",
    "license": "No explicit license found in the gist preview; verify before redistribution.",
}

TRAIN_NAME_SOURCE = {
    "name": "Indian Railway Train Numbers & Names.json",
    "author": "jraavis",
    "url": "https://gist.github.com/jraavis/5274d998916131dd48e76879a1dc6076",
    "raw_url": "https://gist.githubusercontent.com/jraavis/5274d998916131dd48e76879a1dc6076/raw/Indian%20Railway%20Train%20Numbers%20%26%20Names.json",
    "license": "No explicit license found in the gist preview; verify before redistribution.",
}

JSON_SEPARATORS = (",", ":")


def load_coordinate_index(path: Path) -> dict[str, dict[str, Any]]:
    with path.open() as f:
        geojson = json.load(f)

    coordinates = {}
    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        code = str(properties.get("code", "")).strip().upper()
        if not code:
            continue

        geometry_coordinates = feature.get("geometry", {}).get("coordinates", [])
        lon = properties.get("long")
        lat = properties.get("lat")
        if (lat is None or lon is None) and len(geometry_coordinates) >= 2:
            lon, lat = geometry_coordinates[:2]

        coordinates[code] = {
            "code": code,
            "name": properties.get("name"),
            "lat": float(lat),
            "lon": float(lon),
            "state": properties.get("state"),
            "zone": properties.get("zone"),
            "address": properties.get("address"),
        }

    return coordinates


def train_number_keys(train_no: str) -> set[str]:
    normalized = str(train_no).strip()
    stripped = normalized.lstrip("0") or "0"
    return {normalized, stripped, stripped.zfill(5)}


def load_train_name_index(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}

    with path.open() as f:
        payload = json.load(f)

    train_names = {}
    for train in payload.get("trains", []):
        number = str(train.get("number", "")).strip()
        name = str(train.get("name", "")).strip()
        if not number or not name:
            continue
        for key in train_number_keys(number):
            train_names[key] = " ".join(name.split())
    return train_names


def display_train_name(train_no: str, fallback: str, train_names: dict[str, str]) -> str:
    for key in train_number_keys(train_no):
        if key in train_names:
            return train_names[key]
    return fallback


def station_display_name(code: str | None, stations: dict[str, Any]) -> str | None:
    if code is None:
        return None
    station = stations.get(str(code).strip().upper())
    return station.station_name if station else None


def is_major_station(code: str, station_payload: dict[str, Any]) -> bool:
    station = station_payload.get(code)
    if not station:
        return False
    name = str(station.get("name") or "").upper()
    return (
        " JN" in name
        or " JUNCTION" in name
        or name.endswith(" JN.")
        or station.get("eventCount", 0) >= 180
    )


def major_route_stations(
    route: list[str], station_payload: dict[str, Any], limit: int = 6
) -> list[dict[str, str]]:
    majors = [
        {"code": code, "name": station_payload[code]["name"], "routeIndex": index}
        for index, code in enumerate(route[1:-1], start=1)
        if code in station_payload and is_major_station(code, station_payload)
    ]
    return majors[:limit]


def serialize_event(
    event: Event,
    train_names: dict[str, str],
    route: list[str],
    route_origin: str | None,
    route_destination: str | None,
    major_stations: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "trainNo": event.train_no,
        "trainName": display_train_name(event.train_no, event.train_name, train_names),
        "sourceTrainName": event.train_name,
        "type": event.event_type.value,
        "time": event.time.isoformat(),
        "dayOffset": event.day_offset,
        "stationCode": event.station_code,
        "sourceStationCode": event.source_station_code,
        "sourceStation": event.source_station,
        "destinationStationCode": event.destination_station_code,
        "destinationStation": event.destination_station,
        "routeOriginCode": route[0] if route else event.source_station_code,
        "routeOrigin": route_origin,
        "routeDestinationCode": route[-1] if route else event.destination_station_code,
        "routeDestination": route_destination,
        "routeIndex": route.index(event.station_code)
        if event.station_code in route
        else None,
        "majorRouteStations": major_stations,
        "distanceKm": event.distance,
    }


def route_station_codes(events: list[Event]) -> list[str]:
    route = []
    seen = set()
    for event in events:
        if event.event_type == EventType.TRANSIT or event.station_code is None:
            continue
        code = event.station_code.strip().upper()
        if code not in seen:
            route.append(code)
            seen.add(code)
    return route


def export_game_data(
    timetable_path: Path,
    coordinate_path: Path,
    output_dir: Path,
    train_names_path: Path | None = DEFAULT_TRAIN_NAMES,
) -> dict[str, int]:
    trains, stations = load_data(str(timetable_path))
    coordinates = load_coordinate_index(coordinate_path)
    train_names = load_train_name_index(train_names_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    station_payload = {}
    missing_coordinates = []
    station_events_dir = output_dir / "station_events"
    station_events_dir.mkdir(parents=True, exist_ok=True)
    for code, station in sorted(stations.items()):
        normalized_code = code.strip().upper()
        coordinate = coordinates.get(normalized_code)
        if coordinate is None:
            missing_coordinates.append(
                {
                    "code": normalized_code,
                    "name": station.station_name,
                    "eventCount": len(station.events),
                }
            )
        station_payload[normalized_code] = {
            "code": normalized_code,
            "name": station.station_name,
            "lat": coordinate["lat"] if coordinate else None,
            "lon": coordinate["lon"] if coordinate else None,
            "state": coordinate["state"] if coordinate else None,
            "zone": coordinate["zone"] if coordinate else None,
            "address": coordinate["address"] if coordinate else None,
            "eventCount": len(station.events),
            "eventsPath": f"station_events/{normalized_code}.json",
        }

    train_summary_payload = {}
    train_events_dir = output_dir / "train_events"
    train_events_dir.mkdir(parents=True, exist_ok=True)
    serialized_train_events = {}

    for train_no, train in sorted(trains.items()):
        route = route_station_codes(train.events)
        route_origin = station_display_name(route[0] if route else None, stations)
        route_destination = station_display_name(route[-1] if route else None, stations)
        major_stations = major_route_stations(route, station_payload)
        events = [
            serialize_event(
                event,
                train_names,
                route,
                route_origin,
                route_destination,
                major_stations,
            )
            for event in train.events
        ]
        serialized_train_events[str(train_no)] = events
        train_events_path = train_events_dir / f"{train_no}.json"
        train_events_path.write_text(
            json.dumps(
                {
                    "trainNo": train.train_no,
                    "name": display_train_name(
                        train.train_no, train.train_name, train_names
                    ),
                    "sourceName": train.train_name,
                    "routeOrigin": route_origin,
                    "routeDestination": route_destination,
                    "majorRouteStations": major_stations,
                    "events": events,
                },
                separators=JSON_SEPARATORS,
            )
        )
        train_summary_payload[str(train_no)] = {
            "trainNo": train.train_no,
            "name": display_train_name(train.train_no, train.train_name, train_names),
            "sourceName": train.train_name,
            "route": route,
            "routeOrigin": route_origin,
            "routeDestination": route_destination,
            "majorRouteStations": major_stations,
            "mappedRoute": [
                code
                for code in route
                if station_payload.get(code, {}).get("lat") is not None
                and station_payload.get(code, {}).get("lon") is not None
            ],
            "eventCount": len(train.events),
            "eventsPath": f"train_events/{train_no}.json",
        }

    station_event_payload = {code: [] for code in stations}
    for events in serialized_train_events.values():
        for event in events:
            if event["stationCode"] in station_event_payload:
                station_event_payload[event["stationCode"]].append(event)
    for code, events in station_event_payload.items():
        events.sort(key=lambda event: (event["dayOffset"], event["time"], event["trainNo"]))
        (station_events_dir / f"{code.strip().upper()}.json").write_text(
            json.dumps(
                {
                    "code": code.strip().upper(),
                    "name": stations[code].station_name,
                    "events": events,
                },
                separators=JSON_SEPARATORS,
            )
        )

    metadata = {
        "timetableSource": str(timetable_path),
        "coordinateSource": COORDINATE_SOURCE,
        "trainNameSource": TRAIN_NAME_SOURCE if train_names else None,
        "trainNameCount": len(train_names),
        "stationCount": len(stations),
        "coordinateFeatureCount": len(coordinates),
        "matchedStationCount": len(stations) - len(missing_coordinates),
        "missingStationCount": len(missing_coordinates),
        "trainCount": len(trains),
    }

    (output_dir / "stations.json").write_text(
        json.dumps(
            {"metadata": metadata, "stations": station_payload},
            separators=JSON_SEPARATORS,
        )
    )
    (output_dir / "train_summaries.json").write_text(
        json.dumps(
            {"metadata": metadata, "trains": train_summary_payload},
            separators=JSON_SEPARATORS,
        )
    )
    (output_dir / "missing_station_coordinates.json").write_text(
        json.dumps(
            {"metadata": metadata, "missingStations": missing_coordinates},
            separators=JSON_SEPARATORS,
        )
    )
    (output_dir / "coordinate_source.json").write_text(
        json.dumps(COORDINATE_SOURCE, indent=2)
    )
    if train_names:
        (output_dir / "train_name_source.json").write_text(
            json.dumps(TRAIN_NAME_SOURCE, indent=2)
        )

    return {
        "station_count": len(stations),
        "coordinate_feature_count": len(coordinates),
        "matched_station_count": len(stations) - len(missing_coordinates),
        "missing_station_count": len(missing_coordinates),
        "train_count": len(trains),
        "train_name_count": len(train_names),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export map-ready Indian Railways game data."
    )
    parser.add_argument("--timetable", type=Path, default=DEFAULT_TIMETABLE)
    parser.add_argument("--coordinates", type=Path, default=DEFAULT_COORDINATES)
    parser.add_argument("--train-names", type=Path, default=DEFAULT_TRAIN_NAMES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = export_game_data(
        args.timetable,
        args.coordinates,
        args.output_dir,
        args.train_names,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
