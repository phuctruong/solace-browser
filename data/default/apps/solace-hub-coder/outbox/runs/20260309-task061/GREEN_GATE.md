# Task 061 — GREEN Gate

## Focused Command

```bash
python -m pytest tests/test_value_dashboard.py -q
```

## Focused Result

```text
..............                                                           [100%]
14 passed in 0.20s
```

## Additional Validation

```bash
python -m py_compile yinyang_server.py
```

```text
exit code: 0
```

## Verified

- `/api/v1/session/stats` returns ISO8601 `session_start` values and recomputed durations.
- `/api/v1/session/stats/reset` clears counters and starts a fresh session cleanly.
- The top-rail dashboard uses passive 8-second rotation with active-state stats preference.
- The center stats rail includes pages, LLM calls, cost, savings, duration, replays, and evidence.
- The HTML now renders 4 summary cards and keeps all frontend assets local-only.
