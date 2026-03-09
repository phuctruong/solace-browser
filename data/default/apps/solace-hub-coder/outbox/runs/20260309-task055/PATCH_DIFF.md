# Task 055 Patch Diff

## Scope
- Verified the existing FDA Part 11 / ALCOA+ evidence bundle feature already exists in `evidence_bundle.py` and `yinyang_server.py`.
- Fixed the regression where `record_evidence(...)` still wrote Part 11 bundles to the default home path even when tests redirected the active evidence root.

## Files changed
- `yinyang_server.py`
- `tests/test_part11_evidence.py`

## Server fix
- Added default path sentinels in `yinyang_server.py:159` so the server can tell when Part 11 paths were explicitly overridden.
- Added `_part11_storage_paths()` in `yinyang_server.py:2601` to resolve append-only Part 11 storage under the active evidence root when `EVIDENCE_PATH` is redirected in tests.
- Updated chain-tip loading, bundle loading, and append-only writes in `yinyang_server.py:2613`, `yinyang_server.py:2625`, and `yinyang_server.py:2647` to use the resolved writable Part 11 paths.

## Regression proof
- Added `test_record_evidence_uses_active_evidence_root_for_part11_storage()` in `tests/test_part11_evidence.py:179`.
- The new test proves `record_evidence(...)` now creates `evidence/evidence.jsonl` and `evidence/chain.lock` next to a redirected `EVIDENCE_PATH` instead of failing on the default home directory.
