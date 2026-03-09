**Done**
- Added the uplift engine in `app/services/uplift_injector.py:70` with tier matrix enforcement, safe inbox loading, preview metadata, and no free→paid leakage.
- Added managed run + ABCD comparison service in `app/services/app_run_service.py:19`, plus new contracts in `app/schemas/apps.py:11`.
- Added the new routes in `app/api/v1/routers/apps.py:16` and registered them in `app/api/v1/router.py:40`.

**Validated**
- Added 7 focused tests in `tests/app_v1/test_uplift_injection.py:67`.
- Passed: `pytest tests/app_v1/test_task_009_llm_edges.py tests/test_router_registration.py tests/app_v1/test_uplift_injection.py -q` → `14 passed`.
- Passed: `ruff check app/services/uplift_injector.py app/services/app_run_service.py app/schemas/apps.py app/api/v1/routers/apps.py tests/app_v1/test_uplift_injection.py`.

**Artifacts**
- Wrote the proof bundle to `outbox/runs/20260309-task009/PATCH_DIFF.md:1`, `outbox/runs/20260309-task009/RED_GATE.md:1`, `outbox/runs/20260309-task009/GREEN_GATE.md:1`, `outbox/runs/20260309-task009/ORACLE_SWEEP.md:1`, and `outbox/runs/20260309-task009/EVIDENCE.json:1`.
- I could not write to `/home/phuc/projects/solace-browser/...` because that sibling path is outside this run’s writable sandbox, so I mirrored the bundle in-repo.