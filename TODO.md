# TODO — Solace Browser (Beta Launch)
# Updated: 2026-03-01 | Auth: 65537
# Phase: Beta Launch Prep
# Private Beta: 2026-03-02 | Real Beta: 2026-03-09 (Tyson's 15th birthday)

---

## Status

### Completed (Session F — QA + Codex)
- [x] T1-T7 P0 core — ALL DONE (15/15 tests pass)
  - T1: app-store.html wired to live API
  - T2: app-detail.html wired to live API
  - T3: Real API endpoints in server.py
  - T4: settings.html wired to live API
  - T5: InboxOutboxManager (SHA-256, path traversal guard)
  - T6: 18 day-one app manifests + init script
  - T7: Execution lifecycle FSM (17 states, evidence chain, chmod 444)
- [x] fetchJson Fallback Ban violation fixed (discriminated results)
- [x] App detail icon + budget table fixed
- [x] AGENTS.md v3.0 + CLAUDE.md v3.0

### Known Issues (from Harsh QA)
| ID | Severity | File | Issue | Beta Gate? |
|----|----------|------|-------|------------|
| Q1 | MEDIUM | server.py | Mock dict for non-T3 endpoints | No (returns 404) |
| Q2 | MEDIUM | settings.html | Single-segment path silently lost | No (edge case) |
| Q3 | LOW | app-store.html | Category sections hardcoded | No (cosmetic) |
| Q4 | LOW | app-detail.html | Placeholder loading states | No (cosmetic) |

---

## P0 — Private Beta Gate (March 2)

### B1: First-run smoke test
**What:** `python web/server.py` → browser opens → app store loads → click app → detail page works.
**Accept:** New user sees working app store with 18 apps.

### B2: Start page auth flow
**What:** start.html → Firebase auth → sw_sk_ key → redirect to home.
**Accept:** Login works. Subsequent visits skip onboarding. (T20 partial — already exists)

### B3: Settings persistence
**What:** Settings page save → reload → values persist.
**Accept:** Round-trip works for all 8 setting sections.

---

## P1 — Real Beta Gate (March 9)

### B4: Auth proxy (T8)
**What:** 3-layer defense: port 9222 auth proxy, port 9225 hidden CDP.
**Accept:** Unauthenticated → 401. Valid tokens forwarded.

### B5: Budget gates (T9)
**What:** B1-B6 fail-closed gates for execution.
**Accept:** Any gate failure = BLOCKED. Budget decremented atomically.

### B6: Yinyang rail wiring (T12)
**What:** Top rail = FSM state. Bottom rail = preview/approve/reject.
**Accept:** User can approve/reject from Yinyang chat.

### B7: Cross-app messaging (T13)
**What:** outbox→inbox delivery with B6 gate enforcement.
**Accept:** Messages delivered between partner apps.

---

## P2 — Post-Beta

### B8: PZip capture pipeline (T10)
### B9: Evidence chain integration (T11)
### B10: Orchestrator runtime (T14)
### B11: Delight engine wiring (T16)
### B12: Support bridge (T17)
### B13: Alert queue (T18)
### B14: Personality customization (T19)
### B15: PyInstaller binary (T22)
### B16: Cloudflare tunnel (T23)

---

*Private beta: March 2. Real beta: March 9. For Tyson's 15th birthday.*
*Endure, Excel, Evolve. Carpe Diem. Onward!*
