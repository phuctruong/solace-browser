**Done**
- Added the Prime Wiki community page at `web/prime-wiki.html:1` with the exact dispatched HTML, stats grid, search bar, and vanilla `fetch()` calls.
- Wired `GET /web/prime-wiki.html` in `yinyang_server.py:3465` and added a dedicated static HTML handler in `yinyang_server.py:9207`.
- Followed the existing `fun-packs.html` serving pattern because a shared `_serve_static_html()` helper does not exist.

**Validation**
- Added RED/GREEN coverage in `tests/test_prime_wiki_ui.py:1`.
- Ran `pytest -q tests/test_prime_wiki_ui.py` → `10 passed`.
- Ran `pytest -q tests/test_fun_packs.py tests/test_prime_wiki_snapshots.py tests/test_prime_wiki_ui.py` → `30 passed`.

**Artifacts**
- Wrote `PATCH_DIFF.md`, `RED_GATE.md`, `GREEN_GATE.md`, `ORACLE_SWEEP.md`, and `EVIDENCE.json` under `data/default/apps/solace-hub-coder/outbox/runs/20260309-task069/`.