# Task 061 — Patch Summary

## Files Changed

- `yinyang_server.py`
- `web/dashboard.html`
- `web/js/dashboard.js`
- `web/css/dashboard.css`
- `tests/test_value_dashboard.py`

## Backend

- `yinyang_server.py:2394` adds Task 061 session-stat helpers for fresh session creation, ISO8601 `session_start` formatting, and snapshot normalization.
- `yinyang_server.py:15427` switches `GET /api/v1/session/stats` to the normalized snapshot helper.
- `yinyang_server.py:15433` switches `POST /api/v1/session/stats/reset` to a shared reset helper.
- `yinyang_server.py:15` updates the route table documentation for the two session-stat endpoints.

## Frontend

- `web/dashboard.html:8` keeps the 3-zone value rail and trims the stats grid to the requested 4 summary cards.
- `web/js/dashboard.js:1` rewrites the rail controller to accept `apiToken` and `metricsUrl`, poll every 5 seconds, rotate every 8 seconds, and prefer stats during active states.
- `web/js/dashboard.js:130` renders the full stats sentence, including evidence count.
- `web/css/dashboard.css:1` normalizes the dashboard styling around `--hub-*` tokens and on-scale spacing/font/radius values.

## Tests

- `tests/test_value_dashboard.py:58` replaces socket-based coverage with handler-probe tests suitable for the sandbox.
- `tests/test_value_dashboard.py:214` adds frontend spec checks for constructor signature, active-state gating, evidence text, and the 4-card layout.
