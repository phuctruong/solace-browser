# Oracle Sweep

## Determinism sweep
```bash
pytest -q tests/test_domain_detection.py
pytest -q tests/test_domain_detection.py
pytest -q tests/test_domain_detection.py
```

## Results
- Run 1: `8 passed in 0.66s`
- Run 2: `8 passed in 0.64s`
- Run 3: `8 passed in 0.62s`

## Notes
- Domain discovery stays deterministic across repeated runs.
- Free-tier sync denial stays stable and always returns the upgrade URL.
- Custom app scaffolding stays deterministic in the isolated temp repo fixture.
