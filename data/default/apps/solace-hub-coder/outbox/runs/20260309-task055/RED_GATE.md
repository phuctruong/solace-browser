# RED Gate

## Command
```bash
pytest -q tests/test_part11_evidence.py
```

## Baseline setup
- Executed in a clean pre-patch checkout created from `git archive HEAD` under `/tmp/task055-red-1680750`.

## Expected failing proof before the patch
- Test collection failed because `evidence_bundle.py` did not exist in the baseline checkout.
- The failure was `ModuleNotFoundError: No module named 'evidence_bundle'`.
- This proved Task 055 was missing before the patch rather than silently passing.

## Witness
- `1 error in 0.15s`
