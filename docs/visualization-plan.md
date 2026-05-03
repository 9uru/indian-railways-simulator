# Indian Railways Visualization Plan

## Goal

Build a living railway simulator with two first-class views:

- Train view: follow a selected train across India as the clock advances.
- Station view: watch a selected station with arrivals, departures, passengers,
  vendors, and station ambience.

## Current foundation

- Timetable parser builds trains, stations, and event streams.
- Station coordinates are imported from a GeoJSON source.
- `scripts/export_game_data.py` emits browser-ready JSON under
  `data/processed/`.
- `web/` contains the first static visualization prototype.

## Prototype scope

- Draw an India map approximation on canvas without external map services.
- Plot a selected train route from station coordinates.
- Animate train position between scheduled station events.
- Switch sounds between train movement and station ambience.
- Draw a station scene with passengers and vendor stalls.
- Show real station event lists from per-station JSON files.

## Next steps

- Replace the approximate outline with a proper map layer or local vector tiles.
- Improve train interpolation using distance and schedule gaps between stations.
- Add richer procedural audio: horn, rail clatter, crowd bed, announcements.
- Add station layouts with platforms, tracks, signage, and crowd density.
- Add search/ranking for all trains and stations instead of capped datalists.
- Add a timeline scrubber and “jump to next stop/event” controls.
- Decide how to package or cache the large generated data for deployment.
