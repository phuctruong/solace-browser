# AGENTS.md — Solace Browser (Codex Executor)
# Version: 3.0 | Updated: 2026-03-01 | Auth: 65537 | Belt: Yellow
# DNA: browser(capture, control, execute, evidence) x 18_apps x yinyang = agent_platform
# Pipeline: papers -> diagrams -> styleguides -> webservices -> tests -> code -> seal

## Project

Solace Browser — OAuth3-native browser automation platform.
4-plane architecture: Capture + Control + Execution + Evidence.
18 day-one apps. Cross-app orchestration. Yinyang = only user interface.

## 10 Uplift Principles (Paper 17)

| # | Principle | Where in This Project |
|---|-----------|----------------------|
| P1 | Gamification | Belt (Yellow), rung targets in papers, GLOW on artifacts |
| P2 | Magic Words | DNA equations in papers, prime channels [2][3][5][7][11][13] |
| P3 | Famous Personas | Load on-demand: Norman + Rams (UI), Lie (CSS), Hickey (arch), Van Edwards (Yinyang EQ) |
| P4 | Skills | prime-safety + prime-coder + styleguide-first (auto-load from .claude/skills/) |
| P5 | Recipes | 81 recipes in data/default/recipes/, hit rate target 70% |
| P6 | Access Tools | Playwright + CDP 4-plane, CLI commands, OAuth3-scoped |
| P7 | Memory | papers/ (9), src/diagrams/ (18), evidence chains, MEMORY.md |
| P8 | Care / Motivation | Yinyang delight engine, warm tokens, EQ personas, Anti-Clippy |
| P9 | Knowledge | 9 papers + 18 diagrams + IF Theory foundation |
| P10 | God is Real | 65537 target rung, evidence-first, humility, sealed store |

Uplift is multiplicative: remove any one principle and the system degrades.

## Persona Loading (On-Demand)

| Persona | Domain | When to Load |
|---------|--------|-------------|
| Don Norman | Design (UX) | UI flows, user-facing components |
| Dieter Rams | Design (simplicity) | Component design, visual hierarchy |
| Hakon Lie | CSS | Stylesheets, design tokens, --sb-* variables |
| Rich Hickey | Architecture | Data flow, state management, system design |
| Vanessa Van Edwards | EQ | Yinyang rail, delight engine, warm tokens |

Personas advise only. prime-safety always overrides persona suggestions.

## Task Source

Read `TODO.md` for current tasks. Execute in order. Mark done when complete.

## Build & Test

```bash
pytest tests/ -v                           # all tests
pytest tests/test_inbox_outbox.py -v       # specific file
ruff check .                               # lint
```

## Coding Rules

### Python (src/)
- Python 3.12+, full type annotations
- `pathlib.Path` always, never `os.path.join`
- Specific exceptions only — NEVER `except Exception: pass`
- NEVER return None/""/{}/[] from exception handlers
- NEVER mock data in production — return 501 for unbuilt
- SHA-256 hashes on all file operations
- f-strings, dataclasses, async/await

### JavaScript (web/js/)
- Vanilla JS, no frameworks, no build step
- IIFE modules, `'use strict'`, JSDoc on public API
- CDN dependencies loaded lazily

### HTML (web/)
- `data-page="name"` on body
- Shared CSS: `/css/site.css` (`--sb-*` tokens)
- No inline styles. No inline scripts.

## Architecture Laws (ABSOLUTE)

1. LLM called ONCE at preview — execution = deterministic CPU replay
2. Fail-closed — any gate failure = BLOCKED
3. Evidence at event time — per step, never retroactively
4. OAuth3 on every request — Bearer sw_sk_ required
5. Never auto-approve — Anti-Clippy law
6. Apps communicate through files — outbox→inbox only
7. diagrams/ required in every app — AI reads to understand
8. Budget gates B1-B6 fail-closed
9. No vendor API keys — web-native automation
10. Yinyang is the only interface

## Key Files

| Path | What |
|------|------|
| `TODO.md` | Task backlog (start here) |
| `papers/00-index.md` | 9 papers (01-08 + 00-index) |
| `src/diagrams/README.md` | 19 diagrams (01-18 + README) |
| `src/api/openapi.yaml` | OpenAPI 3.1.0 spec |
| `web/server.py` | Web server |
| `web/js/yinyang-delight.js` | Delight engine |
| `data/default/yinyang/` | Jokes, facts, smalltalk DBs |
| `data/default/recipes/` | 81 recipes |
| `src/companion/apps.py` | CompanionApp + AppRegistry |

## Execution Protocol

1. Read TODO.md → find next pending task
2. Read referenced papers + diagrams
3. Write failing test (RED)
4. Implement to pass (GREEN)
5. `pytest tests/ -v` — full suite
6. No regressions → mark done

## NEVER Do

- `except Exception: pass` or `except Exception: return None`
- Mock data in production
- Auto-approve any action
- Skip OAuth3 checks
- Write to inbox/ (AI reads inbox, writes outbox)
- Call LLM during execution
- Commit secrets or API keys
