**Done**
- Added the Evidence Viewer page at `web/evidence-viewer.html:1` with the requested verify/filter/timeline behavior and tokenized theme colors.
- Added the page route at `yinyang_server.py:3509` and handler at `yinyang_server.py:9011`, matching the same static HTML serving pattern used for `pending-actions.html`.
- Added `/api/v1/evidence/log` as an alias to the existing evidence list handler at `yinyang_server.py:3201` so the dispatched frontend path actually works.

**Validation**
- Added RED→GREEN coverage in `tests/test_evidence_viewer.py:1`, including route serving and the `/api/v1/evidence/log` alias check at `tests/test_evidence_viewer.py:89`.
- Ran `pytest -q tests/test_evidence_viewer.py` → `11 passed`.
- Ran `pytest -q tests/test_pending_actions_dashboard.py tests/test_evidence_viewer.py` → `21 passed`.

**Artifacts**
- Wrote all required outputs to `data/default/apps/solace-hub-coder/outbox/runs/20260309-task070/PATCH_DIFF.md:1`, `data/default/apps/solace-hub-coder/outbox/runs/20260309-task070/RED_GATE.md:1`, `data/default/apps/solace-hub-coder/outbox/runs/20260309-task070/GREEN_GATE.md:1`, `data/default/apps/solace-hub-coder/outbox/runs/20260309-task070/ORACLE_SWEEP.md:1`, and `data/default/apps/solace-hub-coder/outbox/runs/20260309-task070/EVIDENCE.json:1`.

If you want, I can also add a nav entry linking to `web/evidence-viewer.html`.