# Task 055 Patch Diff

## Files changed
- `evidence_bundle.py`
- `yinyang_server.py`
- `tests/test_part11_evidence.py`

## Evidence bundle module
- Added `evidence_bundle.py` with immutable ALCOA+ bundle creation via a frozen dataclass.
- Implemented `ComplianceStatus`, `ALCOAError`, chain validation, and compliance checks.
- Enforced the required rung value `274177` and the 9 ALCOA+ dimensions.
- Implemented the required hash-chain formula: `sha256(prev_bundle_sha256 + current_bundle_sha256)` with `GENESIS` for the first bundle.

## Server changes
- Added append-only Part 11 storage at `~/.solace/evidence/evidence.jsonl` and `~/.solace/evidence/chain.lock`.
- Added `POST /api/v1/evidence/bundle` to create and persist ALCOA+ bundles.
- Added `GET /api/v1/evidence/bundles` to list sanitized bundle metadata only.
- Added `GET /api/v1/evidence/verify-chain` to validate the SHA-256 chain.
- Added `GET /api/v1/evidence/compliance-report` to summarize compliant, partial, and non-compliant bundles.
- Updated `record_evidence(...)` so existing state-changing server actions also emit Part 11 evidence bundles.

## Test changes
- Added `tests/test_part11_evidence.py` with 8 focused tests covering ALCOA fields, chain correctness, tamper detection, compliance handling, append-only storage, reporting, timestamps, and rung enforcement.
