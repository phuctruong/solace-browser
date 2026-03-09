# PATCH_DIFF

## Files changed
- `requirements.txt`
- `tests/test_dogfood_self.py`
- `tests/test_oauth3_vault.py`
- `tests/test_yinyang_instructions.py`
- `yinyang_server.py`

## Summary
- Added an AES-256-GCM encrypted OAuth3 vault stored at `~/.solace/oauth3-vault.enc` with PBKDF2-HMAC-SHA256 key derivation.
- Added the new OAuth3 routes for issue, validate, revoke, step-up request, token listing, and vault evidence retrieval.
- Added hash-chained OAuth3 evidence events persisted inside the encrypted vault.
- Preserved legacy `/api/v1/oauth3/tokens` management behavior where practical while migrating listing/detail/extend/audit to understand vault-backed tokens.
- Added focused OAuth3 vault tests and adjusted older token-list assertions to accept the migrated list response shape.
- Added `cryptography` to `requirements.txt` so the new vault dependency is declared explicitly.

## Diffstat
```text
 requirements.txt                   |    2 +
 tests/test_dogfood_self.py         |    3 +-
 tests/test_yinyang_instructions.py |   14 +-
 tests/test_oauth3_vault.py         |  211 ++++++++++++++++++++++++++++++++
 yinyang_server.py                  | 2192 ++++++++++++++++++++++++++++++++++--
 5 files changed, 2306 insertions(+), 117 deletions(-)
```
