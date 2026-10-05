# Bonsai-Friendly Code Improvement Queue

## Purpose and execution constraints

This queue breaks repository improvements into bounded tasks suitable for Bonsai 27B ternary quantization. Prefer one or two files per task, a small diff (roughly under 80 changed lines), explicit expected behavior, and deterministic verification. Avoid architecture changes and event-loop/timing changes unless a task explicitly requires them. For each task group: use a feature branch, run the relevant tests, request the advisor `final-check`, and push to `main` only when the advisor says **On track**. Do not bypass the gate if the advisor is unavailable.

## Tier 1 — small, bounded improvements

| ID | Task | Scope | Verification |
|---|---|---|---|
| T1.1 | Sort station events by `(day_offset, time)`; make `simulate_events` sort its local input by `scheduled_datetime` before simulation. | `src/parse.py` | Tests with overnight events and deliberately unsorted simulation input; verify real station lists are sorted. |
| T1.2 | Validate required CSV columns; warn when rows with missing values are dropped and when `Time` values cannot be parsed; fail clearly if no usable rows remain. | `src/parse.py` | Small CSV fixtures for missing columns, missing values, invalid times, and empty post-validation data. |
| T1.3 | Add focused tests for `scheduled_datetime`, including day offsets and `use_day_offsets` behavior. | `tests/test_parse.py` | `pytest` with fixed dates/times and expected datetimes. |
| T1.4 | Add tests for parsing helpers: `_segment_distance`, `_remove_terminal_placeholders`, `route_station_codes`, `major_route_stations`, `is_major_station`, and `train_number_keys`. | `tests/` | Table-driven/unit tests with boundary and representative cases. |
| T1.5 | Handle failures from the initial data fetch and train/station selection fetches with visible, recoverable UI feedback. | `web/app.js` | Local HTTP smoke test for success and failed requests; verify no unhandled rejection. |
| T1.6 | Replace data-derived `innerHTML` insertion with safe text/DOM APIs at the identified sites. | `web/app.js` | Static review plus browser smoke test using strings containing HTML-like characters. |

## Tier 2 — bounded but higher-risk changes

| ID | Task | Scope | Verification / risk |
|---|---|---|---|
| T2.1 | Remove the unused `sourceTrainName` field from serialized events. | `scripts/export_game_data.py` and generated export consumers as needed | Regenerate export; search all consumers; compare output size and smoke-test the web app. |
| T2.2 | Avoid repeating `majorRouteStations` on every event by storing/reading it at train level in `majorRoutePhrase`. | Exporter and `web/app.js` | Contract-changing: regenerate data, check schema consumers, and run a local web smoke test. |
| T2.3 | Extract command-line handling from `src/parse.py` into `src/cli.py` without changing CLI behavior. | `src/parse.py`, `src/cli.py` | Compare help/output and run the existing tests. |
| T2.4 | Parametrize `simulate_events` tests for ordering, day offsets, and cadence behavior. | `tests/` | Deterministic tests; no timing/event-loop refactor. |

## Task groups and status

| Group | Included tasks | Status |
|---|---|---|
| WT-1 — Python data layer | T1.1, T1.2 | **Implemented and locally verified** on branch `wt1-python-data-layer`, commit `e8ef23bb`. Push remains subject to advisor final-check approval. |
| WT-2 — parser tests | T1.3, T1.4 | Not started. |
| WT-3 — web hardening | T1.5, T1.6 | Not started. |
| WT-4 — export size | T2.1, T2.2 | Not started; T2.2 changes the export contract and requires a local web smoke test. |
| WT-5 — CLI and simulation tests | T2.3, T2.4 | Not started. |

## WT-1 evidence recorded at planning time

- Existing suite: `./venv/bin/python -m pytest -q` → 2 passed.
- Full timetable: 11,112 trains and 8,147 stations loaded; 0/8,147 station event lists out of `(day_offset, time)` order.
- Real CSV validation reports 10 rows with missing values.
- A reversed event sample confirmed `simulate_events` sorts its local input to begin with the earliest scheduled event.
