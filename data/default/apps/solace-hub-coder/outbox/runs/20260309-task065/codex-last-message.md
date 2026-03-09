**Done**
- Added the bundled default pack at `data/fun-packs/default-en.json:1`.
- Added fun-pack constants, loaders, activation state, and auth-gated API routes in `yinyang_server.py:157`, `yinyang_server.py:1160`, `yinyang_server.py:3443`, `yinyang_server.py:3697`, `yinyang_server.py:9020`.
- Added the inline frontend at `web/fun-packs.html:1`.
- Added a hub navigation entry in `solace-hub/src/index.html:824` and `solace-hub/src/index.html:1433` since this repo does not contain `web/index.html`.

**Validation**
- `python -m pytest tests/test_fun_packs.py -q` → `12 passed`
- `python -m py_compile yinyang_server.py tests/test_fun_packs.py` → passed
- The route tests live in `tests/test_fun_packs.py:1` and use an in-memory `YinyangHandler` harness because this sandbox blocks binding test sockets on `18888`.

**Artifacts**
- Wrote the required run files to `data/default/apps/solace-hub-coder/outbox/runs/20260309-task065/PATCH_DIFF.md:1`
- Wrote `data/default/apps/solace-hub-coder/outbox/runs/20260309-task065/RED_GATE.md:1`
- Wrote `data/default/apps/solace-hub-coder/outbox/runs/20260309-task065/GREEN_GATE.md:1`
- Wrote `data/default/apps/solace-hub-coder/outbox/runs/20260309-task065/ORACLE_SWEEP.md:1`
- Wrote `data/default/apps/solace-hub-coder/outbox/runs/20260309-task065/EVIDENCE.json:1`

- Note: the requested paper path `papers/browser/15-tutorial-funpack-mcp.md` is not present in this workspace, so I implemented directly from the dispatch contract.

Want me to add one extra smoke test for serving `GET /web/fun-packs.html` through the handler too?