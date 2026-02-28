# TODO — Solace Browser Build Backlog

**Project:** solace-browser — OAuth3 Reference Implementation + Desktop App
**Auth:** 65537
**Updated:** 2026-02-28

Papers driving this backlog: `23-claude-code-wrapper-as-dev-llm.md`, `24-yinyang-chat-rail-spec.md`, `26-browser-onboarding-first-run.md`
Diagrams: `13-yinyang-fsm.md`, `15-yinyang-data-flow.md`, `16-claude-code-wrapper-integration.md`

---

## COMPLETED (Sprint 0 — Web Architecture)

## TASK-WEB-001
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Replace standalone page-local CSS with shared `web/css/site.css`
Evidence: `web/home.html`, `web/download.html`, `web/machine-dashboard.html`, `web/tunnel-connect.html` all reference `/css/site.css` and contain no embedded `<style>` blocks.

## TASK-WEB-002
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Replace page-local scripts with shared `web/js/solace.js`
Evidence: all four pages reference `/js/solace.js`; page behavior degrades to safe mock states when APIs are unavailable.

## TASK-WEB-003
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Add real local webserver startup path under `src/scripts`
Evidence: `src/scripts/start-local-webserver.sh` starts `web/server.py`; clean slug URLs serve content and legacy `.html` paths redirect.

## TASK-WEB-004
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Normalize site links onto slug URLs
Evidence: site nav/footer and internal links now target `/`, `/download`, `/machine-dashboard`, `/tunnel-connect`.

## TASK-WEB-005
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Add PHUC architecture enforcement and verification
Evidence: `scripts/check_web_architecture.sh` and `tests/test_web_architecture.py` pass.

## TASK-WEB-006
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Enforce PHUC web architecture in CI on pushes and pull requests
Evidence: `.github/workflows/web-architecture.yml` runs `./scripts/check_web_architecture.sh` and `pytest -q tests/test_web_architecture.py`.


## TASK-WEB-007
[x] Status: DONE (2026-02-28)
Rung Achieved: 641
Description: Remove stale duplicate browser API surface and document one supported webservice
Evidence: `browser/http_server.py` and `browser/handlers.py` removed; `docs/BROWSER_API.md`, `README.md`, and `CLAUDE.md` now point only at `solace_browser_server.py`.

---

## PHASE 1 — Claude Code LLM Backend

Paper: `23-claude-code-wrapper-as-dev-llm.md`
Diagram: `16-claude-code-wrapper-integration.md`
Rung target: 641

- [ ] TASK-LLM-001: LLM client factory
  - Create `src/llm/__init__.py` — `get_llm_client(backend: str) -> Callable`
  - Backend selection via `SOLACE_LLM_BACKEND` env var: `claude_code` | `together` | `none`
  - Returns callable with signature: `(intent_dict: dict) -> dict` (recipe JSON)
  - Raise `ValueError` for unknown backend string
  - Test: factory returns correct client type for each backend string

- [ ] TASK-LLM-002: Claude Code wrapper client
  - Create `src/llm/claude_code_client.py`
  - Calls stillwater `ClaudeCodeWrapper` at `localhost:8080` (Ollama-compatible HTTP)
  - Callable signature: `(intent_dict: dict) -> dict`
  - Intent dict: `{intent, platform, action_type}` → sends structured recipe generation prompt
  - Response: parse JSON + validate against recipe schema
  - Raise `LLMBackendError` on connection failure, timeout, or invalid response (not silent)
  - Timeout: 30s default, configurable via `CLAUDE_CODE_TIMEOUT`
  - Test: successful call, timeout handling, connection refused → clear error message

- [ ] TASK-LLM-003: Noop client (offline/test mode)
  - Create `src/llm/noop_client.py`
  - Returns stub recipe JSON for `SOLACE_LLM_BACKEND=none`
  - Stub recipe: valid schema, single "noop" step, zero LLM cost
  - Used for: CI tests, offline dev, recipe schema validation
  - Test: noop client returns valid recipe schema

- [ ] TASK-LLM-004: Wire LLM into RecipeEngine
  - In `solace_browser_server.py` (or wherever RecipeEngine is instantiated):
    - `RecipeEngine(cache=cache, llm=get_llm_client(args.llm_backend))`
  - Wire into `_handle_run_recipe()` — recipe generation uses LLM client
  - Add `--llm-backend` argparse flag: choices `{claude_code, together, none}`, default `claude_code`
  - Startup log: `[LLM] Backend: claude_code @ localhost:8080` (or whichever backend)
  - Test: recipe engine uses correct client; startup log shows backend

- [ ] TASK-LLM-005: Dev startup script
  - Create `scripts/dev-start.sh`:
    1. Start Claude Code wrapper: `python3 /path/to/claude_code_wrapper.py` (background)
    2. Wait for wrapper health: `curl -s localhost:8080/` → `{cli_available: true}`
    3. Start solace-browser: `python3 solace_browser_server.py --port 9222 --show-ui --llm-backend claude_code`
    4. Trap SIGINT → kill both processes
  - Env vars: `SOLACE_LLM_BACKEND=claude_code`, `CLAUDE_CODE_HOST=127.0.0.1`, `CLAUDE_CODE_PORT=8080`
  - Print startup banner with version + backend + ports
  - Test: script starts both services; Ctrl+C kills both

- [ ] TASK-LLM-006: LLM backend test suite
  - Create `tests/test_llm_backend.py` — 10 tests:
    1. `get_llm_client("claude_code")` returns ClaudeCodeClient
    2. `get_llm_client("together")` returns TogetherClient (or raises NotImplementedError for now)
    3. `get_llm_client("none")` returns NoopClient
    4. `get_llm_client("unknown")` raises ValueError
    5. ClaudeCodeClient with mock server → valid recipe returned
    6. ClaudeCodeClient with server down → LLMBackendError with clear message
    7. ClaudeCodeClient timeout → LLMBackendError with timeout info
    8. NoopClient → valid recipe schema
    9. RecipeEngine integration with NoopClient → recipe generated
    10. `--llm-backend` argparse flag parsed correctly

---

## PHASE 2 — Yinyang Browser Rails (Playwright + CDP)

Paper: `24-yinyang-chat-rail-spec.md`, `26-browser-onboarding-first-run.md`
Diagrams: `13-yinyang-fsm.md`, `15-yinyang-data-flow.md`
Rung target: 641

- [ ] TASK-YY-001: Yinyang module init
  - Create `src/yinyang/__init__.py` — module docstring + version
  - Export: `TopRail`, `BottomRail`, `Highlighter`, `WSBridge`, `StateBridge`
  - No circular imports — each submodule imports independently

- [ ] TASK-YY-002: Top rail (32px status bar)
  - Create `src/yinyang/top_rail.py` — Python side:
    - `inject_top_rail(page)` — call `page.add_init_script()` to inject top rail JS
    - Rail shows: FSM state badge (color-coded), connection status, page URL
  - Create `static/top_rail.js` — Browser-side JS:
    - 32px fixed bar at top of page
    - Color map: IDLE=grey, PROCESSING=blue-pulse, PREVIEW_READY=orange, EXECUTING=green, ERROR=red
    - Receives state updates via postMessage from bottom rail
    - Minimal DOM footprint (shadow DOM preferred)
  - Test: inject into test page → rail visible → state changes reflected

- [ ] TASK-YY-003: Bottom rail (36→300px chat panel)
  - Create `src/yinyang/bottom_rail.py` — Python side:
    - `inject_bottom_rail(page)` — inject chat panel JS + CSS
    - Collapsed: 36px bar with launcher button + credits summary
    - Expanded: 300px panel with chat messages + input + credits panel
  - Create `static/bottom_rail.js` — Browser-side JS:
    - Launcher button: click to expand/collapse
    - Chat messages: scrollable area, user/assistant/system roles styled
    - Input: text input + send button
    - Credits panel: `💳 $X.XX · Y tokens · $Z.ZZ/mo`
    - WebSocket: connect to local WS bridge for real-time chat
    - Mobile: collapsible to 36px, full layout at 768px+
  - Test: inject → launcher visible → expand → chat UI rendered → collapse works

- [ ] TASK-YY-004: Element highlighter (CDP overlay)
  - Create `src/yinyang/highlighter.py`:
    - `highlight_element(page, selector)` — highlight via CDP `Overlay.highlightNode`
    - `clear_highlights(page)` — remove all highlights
    - JS fallback: if CDP overlay unavailable, inject CSS outline on target element
    - Highlight config: color=orange, border=2px, animation=pulse
  - Used by: Yinyang shows what it's about to click/interact with
  - Test: highlight selector → element outlined; clear → outline removed

- [ ] TASK-YY-005: WebSocket bridge (browser JS ↔ Python ↔ Cloud)
  - Create `src/yinyang/ws_bridge.py`:
    - Local WebSocket server at `/ws/yinyang` (on browser's port)
    - JS (bottom_rail.js) connects to `ws://localhost:{port}/ws/yinyang`
    - Python bridge: relay messages between browser JS and solaceagi.com cloud API
    - Auth-aware: if logged in → real API relay; if guest → local mock responses
    - Message format: JSON `{type, payload}` matching solaceagi WS protocol
  - Add to `solace_browser_server.py` route table
  - Test: WS connect → message sent → response received → connection close clean

- [ ] TASK-YY-006: State bridge (tab state → rail updates)
  - Create `src/yinyang/state_bridge.py`:
    - Monitor tab state machine (navigation events, page loads, errors)
    - On page.goto() → update top rail URL + state
    - On recipe execution → update top rail state (EXECUTING → DONE)
    - On error → update top rail (ERROR state, red badge)
    - Forward page context to cloud API for Yinyang chat awareness
  - Test: navigate to URL → top rail updated; recipe runs → state transitions shown

- [ ] TASK-YY-007: Wire Yinyang into browser server
  - In `solace_browser_server.py`:
    - On every `page.goto()`: call `inject_top_rail(page)` + `inject_bottom_rail(page)`
    - Start WS bridge on server startup
    - Pass LLM client + auth state to WS bridge
    - Config: `--yinyang` flag to enable/disable (default: enabled)
    - Config: `--yinyang-cloud-url` for solaceagi.com endpoint (default: https://www.solaceagi.com)
  - Test: browser starts with Yinyang → rails visible on page → WS bridge accepting connections

- [ ] TASK-YY-008: Yinyang integration test suite
  - Create `tests/test_yinyang_integration.py` — 15+ tests:
    1. Top rail injects on page load
    2. Bottom rail injects on page load
    3. Bottom rail expands/collapses
    4. Chat message sent via WS → response received
    5. State transition → top rail color updates
    6. Highlighter highlights element → visible outline
    7. Highlighter clears → outline removed
    8. Credits panel shows balance (mock data)
    9. Guest mode → mock responses (no API calls)
    10. Auth mode → API relay attempted
    11. WS reconnect after disconnect
    12. Page navigation → rails persist (re-inject)
    13. Multiple tabs → independent sessions
    14. --yinyang=false → no rails injected
    15. Error state → red badge on top rail

---

## PHASE 3 — Binary Compilation + Distribution

Paper: `28-browser-distribution-installation.md`
Rung target: 641

- [ ] TASK-DIST-001: PyInstaller spec update
  - Update `solace-browser.spec`:
    - Add `src/llm/` and `src/yinyang/` to `pathex` and `hiddenimports`
    - Add `static/top_rail.js`, `static/bottom_rail.js` to data files
    - Version info: `solace-browser 1.0.1`
  - Build: `python -m PyInstaller solace-browser.spec --clean --noconfirm`
  - Test: `./dist/solace-browser --version` prints `solace-browser 1.0.1`, exits 0

- [ ] TASK-DIST-002: Binary smoke test
  - `./dist/solace-browser --help` — shows all flags including `--llm-backend`, `--yinyang`
  - `./dist/solace-browser --llm-backend none` — starts without wrapper dependency
  - Health: `curl localhost:9222/api/health` → 200 within 5s
  - Startup log: shows LLM backend, port, version
  - Test: binary runs standalone (no source code needed)

- [ ] TASK-DIST-003: GCS upload script
  - Create `scripts/upload-release.sh`:
    - `sha256sum dist/solace-browser > dist/solace-browser.sha256`
    - Upload to `gs://solace-downloads/v{version}/solace-browser-{platform}-{arch}`
    - Upload checksum alongside
    - Set public read ACL
  - Test: uploaded file accessible via public URL; SHA256 matches

---

## BUILD ORDER

```
Phase 1 (LLM Backend)      ← START HERE — enables recipe execution with real LLM
    ↓
Phase 2 (Yinyang Rails)    ← requires Phase 1 (LLM for chat responses)
    ↓
Phase 3 (Binary + Dist)    ← requires Phase 1 + 2 (all features compiled)
```

**Dependencies on solaceagi:**
- Phase 2 (Yinyang Rails) needs solaceagi Phase 10 (Yinyang Chat Backend) for cloud relay
- Phase 2 can work in guest/mock mode without solaceagi running

**Next action:** `/build Phase 1` — Claude Code LLM Backend
