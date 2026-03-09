# RED_GATE

Baseline note:
- This repository snapshot was already modified when Task 054 began, so a literal pre-patch re-run of the new vault suite was not preserved.
- The baseline failure is reconstructed from the committed server contract before this patch: no `/api/v1/oauth3/token/issue`, `/api/v1/oauth3/token/validate`, `/api/v1/oauth3/token/revoke`, `/api/v1/oauth3/step-up/request`, or `/api/v1/oauth3/evidence` handlers existed, and OAuth3 storage was metadata-only rather than AES-GCM encrypted.

Expected failing command on the pre-patch baseline:
```bash
pytest -q tests/test_oauth3_vault.py
```

Expected baseline failures:
```text
- POST /api/v1/oauth3/token/issue → 404 not found
- GET /api/v1/oauth3/token/validate → 404 not found
- POST /api/v1/oauth3/token/revoke → 404 not found
- POST /api/v1/oauth3/step-up/request → 404 not found
- GET /api/v1/oauth3/evidence → 404 not found
- Vault file at ~/.solace/oauth3-vault.enc not created
- Evidence chain not persisted inside an encrypted vault
```
