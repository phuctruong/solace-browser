# ROADMAP.md — Solace Browser Coder App
# DNA: `roadmap(app) = phase(current) × milestone(next) × evidence(proof) → belt_progression`
# Auth: 65537 | Version: 1.0.0 | Updated: 2026-03-08

## Current Status

| Field | Value |
|-------|-------|
| Phase | 0 (Setup Verification) |
| Belt | White |
| GLOW | 0 |
| Tasks completed | 0 |
| Uplifts active | 33/47 (70%) |
| Chromium source | Downloading (~34GB/61GB) |

---

## Phase 0: Setup Verification (CURRENT)
**Goal:** Prove the pipeline works end-to-end without Chromium

| Task | Status | Evidence |
|------|--------|----------|
| Create app manifest + inbox + outbox | DONE | manifest.yaml, 8 inbox files |
| Write companion runner (run.py) | DONE | run.py (372 lines) |
| Write CLAUDE.md anti-drift chain | DONE | CLAUDE.md |
| Write AUDIT.md 47-uplift tracker | DONE | AUDIT.md |
| Dry run: prompt composition | TODO | run.py --test |
| Live run: Claude CLI spawns | TODO | run.py task-001 |
| Verify diff parser works | TODO | Parse real Claude output |
| Verify path validator works | TODO | Block forbidden paths |
| Verify evidence saves to outbox | TODO | SHA-256 bundle in outbox/runs/ |

**Exit criteria:** All 5 acceptance criteria from task-001 pass

---

## Phase 1: Chromium Build
**Goal:** Compile stock Chromium, brand it as Solace

| Task | Status | Evidence |
|------|--------|----------|
| Download Chromium source (61GB) | IN PROGRESS | fetch --nohooks chromium |
| Run gclient runhooks | TODO | |
| Run install-build-deps.sh | TODO | |
| Configure gn gen out/Solace | TODO | args.gn |
| Compile: autoninja -C out/Solace chrome | TODO | Build log |
| Launch binary, take screenshot | TODO | Screenshot |
| Brand: change app name to "Solace" | TODO | chromium_strings.grd |

**Exit criteria:** `./out/Solace/chrome` launches with "Solace" in title bar

---

## Phase 2: Native Sidebar (Yinyang)
**Goal:** Add C++ side panel to Chromium (not an extension)

| Task | Status | Evidence |
|------|--------|----------|
| Create SolaceSidePanelCoordinator | TODO | .h + .cc files |
| Register in side_panel_coordinator.cc | TODO | Build succeeds |
| Create WebUI page for sidebar content | TODO | HTML + JS |
| Connect sidebar to Python server (port 8888) | TODO | WebSocket works |
| Show task list in sidebar | TODO | Screenshot |
| Show diff viewer in sidebar | TODO | Screenshot |
| Show approve/reject buttons | TODO | User can click |

**Exit criteria:** Sidebar shows in panel menu, displays content from server

---

## Phase 3: Full Pipeline
**Goal:** End-to-end: user types task → agent codes → user approves → build → screenshot

| Task | Status | Evidence |
|------|--------|----------|
| Inbox → prompt composition in sidebar | TODO | |
| Claude CLI subprocess from sidebar | TODO | |
| Diff display with syntax highlighting | TODO | |
| Approve/reject each file | TODO | |
| Build gate with live log | TODO | |
| Screenshot capture | TODO | |
| Evidence chain with hash display | TODO | |

**Exit criteria:** Complete task from sidebar, evidence in outbox

---

## Phase 4: Port Working Code
**Goal:** Bring proven code from solace-browser-fuckup

| Task | Status | Evidence |
|------|--------|----------|
| Port Python server (port 8888) | TODO | |
| Port WebSocket bridge (ws_bridge.py) | TODO | |
| Port evidence chain (chain.py) | TODO | |
| Port MCP integration | TODO | |
| Port app detection + manifests | TODO | |
| Audit every ported file for lies | TODO | |

**Exit criteria:** All ported features verified with build + screenshot

---

## Belt Progression

| Belt | Criteria | Status |
|------|----------|--------|
| White | App created, pipeline tested | IN PROGRESS |
| Yellow | First task completed through full pipeline | TODO |
| Orange | 10 tasks completed, all evidence sealed | TODO |
| Green | Native sidebar working in custom Chromium | TODO |
| Blue | Full pipeline: sidebar → code → approve → build → screenshot | TODO |

---

## GLOW Log

| GLOW # | Date | Achievement |
|--------|------|-------------|
| — | — | No tasks completed yet |

---

*Auth: 65537 | "Phase 0 first. Earn trust. Then build."*
