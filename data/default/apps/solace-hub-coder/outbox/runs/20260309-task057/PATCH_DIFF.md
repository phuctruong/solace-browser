# Patch Diff

This workspace already contains unrelated uncommitted changes. This artifact isolates the Task 057 edits only.

- `yinyang_server.py:306` adds shared preview helpers for human-readable previews, stable action hashes, UTC timestamps, and pending-action records.
- `yinyang_server.py:715` adds `_append_evidence_record()` so approval and rejection can write audit rows without creating duplicate Part 11 bundles.
- `yinyang_server.py:8797` updates `POST /api/v1/actions/preview` to persist `oauth3_token_id`, reuse the preview helpers, and return explicit non-immediate execution metadata.
- `yinyang_server.py:8853` updates `POST /api/v1/actions/{action_id}/approve` to:
  - enforce cooldown and Class C step-up + reason,
  - sign approvals with HMAC over action hash + timestamp,
  - seal a concrete Part 11 bundle,
  - store and return the real `evidence_bundle_id`,
  - capture before/after state hashes in history.
- `yinyang_server.py:8967` updates `POST /api/v1/actions/{action_id}/reject` to seal rejection evidence with bundle ids and before/after hashes.
- `yinyang_server.py:9043` keeps cancel as an audit-only revoke path without extra bundle duplication.
- `tests/test_preview_cooldown_signoff.py:76` replaces socket-bound HTTP fixtures with in-process route dispatch, making the proof deterministic in sandboxed environments.
- `tests/test_preview_cooldown_signoff.py:126` strengthens the Class B preview proof for affected resources and reversal semantics.
- `tests/test_preview_cooldown_signoff.py:205` strengthens the approval proof for real bundle ids, signatures, and state hashes.
- `tests/test_preview_cooldown_signoff.py:254` strengthens the rejection proof for sealed evidence ids.
