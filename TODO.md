# TODO — Solace Browser
# Updated: 2026-03-01 | Auth: 65537
# Agent: Codex (execute in this repo)
# Rung Target: 641 (all tasks)
# Papers: papers/01-08 | Diagrams: src/diagrams/01-18 | OpenAPI: src/api/openapi.yaml

---

## Architecture

4-plane design: Capture (always-on) + Control (OAuth3) + Execution (recipes) + Evidence (hash-chain).
LLM called ONCE at preview. Execution = deterministic CPU replay of sealed outbox.
18 day-one apps. Cross-app orchestration via outbox→inbox. Yinyang = only user interface.

**Fallback ban:** No `except Exception: pass`. No mock data in production. No silent degradation.

---

## P0 — Must Ship (Core)

### T1: Wire app-store.html to live API
**Status:** DONE (2026-03-01)
**Files:** `web/js/solace.js`, `web/app-store.html`, `web/server.py`
**What:** Replace hardcoded app cards with dynamic fetch from `/api/apps`. Add search filter JS.
**Accept:** `fetchJson('/api/apps')` populates cards. Search input filters by name/category. Category sections generated from API response.
**Depends on:** T3

### T2: Wire app-detail.html to live API
**Status:** DONE (2026-03-01)
**Files:** `web/js/solace.js`, `web/app-detail.html`, `web/server.py`
**What:** Read `?app=` query param, fetch `/api/apps/{appId}`, populate inbox/outbox/budget/scopes/runs sections dynamically.
**Accept:** Page loads app data from API. Inbox files show real status. Outbox shows real pending items. Recent runs table populated.
**Depends on:** T3, T5

### T3: Implement real API endpoints in web/server.py
**Status:** DONE (2026-03-01)
**Files:** `web/server.py`
**What:** Replace mock JSON responses with real filesystem reads:
- `GET /api/apps` — scan `~/.solace/apps/*/manifest.yaml`, return list
- `GET /api/apps/{appId}` — read specific manifest + inbox/ + outbox/ status
- `GET /api/apps/{appId}/inbox` — list files in app inbox/
- `GET /api/apps/{appId}/outbox` — list files in app outbox/
- `GET /api/settings` — read `~/.solace/settings.json`
- `PUT /api/settings` — write `~/.solace/settings.json` (hot-reload)
**Accept:** All endpoints return real data. 404 for missing apps. Settings persist across restarts.

### T4: Wire settings.html to live API
**Status:** DONE (2026-03-01)
**Files:** `web/js/solace.js`, `web/settings.html`
**What:** Fetch `/api/settings` on load, populate all 8 sections. Add save buttons that PUT back.
**Accept:** Settings round-trip: load → edit → save → reload shows saved values.
**Depends on:** T3

### T5: Implement inbox/outbox filesystem operations
**Status:** DONE (2026-03-01)
**Files:** `src/inbox_outbox.py` (NEW), `src/companion/apps.py`
**What:** InboxOutboxManager class:
- `list_inbox(app_id)` → list files by type (prompts/, templates/, assets/, policies/, datasets/, requests/, conventions/)
- `list_outbox(app_id)` → list files by type (previews/, drafts/, reports/, suggestions/, runs/)
- `read_file(app_id, path)` → content + SHA-256 hash
- `write_outbox(app_id, type, name, content)` → write + update manifest
- `validate_inbox(app_id)` → check required files per manifest (including diagrams/ dir)
**Accept:** Unit tests for each method. Files in correct directories. SHA-256 hashes computed. Fails if diagrams/ missing.
**Tests:** `tests/test_inbox_outbox.py`

### T6: Create default app directory structure + 18 day-one app manifests
**Status:** DONE (2026-03-01)
**Files:** `scripts/init_apps.py` (NEW), `data/default/apps/` (NEW — 18 subdirs)
**What:** Script to create `~/.solace/apps/{app_id}/` for each app. Create manifest.yaml, recipe.json, budget.json, and diagrams/ for all 18 day-one apps:
- **10 standard:** gmail-inbox-triage, calendar-brief, focus-timer, github-issue-triage, slack-triage, linkedin-outreach, google-drive-saver, youtube-script-writer, twitter-monitor, reddit-scanner
- **5 no-API exclusive:** whatsapp-responder, amazon-price-tracker, instagram-poster, twitter-poster, linkedin-poster
- **3 orchestrators:** morning-brief, weekly-digest, lead-pipeline
- Each app: manifest.yaml + diagrams/workflow.md + diagrams/data-flow.md + diagrams/partner-contracts.md + budget.json + inbox/{prompts,templates,assets,policies,datasets,requests,conventions}/ + outbox/{previews,drafts,reports,suggestions,runs}/
- Manifest includes `partners.produces_for` and `partners.consumes_from` for cross-app discovery
**Accept:** 18 app directories. All manifests valid. `validate_inbox()` passes. Diagrams render as Mermaid.
**Tests:** `tests/test_day_one_apps.py`

### T7: Implement execution lifecycle (preview → approve → execute)
**Status:** DONE (2026-03-01)
**Files:** `src/execution_lifecycle.py` (NEW), `src/recipes/recipe_executor.py`
**What:** Full lifecycle from diagram 14:
1. TRIGGER → INTENT → BUDGET_CHECK (B1-B5 gates)
2. PREVIEW (LLM called ONCE) → PREVIEW_READY
3. User APPROVE/REJECT/TIMEOUT (30s = deny)
4. COOLDOWN (risk-based: 0s/5s/15s/30s)
5. SEAL (chmod 444 outbox file)
6. EXECUTE (CPU replay, no LLM)
7. EVIDENCE_SEAL (hash chain closed)
**Accept:** Full state machine. Evidence entry per step. Budget decremented on completion.
**Tests:** `tests/test_execution_lifecycle.py`
**Depends on:** T5, T9

---

## P1 — Should Ship (Integration)

### T8: Auth proxy for port 9222
**Files:** `src/auth_proxy.py` (NEW)
**What:** 3-layer defense from diagram 09:
- Port 9222 = auth proxy (Bearer sw_sk_ required)
- Port 9225 = hidden Chrome CDP (localhost only)
- Session token exchange for WebSocket clients
**Accept:** Unauthenticated → 401 + redirect. Valid tokens forwarded to :9225. WebSocket upgrade requires token.
**Tests:** `tests/test_auth_proxy.py`

### T9: Budget gate enforcement (B1-B6)
**Files:** `src/budget_gates.py` (NEW)
**What:** Fail-closed budget gates from diagram 13 + diagram 16:
- B1: Policy file present
- B2: Remaining limit > 0
- B3: Target domain in allowed list
- B4: Step-up required? (safety C)
- B5: Evidence mode meets minimum
- B6: Cross-app gate (target installed + in partners + target budget > 0, effective = MIN(source, target))
**Accept:** Any gate failure = BLOCKED. Budget decremented atomically. MIN-cap for delegated budgets.
**Tests:** `tests/test_budget_gates.py`

### T10: PZip capture pipeline
**Files:** `src/capture_pipeline.py` (NEW)
**What:** Capture from diagram 10:
- `page.on('load')` → domain exclusion check → DOM snapshot
- Guest: HTML only (local, no sync)
- Logged-in: HTML + assets + screenshot + Prime Mermaid snapshot
- PZip compress with 100% RTC verification
- Store to `~/.solace/history/{domain}/{ts}_{url}.ripple`
**Accept:** Captures on every page load. Guest vs logged-in paths work. RTC passes.
**Tests:** `tests/test_capture_pipeline.py`
**Depends on:** T8

### T11: Evidence chain integration
**Files:** `src/audit/chain.py`, `src/evidence_upload.py`
**What:** Connect evidence to execution lifecycle:
- Write entry per step (not just at end)
- Two streams: `evidence_chain.jsonl` + `oauth3_audit.jsonl` sharing `run_id`
- Validate chain on retrieval (broken chain surfaced to user)
- E-signing: `SHA256(user_id + timestamp + meaning + record_hash)`
- Cross-app evidence: single chain across multi-app workflows
**Accept:** Chain validated on every read. Break detection alerts user. E-signatures non-detachable.
**Tests:** `tests/test_evidence_chain_integration.py`

### T12: Yinyang rail wiring to execution
**Files:** `src/yinyang/state_bridge.py`, `src/yinyang/bottom_rail.py`
**What:** Connect Yinyang rails to execution lifecycle:
- Top rail shows current FSM state
- Bottom rail auto-expands for PREVIEW_READY, BLOCKED, ERROR
- Approve/reject buttons trigger state transitions
- Never auto-approve (Anti-Clippy law)
**Accept:** FSM state in top rail. Preview in bottom rail. Approve button works.
**Tests:** `tests/test_yinyang_rails.py`
**Depends on:** T7

---

## P1.5 — Cross-App + Delight (Paper 08)

### T13: Cross-app message protocol
**Files:** `src/cross_app/orchestrator.py` (NEW), `src/cross_app/message.py` (NEW)
**What:** Cross-app outbox→inbox delivery from diagram 16:
- Parse outbox/suggestions/*.json for `target_app` field
- Validate target is in manifest `partners.produces_for`
- Budget gate B6 enforcement
- Drop message into target app `inbox/requests/from-{source}-{run_id}.json`
**Accept:** Messages delivered. B6 fail-closed. Evidence chain unbroken across apps.
**Tests:** `tests/test_cross_app.py`
**Depends on:** T5, T9

### T14: Orchestrator app runtime
**Files:** `src/cross_app/orchestrator_runtime.py` (NEW)
**What:** Execute orchestrator-type apps from diagram 16:
- Read manifest `type: orchestrator` + `orchestrates: [app_ids]`
- Trigger child apps in parallel (budget-gated per child)
- Collect outbox results
- LLM ONCE: synthesize into single report
- Write to orchestrator's outbox/reports/
**Accept:** morning-brief orchestrator runs 4 child apps, produces combined report.
**Tests:** `tests/test_orchestrator.py`
**Depends on:** T13, T7

### T15: App conventions/config system
**Files:** `src/inbox_outbox.py` (extend T5)
**What:** Conventions/ subdirectory in inbox:
- `inbox/conventions/config.yaml` — user-editable app settings
- `inbox/conventions/defaults.yaml` — factory defaults
- `inbox/conventions/examples/` — example files
- Config merge: user overrides defaults (deep merge)
- Yinyang can edit config.yaml (not defaults.yaml)
**Accept:** Config loaded and merged before recipe execution. Missing config falls back to defaults.
**Tests:** `tests/test_app_conventions.py`
**Depends on:** T5

### T16: Yinyang delight engine wiring
**Files:** `web/js/yinyang-delight.js` (EXISTS), `web/js/solace.js`, `src/yinyang/bottom_rail.py`
**What:** Wire delight engine into browser:
- Load on all Yinyang pages
- Bottom rail sends warm_token to `YinyangDelight.respond()`
- Key moments trigger `YinyangDelight.celebrate()`
- Jokes/facts served from `data/default/yinyang/*.json` databases
- Holiday detection on page load
- Konami code easter egg
**Accept:** Delight effects fire on warm_token. Jokes/facts in chat. Holidays themed. Konami works.
**Tests:** `tests/test_yinyang_delight.py`
**Depends on:** T12

### T17: Yinyang customer support bridge
**Files:** `src/yinyang/support_bridge.py` (NEW), `web/js/solace.js`
**What:** Yinyang fix vs escalate from diagram 17:
- **CAN FIX:** edit config.yaml, toggle settings, explain app, show history, re-run tasks
- **MUST ESCALATE:** new app requests, bug reports, recipe changes, billing, features
- Escalation: `POST /api/v1/support/ticket` to solaceagi.com
- Status: `GET /api/v1/support/tickets/{id}/status`
**Accept:** Easy requests handled locally. Hard requests escalated with evidence context.
**Tests:** `tests/test_support_bridge.py`
**Depends on:** T12

### T18: Yinyang alert queue
**Files:** `src/yinyang/alert_queue.py` (NEW)
**What:** Alert delivery from solaceagi.com:
- Poll `GET /api/v1/alerts/pending` on user interaction (never background)
- Surface in bottom rail on next chat
- Types: app_update, support_reply, usage_warning, new_app, system, celebration
- Dismiss: `POST /api/v1/alerts/{id}/dismiss`
- Never interrupt. Never auto-expand for low-priority.
**Accept:** Alerts surface naturally. High-priority first. Dismissed properly.
**Tests:** `tests/test_alert_queue.py`
**Depends on:** T12

### T19: Yinyang personality customization
**Files:** `src/yinyang/personality.py` (NEW)
**What:** User customization via files:
- `~/.solace/yinyang/personality.yaml` — tone, humor_level, formality, name, idle_behavior
- `~/.solace/yinyang/favorites.json` — liked jokes/facts (boosted)
- `~/.solace/yinyang/blocked_topics.json` — topics to skip
- Hot-reload on file change
**Accept:** Personality changes reflected immediately. Blocked topics never shown. Favorites boosted.
**Tests:** `tests/test_yinyang_personality.py`

---

## P2 — Polish

### T20: First-run onboarding (start.html)
**Files:** `web/start.html`
**What:** Firebase auth flow → sw_sk_ key → vault → redirect to home.
**Accept:** Full auth flow. Key encrypted. Subsequent visits skip onboarding.

### T21: Settings hot-reload
**Files:** `src/settings_manager.py` (NEW)
**What:** Watch `~/.solace/settings.json` for changes, broadcast to all components.
**Accept:** External edit → reflected in browser within 2s.

### T22: PyInstaller binary compilation
**Files:** `scripts/build_binary.py` (NEW), `solace-browser.spec`
**What:** Single binary: Playwright + Chromium + web/ + default config.
**Accept:** `./solace-browser` starts everything. macOS, Linux, Windows.

### T23: Cloudflare tunnel integration
**Files:** `src/machine/tunnel.py`
**What:** Real cloudflared integration with step-up approval.
**Accept:** `solace tunnel start` creates public URL. Stops on revocation.

---

## Build Order

```
T3 (real API)
T5 (inbox/outbox) ──┐
T6 (app manifests)  ├─→ T7 (execution lifecycle)
T9 (budget gates) ──┘         ↓
T8 (auth proxy)          T12 (Yinyang rails)
T10 (PZip)                    ↓
T11 (evidence)     ┌─── T13 (cross-app) ──→ T14 (orchestrator)
                   ├─── T15 (conventions)
T1-T4 (wire pages) ├─── T16 (delight)
                   ├─── T17 (support bridge)
                   ├─── T18 (alert queue)
                   └─── T19 (personality)
                   T20-T23 (polish)
```

---

## Cross-Project Dependencies

| This Task | Needs From solaceagi | Needs From solace-cli |
|-----------|---------------------|-----------------------|
| T8 (auth proxy) | `GET /api/v1/auth/verify` | `solace auth grant` |
| T10 (PZip) | PZip Stillwater DB | — |
| T17 (support) | `POST /api/v1/support/ticket` | — |
| T18 (alerts) | `GET /api/v1/alerts/pending` | — |
| T20 (onboarding) | Firebase auth + sw_sk_ issuance | — |
| T23 (tunnel) | — | `solace tunnel` command |

---

*23 tasks. P0=7, P1=5, P1.5=7, P2=4. Est. 6,000 LOC + 2,500 test LOC.*
