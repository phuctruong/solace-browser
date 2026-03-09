**Done**
- Added domain-index build/load, exact+wildcard+path matching, manifest/store fallback, and tier-gated `/api/v1/apps/by-domain` responses in `yinyang_server.py:2256` and `yinyang_server.py:4349`.
- Added custom app scaffolding under `data/custom/apps`, automatic index rebuilds, and `POST /api/v1/apps/rebuild-domain-index` in `yinyang_server.py:2576` and `yinyang_server.py:4152`.
- Added the 8 requested focused tests in `tests/test_domain_app_linking.py:1`.

**Validation**
- `pytest -q tests/test_domain_app_linking.py` → 8 passed.
- `python -m py_compile yinyang_server.py tests/test_domain_app_linking.py` passed.

**Artifacts**
- Wrote `PATCH_DIFF.md`, `RED_GATE.md`, `GREEN_GATE.md`, `ORACLE_SWEEP.md`, and `EVIDENCE.json` in `data/default/apps/solace-browser-coder/outbox/runs/20260309-task053/`.
- Kill checks on `data/default/apps/solace-browser-coder/outbox/runs/20260309-task053/PATCH_DIFF.md:1` are clean: `9222=0`, `companion app=0`, `except Exception=0`.

If you want, I can also update the older domain-detection tests to the new response contract.