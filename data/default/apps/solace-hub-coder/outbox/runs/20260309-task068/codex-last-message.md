**Done**
- Added the pending dashboard page at `web/pending-actions.html:1` with token-only CSS, 1s cooldown countdowns, 10s auto-refresh, and vanilla JS approve/reject flows.
- Wired the route in `yinyang_server.py:3502` and added a matching static handler in `yinyang_server.py:8990`.
- Added RED/GREEN tests in `tests/test_pending_actions_dashboard.py:1` using a unique test port `18896`.

**Checks**
- Ran `pytest -q tests/test_pending_actions_dashboard.py tests/test_preview_cooldown_signoff.py`
- Result: `18 passed in 0.76s`
- Verified the new page uses the existing actions APIs at `web/pending-actions.html:226` and handles Class C approval requirements at `web/pending-actions.html:491`.

**Artifacts**
- Wrote required handoff files under `data/default/apps/solace-hub-coder/outbox/runs/20260309-task068/`
- Included `PATCH_DIFF.md`, `RED_GATE.md`, `GREEN_GATE.md`, `ORACLE_SWEEP.md`, and `EVIDENCE.json:1`

**Notes**
- The page prefers `solace_token_sha256` and hashes `solace_token` client-side when needed, matching server auth expectations.
- I kept changes scoped to this task; the repo already has unrelated dirty files outside these edits.