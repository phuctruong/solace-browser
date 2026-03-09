# Oracle Sweep

## Determinism sweep
```bash
pytest -q tests/test_part11_evidence.py
pytest -q tests/test_part11_evidence.py
pytest -q tests/test_part11_evidence.py
```

## Results
- Run 1: `8 passed in 0.14s`
- Run 2: `8 passed in 0.15s`
- Run 3: `8 passed in 0.14s`

## Notes
- Bundle generation stays deterministic for compliance outcomes while preserving unique IDs and timestamps.
- SHA-256 chain verification stays stable across repeated runs.
- Append-only evidence storage and compliance reporting remain repeatable in isolated temp-path fixtures.
