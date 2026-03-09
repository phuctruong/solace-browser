# RED Gate

## Command
```bash
python -m pytest -q tests/test_part11_evidence.py tests/test_session_rules.py tests/test_solace_hub.py
```

## Failing proof before the fix
- Result: `2 failed, 194 passed in 3.02s`
- Failing tests:
  - `tests/test_session_rules.py::test_check_app_returns_status`
  - `tests/test_session_rules.py::test_session_check_records_evidence`

## Witness
- `PermissionError: [Errno 13] Permission denied: '/home/phuc/.solace/evidence/evidence.jsonl'`
- Root cause: Part 11 evidence persistence ignored the redirected `EVIDENCE_PATH` used by adjacent tests and still wrote to the default home directory.
