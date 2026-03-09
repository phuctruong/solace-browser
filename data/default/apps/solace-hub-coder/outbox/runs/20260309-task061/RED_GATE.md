# Task 061 — RED Gate

## Command

```bash
python -m pytest tests/test_value_dashboard.py -q
```

## Result

```text
F..F......FF.F                                                           [100%]
5 failed, 9 passed in 0.42s
```

## Failure Summary

- `session_start` was returned as a float timestamp instead of ISO8601.
- Session reset did not produce an ISO8601 `session_start` on the next stats read.
- `ValueDashboard` did not accept `apiToken` and `metricsUrl` constructor arguments.
- The dashboard JS did not encode active-session state gating for stats-vs-delight behavior.
- `web/dashboard.html` rendered 6 summary cards instead of the requested 4.

## Representative Failure

```text
E       assert False
E        +  where False = isinstance(1710000000.0, str)
```
