Command: python -m pytest tests/test_fun_packs.py -q
Exit code: 0

```text
............                                                             [100%]
12 passed in 0.18s
```

Command: python -m py_compile yinyang_server.py tests/test_fun_packs.py
Exit code: 0

Note: the route tests use an in-memory `YinyangHandler` harness rather than a bound localhost socket because this sandbox rejects test socket binds on port `18888` with `PermissionError`.
