# NORTHSTAR: solace-browser
# Auth: 65537 | Updated: 2026-03-08

> **Vision:** The AI Browser — Local-First, Evidence-Proven, Safe Autonomy at the OS level

---

## The Single Metric

**Recipes that run autonomously with zero human intervention, producing tamper-evident evidence.**

- Every recipe run = one evidence chain entry (sha256-linked, Part 11 ready)
- Every task = budget-gated, OAuth3-scoped, step-up on irreversible actions
- Replay cost = $0.001 (CPU-only, no LLM)

---

## Three Surfaces (Never Confuse)

| Surface | What | Where |
|---------|------|-------|
| **Yinyang** | Native C++ sidebar (4 tabs) | Follows user on every page — built into Chromium fork |
| **Solace Hub** | Tauri desktop app (~20MB) | System tray, scheduler, OAuth3 dashboard, evidence viewer |
| **Yinyang Server** | Python backend (port 8888) | Serves both surfaces — never port 9222 |

---

## Belt Progression

| Belt | Gate |
|------|------|
| White | Server runs, 534 tests pass, tray menu visible |
| Yellow | All 48 Hub tasks COMPLETE, receipts verified |
| Orange | Chromium fork compiles + sidebar renders native |
| Green | Full recipe replay deterministic at rung 65537 |
| Blue | 3-platform builds ship signed (Linux + macOS + Windows) |
| Black | Distributed via Snap + apt + Homebrew + winget |

**Current belt: Yellow → Orange** (Chromium build in progress)

---

## Absolute Laws

- **Port 8888 ONLY** — 9222 permanently banned, even in comments
- **Solace Hub** — "Companion App" banned everywhere
- **No extensions** — sidebar is native C++ WebUI, not MV3
- **Evidence at event time** — never retroactive
- **Fail-closed budgets** — any gate failure = BLOCKED

---

## Next Milestone

1. Chromium fork compiles + `chrome --version` returns `Solace/1.0.0`
2. Native sidebar renders in fork (Mojo IPC to yinyang_server.py)
3. Sign all 3 platform binaries (eSign cert pending for Windows)
4. Ship to Snap Store + Homebrew tap + winget
