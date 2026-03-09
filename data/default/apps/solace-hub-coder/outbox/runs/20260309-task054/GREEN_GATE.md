# GREEN_GATE

Command:
```bash
pytest -q tests/test_oauth3_vault.py
```

Result:
```text
........                                                                 [100%]
8 passed in 5.84s
```

Regression command:
```bash
pytest -q tests/test_yinyang_instructions.py tests/test_oauth3_vault.py
```

Regression result:
```text
339 passed in 7.21s
```
