# TODO — Solace Browser
# Updated: 2026-03-07 | Auth: 65537 | Belt: Yellow
# Source: Virtual Focus Group (49 Personas × 5 Phases) + Competitive Analysis
# Tests: 5,307+ | Modules: 22+ | Rung Target: 65537
# Pipeline: papers → diagrams → styleguides → webservices → tests → code → seal

---

## P0 — Critical Path (Beta Mar 9)

### T1: Plain-English scope confirmation UI ✅
**Files:** src/ui/scope_display.py — 668 lines, tests/test_scope_display.py

### T2: Step-by-step execution progress UI ✅
**Files:** src/ui/execution_progress.py — 324 lines, tests/test_execution_progress.py

### T3: First-success celebration (delight engine) ✅
**Files:** src/yinyang/delight_engine.py — 677 lines, 28 tests pass (bug fixed 7fa691e)

### T4: Preview explainer ("what will happen") ✅
**Files:** src/ui/preview_explainer.py — 414 lines, tests/test_preview_explainer.py

---

## P1 — Launch (Mar 9 → Apr 1)

### T5: Plain-English evidence summary ✅
**Phase:** 4-VALUE | **Score:** 2.00 | **Source:** Kernighan, Norman, Rams
**Acceptance:** "6 emails triaged, 2 marked important, 1 draft created. Time: 47s"
**Files:** src/evidence/summary_formatter.py (new)
**Tests:** ~15

### T6: Live Mermaid execution diagram ✅
**Phase:** 4-VALUE | **Score:** 1.80 | **Source:** Mermaid Creator, Karpathy
**Acceptance:** Mermaid stateDiagram in browser, nodes highlight green on completion, current pulses
**Files:** src/ui/live_diagram.py (new)
**Tests:** ~12

### T7: Visual execution replay (screenshots per step)
**Phase:** 4-VALUE | **Score:** 1.44 | **Source:** Karpathy, Norman
**Acceptance:** Optional screenshot at each step, playable as slideshow, stored in evidence (encrypted)
**Files:** src/capture_pipeline.py (extend existing)
**Tests:** ~15

### T8: Yinyang emotional indicators
**Phase:** 5-HABIT | **Score:** 1.20 | **Source:** Ekman, Norman, Siegel
**Acceptance:** Yinyang face changes: happy (healthy), concerned (tokens expiring), alert (failures)
**Files:** src/yinyang/ (extend existing)
**Tests:** ~10

---

## P2 — Growth (Apr → May)

### T9: Prime Wiki + PZip snapshot engine
**Phase:** 4-VALUE | **Score:** 3.80 | **Source:** Paper 22 (Berners-Lee, Karpathy, Larry Page)
**Acceptance:** On navigate, capture Prime Wiki snapshot (LLM once → cache forever). PZip 66:1 compress. RTC verified. Local cache at ~/.solace/prime-wiki/
**Settings:**
  - prime_wiki.enabled (bool, default: true)
  - prime_wiki.depth: "full" | "shallow" | "headings_only"
  - prime_mermaid.enabled (bool, default: true)
  - prime_mermaid.auto_capture (bool, default: true)
  - screenshots.enabled (bool, default: true)
  - community.sync_enabled (bool, default: false — explicit opt-in)
  - community.auto_pull (bool, default: true for paid)
**API endpoints (browser, port 9222):**
  - POST /api/prime-wiki/capture
  - GET  /api/prime-wiki/mermaid?url=<encoded>
  - POST /api/prime-wiki/rtc
  - POST /api/prime-wiki/push (OAuth3: community.write, Pro only)
  - GET  /api/prime-wiki/pull?url_hash=<sha256> (OAuth3: community.read)
**Files:** src/prime_wiki/extractor.py, src/prime_wiki/pzip_bridge.py, src/prime_wiki/community_sync.py
**Tests:** ~40

### T10: Natural language recipe creation
**Phase:** 4-VALUE | **Score:** 2.40 | **Source:** Hopper, Norman, Karpathy
**Acceptance:** User describes task in English → AI generates recipe.json → preview before save
**Files:** src/recipes/nl_compiler.py (new)
**Tests:** ~20

### T10: Proactive Yinyang suggestions
**Phase:** 5-HABIT | **Score:** 1.92 | **Source:** Van Edwards, Ekman, Siegel
**Acceptance:** Pattern learning: "Ready for morning brief?" at 8am. Anti-Clippy: never auto-execute
**Files:** src/yinyang/proactive.py (new)
**Tests:** ~15

### T11: Cross-app recipe chaining (browser side)
**Phase:** 4-VALUE | **Score:** 3.20 | **Source:** Lovelace, Kleppmann
**Acceptance:** Execute pipeline across apps with single evidence chain, browser context switching
**Files:** src/recipes/pipeline_executor.py (new)
**Tests:** ~25

### T12: Chrome extension (lightweight entry point)
**Phase:** 3-INSTALL | **Score:** 1.44 | **Source:** Hashimoto, Hightower
**Acceptance:** Chrome Web Store extension, shows recipes for current tab, delegates to CLI/cloud
**Files:** extension/ (new directory)
**Tests:** ~20

---

## P2.5 — MCP Server: AI Agent Interface (Paper 47 §24)

### T15: MCP server core — stdio transport + tool registry
**Paper:** 47 §24 | **Priority:** P0
**Acceptance:** `solace-browser mcp` starts stdio MCP server, `tools/list` returns core browser tools
**Files:** src/solace_mcp/__init__.py, src/solace_mcp/server.py, src/solace_mcp/transport.py
**Tests:** ~20
**Details:**
- MCP server runs in companion app process (same as webservice)
- stdio transport for local agents (Claude Code, Codex)
- Tool registry with versioned schema
- Health check tool always present

### T16: Core browser tools — navigate, screenshot, click, type, scroll, snapshot
**Paper:** 47 §24 | **Priority:** P0
**Acceptance:** AI agent can navigate, take screenshots, interact with page elements via MCP tools
**Files:** src/solace_mcp/tools_core.py
**Tests:** ~25
**Details:**
- 1:1 mapping to existing webservice endpoints
- Shared handler code (MCP calls same functions as HTTP API)
- `solace_navigate`, `solace_screenshot`, `solace_page_snapshot`, `solace_click`, `solace_type`, `solace_scroll`
- `solace_health`, `solace_status`

### T17: Dynamic app tools — generate MCP tools from app manifests
**Paper:** 47 §24 | **Priority:** P0
**Acceptance:** Install a new app manifest → `tools/list` shows new tools automatically. No code changes needed.
**Files:** src/solace_mcp/tools_apps.py
**Tests:** ~20
**Details:**
- Read all manifest.yaml from data/default/apps/
- Each app generates: `solace_app_{id}_run`, `solace_app_{id}_benchmarks`, `solace_app_{id}_status`
- Cache invalidation when manifest files change (mtime check)
- Tool descriptions from manifest `description` field

### T18: Model + evidence tools
**Paper:** 47 §24 | **Priority:** P1
**Acceptance:** AI agent can list models, get benchmarks, search/verify evidence via MCP
**Files:** src/solace_mcp/tools_evidence.py
**Tests:** ~15
**Details:**
- `solace_list_models`, `solace_list_apps`, `solace_app_benchmarks`
- `solace_search_evidence`, `solace_verify_evidence`, `solace_list_screenshots`
- `solace_discovery_map` (site structure mapping)
- Trade secret boundary enforced (no uplift internals in responses)

### T19: OAuth3 scope gating for MCP calls
**Paper:** 47 §24 | **Priority:** P1
**Acceptance:** MCP tool calls check OAuth3 scopes. Unauthorized calls return clear error.
**Files:** src/solace_mcp/oauth3_gate.py
**Tests:** ~15
**Details:**
- Same scope model as webservice: navigate=LOW, click=MEDIUM, run_app=per-app-scope
- Step-up required for destructive actions (same as webservice)
- Evidence bundle emitted for every MCP tool call

### T20: SSE transport for remote/tunnel MCP access
**Paper:** 47 §24 | **Priority:** P2
**Acceptance:** MCP clients can connect via SSE over tunnel for cloud twin scenarios
**Files:** src/solace_mcp/transport.py (extend)
**Tests:** ~10
**Details:**
- SSE endpoint at /mcp/sse on webservice port
- Tunnel-compatible (goes through existing tunnel.solaceagi.com)
- OAuth3 token required for remote access

### T21: Claude Code .mcp.json + Codex integration docs
**Paper:** 47 §24 | **Priority:** P1
**Acceptance:** Drop `.mcp.json` in project root → Claude Code auto-discovers Solace Browser tools
**Files:** templates/mcp.json, docs/mcp-integration.md
**Tests:** ~5 (validation)
**Details:**
- Template .mcp.json for Claude Code projects
- Codex compatible configuration
- Getting started guide for AI agent users

---

## P3 — Ecosystem (May → Jun)

### T13: Recipe debugger (browser visualization)
**Phase:** 5-HABIT | **Score:** 2.45 | **Source:** Guido, Fowler
**Acceptance:** Visual debugger: DOM snapshot at each step, state inspection panel
**Files:** src/ui/debugger.py (new)
**Tests:** ~15

### T14: Weekly value dashboard
**Phase:** 5-HABIT | **Score:** 1.28 | **Source:** Allen, Van Edwards
**Acceptance:** Dashboard: tasks completed, time saved, top recipes, week-over-week comparison
**Files:** src/ui/value_dashboard.py (new)
**Tests:** ~10

---

## Completed (Session G+L+M+N)

### Previous P0+P1 (4,814 tests) ✅
- Budget gates (56), Auth proxy (62), Yinyang rails (61), Session manager (47)
- Cross-app (24), Capture pipeline (80), Evidence chain (48), Delight engine (43)
- Support bridge (32), Alert queue (26), Install browsers (61), Settings manager (32)
- Personality (37), macOS spec (30), Gmail recipe execution pipeline (38)
