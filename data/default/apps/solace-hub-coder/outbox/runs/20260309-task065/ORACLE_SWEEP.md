Task 065 focused sweep on the touched fun-pack surface:

- `yinyang_server.py` now exposes the requested auth-gated fun-pack routes for list, active pack, pack detail, activation, random joke, random fact, and greeting.
- Active-pack state persists to `ACTIVE_PACK_PATH` and defaults to `default-en` when the state file is missing, unreadable, or invalid JSON.
- Fun-pack loading computes `_meta.sha256` at read time from a canonical sealed JSON form while preserving the on-disk placeholder.
- Random selection uses `random.choice()` exactly as requested; no cryptographic randomness was introduced.
- The frontend lives in `web/fun-packs.html` with inline CSS and JS only, no CDN references, and component styling through `var(--hub-*)` tokens.
- The new hub navigation entry was added to `solace-hub/src/index.html` because this repo does not contain the requested `web/index.html` path.
- No `except Exception` was introduced in touched Python files.
- No banned `9222`, `Companion App`, or Chromium extension API strings were introduced in the touched implementation files.
- The requested paper path `papers/browser/15-tutorial-funpack-mcp.md` is not present in this workspace; implementation followed the dispatch contract directly after confirming the file was absent.
- Verification witness: `python -m pytest tests/test_fun_packs.py -q` passed with `12 passed` and `python -m py_compile yinyang_server.py tests/test_fun_packs.py` passed.
