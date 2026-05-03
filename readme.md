# Indian Railways Simulator

This is a fun project rooted in a passion for the complex chaotic beauty that is India Railways.

1. Reads the timetable data
2. Clock based events with controllable clock speed
3. Generate Station Views - watch trains arrive and leave your station
4. Generates train views - follow along the train journey as you visit stations in your route


Thanks to @itzmeanjan for the timetable data.

## Run

```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m src.parse
```

## Web Visualization

Export the map-ready data, then serve the repo root and open the web app:

```bash
./venv/bin/python scripts/export_game_data.py
./venv/bin/python -m http.server 8000
```

Then visit http://127.0.0.1:8000/web/.

## Attributions

- Timetable data: @itzmeanjan.
- Station coordinates: Sankalp Sharma's "Geo-referenced Indian Railways Data" gist, documented in `data/external/README.md`.
- Station announcement reference: [R-o-n-a-k/Railway](https://github.com/R-o-n-a-k/Railway), used as inspiration for fragment-based railway PA announcements.
- Bilingual PA reference: [Cosmos-Ved09/RailVaani-Murf-ai](https://github.com/Cosmos-Ved09/RailVaani-Murf-ai), used as inspiration for English/Hindi-style announcement structure.
- Station ambience: `arunangshubanerjee-indian-railway-station-ambience-crowd-chatter-and-train-arrival-331012.mp3`, provided locally by the project owner and stored as `web/assets/station-ambience.mp3`.

## Commands

- `list trains`
- `next`
- `prev`
- `show train <train number>`
- `list stations`
- `show station <station code>`
- `exit`

## Test

```bash
./venv/bin/python -m pytest
```
