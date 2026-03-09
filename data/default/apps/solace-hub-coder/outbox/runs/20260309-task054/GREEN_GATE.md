Post-validation commands:

```text
$ pytest -q tests/test_oauth3_vault.py tests/test_oauth3_consent.py
..................                                                       [100%]
18 passed in 6.36s

$ pytest -q tests/test_oauth3_vault.py tests/test_oauth3_consent.py tests/test_yinyang_instructions.py
........................................................................ [ 20%]
........................................................................ [ 41%]
........................................................................ [ 61%]
........................................................................ [ 82%]
.............................................................            [100%]
349 passed in 7.85s
```

Outcome:
- OAuth3 vault routes validate successfully.
- Adjacent OAuth3 consent and server instruction coverage stay green.
