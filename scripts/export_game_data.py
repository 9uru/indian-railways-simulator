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
DEFAULT_OUTPUT_DIR = Path("data/processed")

COORDINATE_SOURCE = {
    "name": "Geo-referenced Indian Railways Data",
    "author": "Sankalp Sharma",
    "url": "https://gist.github.com/sankalpsharmaa/0c0587f3ae31277411960f70128d682f",
    "raw_url": "https://gist.githubusercontent.com/sankalpsharmaa/0c0587f3ae31277411960f70128d682f/raw/075361e1625bac0e8138dfbc68880c639d871e7b/india_railway_stations.geojson",
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


def serialize_event(event: Event) -> dict[str, Any]:
    return {
        "trainNo": event.train_no,
        "trainName": event.train_name,
        "type": event.event_type.value,
        "time": event.time.isoformat(),
        "dayOffset": event.day_offset,
        "stationCode": event.station_code,
        "sourceStationCode": event.source_station_code,
        "sourceStation": event.source_station,
        "destinationStationCode": event.destination_station_code,
        "destinationStation": event.destination_station,
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
    timetable_path: Path, coordinate_path: Path, output_dir: Path
) -> dict[str, int]:
    trains, stations = load_data(str(timetable_path))
    coordinates = load_coordinate_index(coordinate_path)
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
        (station_events_dir / f"{normalized_code}.json").write_text(
            json.dumps(
                {
                    "code": normalized_code,
                    "name": station.station_name,
                    "events": [serialize_event(event) for event in station.events],
                },
                separators=JSON_SEPARATORS,
            )
        )

    train_summary_payload = {}
    train_events_dir = output_dir / "train_events"
    train_events_dir.mkdir(parents=True, exist_ok=True)

    for train_no, train in sorted(trains.items()):
        route = route_station_codes(train.events)
        train_events_path = train_events_dir / f"{train_no}.json"
        train_events_path.write_text(
            json.dumps(
                {
                    "trainNo": train.train_no,
                    "name": train.train_name,
                    "events": [serialize_event(event) for event in train.events],
                },
                separators=JSON_SEPARATORS,
            )
        )
        train_summary_payload[str(train_no)] = {
            "trainNo": train.train_no,
            "name": train.train_name,
            "route": route,
            "mappedRoute": [
                code
                for code in route
                if station_payload.get(code, {}).get("lat") is not None
                and station_payload.get(code, {}).get("lon") is not None
            ],
            "eventCount": len(train.events),
            "eventsPath": f"train_events/{train_no}.json",
        }

    metadata = {
        "timetableSource": str(timetable_path),
        "coordinateSource": COORDINATE_SOURCE,
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

    return {
        "station_count": len(stations),
        "coordinate_feature_count": len(coordinates),
        "matched_station_count": len(stations) - len(missing_coordinates),
        "missing_station_count": len(missing_coordinates),
        "train_count": len(trains),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export map-ready Indian Railways game data."
    )
    parser.add_argument("--timetable", type=Path, default=DEFAULT_TIMETABLE)
    parser.add_argument("--coordinates", type=Path, default=DEFAULT_COORDINATES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = export_game_data(args.timetable, args.coordinates, args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
