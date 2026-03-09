Task 054 red gate note: the requested OAuth3 vault API was already implemented before this run, so there was no failing reproduction to capture without inventing one.

Pre-change verification command:

```text
$ pytest -q tests/test_oauth3_vault.py
........                                                                 [100%]
8 passed in 5.91s
```

Interpretation:
- Existing implementation already satisfies the requested focused vault behavior.
- No source patch was applied.
