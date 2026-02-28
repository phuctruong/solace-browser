# TODO — Solace Browser (Browser Vertex)

**Project:** solace-browser — Headless Chromium + CDP + React frontend
**Stack:** Python 3.10 (Playwright, aiohttp), React/TypeScript (Vite), PyInstaller
**Tests:** `cd /home/phuc/projects/solace-browser && python -m pytest tests/ -x -q`
**Binary:** `python -m PyInstaller solace-browser.spec --clean --noconfirm`

---

## TASK-001: Integrate sync client into main server startup

**Priority:** P0
**Files:** `solace_browser_server.py`, `src/sync_client.py`
**Status:** DONE (2026-02-28)
**Rung Achieved:** 641
**Evidence:** CLI sync flags + sync config builder + startup heartbeat/background loop + Part 11 upload hook integration in `solace_browser_server.py`; verified by `pytest tests/test_wave6_browser_server.py tests/test_sync_client.py -q`

Sync client module exists (`src/sync_client.py`) with routes registered, but it's not initialized on startup. Need auto-heartbeat and optional auto-sync.

**Steps:**
1. Read `src/sync_client.py` — `SyncConfig.from_env()` reads API URL + key
2. In `SolaceBrowser.__init__` or `SolaceBrowserServer.start()`, initialize `SyncClient` from config
3. If API key is configured, send initial heartbeat on startup
4. Add optional background task: heartbeat every 60s (configurable via `--sync-interval`)
5. Add CLI flags: `--sync-api-url`, `--sync-api-key`, `--sync-interval`
6. Test: start browser with sync config, verify heartbeat hits cloud

**Done when:** `solace-browser --sync-api-key sk_... --sync-interval 60` sends heartbeats to solaceagi.com.

---

## TASK-002: Build macOS and Windows binaries

**Priority:** P0
**Files:** `solace-browser.spec`, CI/CD
**Status:** DONE (2026-02-28, repo/CI implementation)
**Rung Achieved:** 641
**Evidence:** Added `.github/workflows/build-binaries.yml`, bundled sync modules in `solace-browser.spec`, and updated `web/download.html` to point at the GCS release bucket; verified by `pytest tests/test_distribution.py -q`. Actual binary publication happens on the next `v*` tag push in GitHub Actions.

Currently only Linux x86_64 binary exists on GCS. Need macOS and Windows builds.

**Steps:**
1. For macOS: run PyInstaller on a Mac (GitHub Actions `macos-latest` runner)
2. For Windows: run PyInstaller on Windows (GitHub Actions `windows-latest` runner)
3. Create `.github/workflows/build-binaries.yml`:
   - Trigger: on tag push (`v*`)
   - Matrix: [ubuntu-latest, macos-latest, windows-latest]
   - Steps: checkout, setup python, pip install deps, PyInstaller build, upload to GCS
4. Upload binaries to `gs://solace-downloads/v1.0.0/` with platform suffixes
5. Update `web/browser.html` in solaceagi to link to real macOS/Windows binaries

**Done when:** All 3 platform binaries on GCS, download page links updated.

---

## TASK-003: Evidence auto-upload to cloud

**Priority:** P1
**Files:** `src/evidence_upload.py`, `src/sync_client.py`
**Status:** DONE (2026-02-28)
**Rung Achieved:** 641
**Evidence:** Added post-seal Part 11 upload hook, auto-upload gating via `SOLACE_EVIDENCE_AUTO_UPLOAD`, and `last_evidence_upload` status reporting in `solace_browser_server.py`; verified by `pytest tests/test_wave6_browser_server.py tests/test_sync_client.py -q`

Evidence collector exists but auto-upload isn't wired to Part 11 audit events.

**Steps:**
1. Read `src/evidence_upload.py` — `EvidenceCollector` scans `~/.solace/audit/`
2. After each Part 11 audit event completes, trigger `upload_pending_evidence()`
3. Add to `SolaceBrowser` Part 11 flow: after evidence is sealed, call collector
4. Respect `SOLACE_EVIDENCE_AUTO_UPLOAD=true/false` env var (default: false for privacy)
5. Add upload status to `/api/sync/status` response
6. Test with Part 11 mode: `./solace-browser --part11 --sync-api-key sk_...`

**Done when:** Part 11 evidence bundles auto-upload to cloud when configured.

---

## TASK-004: Add --version flag

**Priority:** P1
**File:** `solace_browser_server.py`
**Status:** DONE (2026-02-28)
**Rung Achieved:** 641
**Evidence:** Added `__version__`, argparse `--version`, and parser regression coverage in `tests/test_wave6_browser_server.py`

Binary doesn't support `--version`. Should print version and exit.

**Steps:**
1. Add version constant at top of `solace_browser_server.py`: `__version__ = "1.0.0"`
2. Add argparse argument: `parser.add_argument('--version', action='version', version=f'solace-browser {__version__}')`
3. Rebuild binary and test: `./solace-browser --version`

**Done when:** `solace-browser --version` prints `solace-browser 1.0.0`.

---

## TASK-005: Expand recipe library (Slack, GitHub, Notion)

**Priority:** P1
**Files:** `data/recipes/`
**Status:** DONE (2026-02-28)
**Rung Achieved:** 641
**Evidence:** Added `data/default/recipes/slack/slack-digest.json`, `data/default/recipes/github/github-pr-review.json`, and `data/default/recipes/notion/notion-daily.json`; expanded recipe validation coverage in `tests/test_multi_platform_recipe_validation.py` and `tests/test_recipe_all_parse.py`

Current recipes: email-triage, gmail-search, gmail-archive. Need more for launch.

**Steps:**
1. Create `data/recipes/slack-digest.yaml` — summarize unread Slack channels
2. Create `data/recipes/github-pr-review.yaml` — list open PRs, summarize changes
3. Create `data/recipes/notion-daily.yaml` — create daily note from template
4. Each recipe needs: name, description, scopes, steps (CPU + LLM nodes), budget limits
5. Follow existing recipe format in `data/recipes/email-triage.yaml`
6. Add tests for recipe parsing and step validation

**Done when:** 6+ recipes in library, all parseable, all with budget limits defined.

---

## TASK-006: Fix competitive_features hard dependency

**Priority:** P2
**File:** `src/competitive_features.py`
**Status:** DONE (2026-02-28)
**Rung Achieved:** 641
**Evidence:** Guarded all competitive feature handler call sites in `solace_browser_server.py` and added missing-module `503` regression tests in `tests/test_wave6_browser_server.py`; verified by full suite `pytest tests/ -q`

`competitive_features` is imported with try/except fallback (fixed for PyInstaller), but the functions (`load_proxy_config`, `select_proxy`, `solve_captcha`, `webvoyager_score`) are called without null checks throughout the codebase.

**Steps:**
1. `grep -rn "load_proxy_config\|select_proxy\|solve_captcha\|webvoyager_score" solace_browser_server.py`
2. Wrap each call site with `if solve_captcha is not None:` guards
3. Test binary runs without `src/competitive_features.py` present
4. Run full test suite

**Done when:** Binary runs clean with zero warnings about competitive_features.

---

## Backlog

- [ ] Headed mode window positioning and sizing options
- [ ] Multi-tab support (parallel page sessions)
- [ ] Cookie/session export for recipe sharing
- [ ] Playwright stealth mode integration (anti-detection)
- [ ] Frontend dashboard: real-time view of browser actions + evidence
- [ ] WebSocket live stream of browser events to frontend
