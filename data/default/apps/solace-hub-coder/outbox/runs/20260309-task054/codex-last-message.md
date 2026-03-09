**Done**
- Added an AES-256-GCM OAuth3 vault at `yinyang_server.py:128` with PBKDF2-HMAC-SHA256 key derivation and hash-chained vault evidence persisted in `~/.solace/oauth3-vault.enc`.
- Implemented the new routes in `yinyang_server.py:4437`, `yinyang_server.py:4497`, `yinyang_server.py:4541`, `yinyang_server.py:4570`, `yinyang_server.py:4622`, and updated token listing in `yinyang_server.py:4647`.
- Declared the crypto dependency in `requirements.txt:2`.

**Tests**
- Added focused coverage in `tests/test_oauth3_vault.py:80`.
- Updated legacy list-shape expectations in `tests/test_yinyang_instructions.py:94` and `tests/test_dogfood_self.py:73`.
- Passed: `pytest -q tests/test_oauth3_vault.py`
- Passed: `pytest -q tests/test_yinyang_instructions.py tests/test_oauth3_vault.py` → `339 passed`

**Artifacts**
- Wrote the required run outputs under `data/default/apps/solace-hub-coder/outbox/runs/20260309-task054/PATCH_DIFF.md:1`, `data/default/apps/solace-hub-coder/outbox/runs/20260309-task054/RED_GATE.md:1`, `data/default/apps/solace-hub-coder/outbox/runs/20260309-task054/GREEN_GATE.md:1`, `data/default/apps/solace-hub-coder/outbox/runs/20260309-task054/ORACLE_SWEEP.md:1`, and `data/default/apps/solace-hub-coder/outbox/runs/20260309-task054/EVIDENCE.json:1`.
- Note: the spec file path from the prompt was not present locally, so I implemented against the task spec plus the backup OAuth3 source.

If you want, I can next fold the older legacy `/api/v1/oauth3/tokens` write paths fully onto the encrypted vault and remove the remaining metadata-only storage path.