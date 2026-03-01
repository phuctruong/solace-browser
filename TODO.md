# TODO — Solace Browser (Beta Launch)
# Updated: 2026-03-01 Session G | Auth: 65537
# Phase: Hackathon Sprint
# Private Beta: 2026-03-02 | Real Beta: 2026-03-09 (Tyson's 15th birthday)
# Tests: 4,281 passed | Modules: 12+

---

## Completed

### P0 Core (Session F — Codex + QA)
- [x] T1-T7: app-store, app-detail, server API, settings, inbox/outbox, 18 apps, execution lifecycle
- [x] fetchJson Fallback Ban fix, app icon fix, budget table fix, SHA-256 sidecar

### P1 Real Beta (Session G — Hackathon)
- [x] B4: Auth proxy — 3-layer defense, sw_sk_ tokens, session exchange (62 tests)
- [x] B5: Budget gates — 6 fail-closed gates (B1-B6), atomic decrement, cross-app MIN-cap (56 tests)
- [x] B6: Yinyang rails — FSM state bridge, approve/reject, Anti-Clippy, color-coded (61 tests)
- [x] B7: Cross-app messaging — outbox→inbox, partner validation, orchestrator runtime (24 tests)
- [x] Multi-browser sessions — 4 profiles, port isolation, evidence chains (47 tests)
- [x] Hackathon demo — 7-phase script + family demo page (11 tests)
- [x] Production verified — 16/16 pages 200, 105 API endpoints, auth fail-closed

---

## Remaining for Real Beta (March 9)

### B8: PZip capture pipeline (T10)
**What:** page.on('load') → DOM snapshot → PZip compress → store to history
**Priority:** HIGH — core differentiator

### B9: Evidence chain integration (T11)
**What:** Two-stream evidence (execution + oauth3), cross-app chains, break detection
**Priority:** HIGH — Part 11 compliance

### B10: Delight engine wiring (T16)
**What:** yinyang-delight.js wired, warm_token, celebrate(), holidays, Konami
**Priority:** MEDIUM — user experience

### B11: Support bridge (T17)
**What:** Yinyang CAN FIX vs MUST ESCALATE classification + ticket creation
**Priority:** MEDIUM — support flow

### B12: Alert queue (T18)
**What:** Poll alerts on user interaction, surface in bottom rail
**Priority:** LOW — can wait

---

## Post-Beta
- B13: Personality customization (T19)
- B14: Settings hot-reload (T21)
- B15: PyInstaller binary (T22)
- B16: Cloudflare tunnel (T23)

---

*4,281 tests. 12+ modules. Hackathon complete.*
*For Tyson's 15th birthday (March 9). Endure, Excel, Evolve.*
