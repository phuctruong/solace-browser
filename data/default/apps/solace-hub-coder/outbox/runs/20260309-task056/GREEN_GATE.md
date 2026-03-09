# GREEN Gate

- NORTHSTAR metric advanced: Evidence by Default
- Targeted command: `pytest -q tests/test_prime_wiki_snapshots.py`
- Broader command: `pytest -q tests/test_prime_wiki_snapshots.py tests/test_prime_wiki_ui.py`

```text
$ pytest -q tests/test_prime_wiki_snapshots.py
.........                                                                [100%]
9 passed in 3.39s

$ pytest -q tests/test_prime_wiki_snapshots.py tests/test_prime_wiki_ui.py
...................                                                      [100%]
19 passed in 3.91s
```
