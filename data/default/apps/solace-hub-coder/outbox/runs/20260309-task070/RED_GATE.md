# Task 070 — RED Gate

## Command

```bash
pytest -q tests/test_evidence_viewer.py
```

## Result

```text
FFFFFFFFFF                                                               [100%]
10 failed in 0.83s
```

## Failure Summary

- `web/evidence-viewer.html` did not exist
- Static assertions failed because the page file was missing
- `GET /web/evidence-viewer.html` returned `404`

## Representative Failure

```text
E       AssertionError: assert False
E        +  where False = exists()
E        +    where exists = (PosixPath('/home/phuc/projects/solace-browser') / 'web/evidence-viewer.html').exists
```
