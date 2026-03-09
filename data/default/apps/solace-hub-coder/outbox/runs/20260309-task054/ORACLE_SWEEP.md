# ORACLE_SWEEP

Command:
```bash
pytest -q tests/test_oauth3_vault.py
pytest -q tests/test_oauth3_vault.py
pytest -q tests/test_oauth3_vault.py
```

Result:
```text
run 1
........                                                                 [100%]
8 passed in 5.84s
run 2
........                                                                 [100%]
8 passed in 5.82s
run 3
........                                                                 [100%]
8 passed in 5.88s
```

Broader regression:
```bash
pytest -q tests/test_yinyang_instructions.py tests/test_oauth3_vault.py
```

```text
339 passed in 7.21s
```
