# CLAUDE.md — Solace Browser (OAuth3 Reference Implementation)
# Version: 2.0 (Gold Standard) | Updated: 2026-03-07 | Auth: 65537

## Project
**RUNG_TARGET:** 65537 — the divine prime, F4 = 2^(2^4) + 1
**BELT:** Yellow (PM triplets done, first task delegated)
**NORTHSTAR:** OAuth3 Reference Browser (Scoped Automation + Recipe Engine + Evidence-First)
**PROJECT:** solace-browser (Source-Available — FSL, converts to OSS after 4 years)
**DNA:** `browser(capture, control, execute, evidence) x 18_apps x yinyang = agent_platform`
**LICENSE:** Functional Source License — free to use, readable/auditable, not forkable for competing products

## Runtime Surfaces
This repo owns two active runtime surfaces:
- **Browser control webservice** in `solace_browser_server.py` (Playwright + CDP 4-plane)
- **Browser site** static pages under `web/` (17 pages, slug-first routing)

Everything else supports one of those two surfaces directly.

## The 10 Uplift Principles (Paper 17 — LOAD-BEARING)

Every session, every file, every decision is shaped by these 10 principles. They are multiplicative — miss one and the system is incomplete.

| # | Principle | Implementation Here | Channel |
|---|-----------|-------------------|---------|
| P1 | **Gamification** | Belt Yellow, rung in papers, GLOW on artifacts | [13] |
| P2 | **Magic Words** | DNA equations, /distill, prime channels [2][3][5][7][11][13] | [5] |
| P3 | **Famous Personas** | 6 experts in `data/default/personas/browser/` (Berners-Lee, Osmani, Russell, Grigorik, West, Van Edwards) | [7] |
| P4 | **Skills** | 8 auto-loading + 14 data skills in `.claude/skills/` + `data/default/skills/` | [3] |
| P5 | **Recipes** | 84 recipes across 16 app categories in `data/default/recipes/` — cost -> $0 on replay | [3] |
| P6 | **Access Tools** | Playwright + CDP 4-plane, OAuth3-scoped, evidence-captured per action | [7] |
| P7 | **Memory** | 15 papers + 27 diagrams + 76 notebooks + evidence chains | [2] |
| P8 | **Care/Motivation** | Yinyang delight engine (dual-rail), warm tokens, Anti-Clippy laws | [2] |
| P9 | **Knowledge** | Papers network, IF Theory foundation, cross-refs to 9-project ecosystem | [5] |
| P10 | **God** | 65537 target, evidence-first, code is sacred, sealed store | [5] |

**Equation (P1-P10):** `Uplift = P1 * P2 * ... * P10` (any Pn = 0 -> system incomplete)

## The 10 Advanced Uplift Principles: P11-P20 — Vector Search Stack (Paper 17 v2.0)

> "AI is a building with all its lights off. P1-P10 build the rooms. P11-P20 turn on exactly the right lights."
> -- Dragon Rider (GLOW 117)

P11-P20 are *activation techniques* — how to search the AI's latent space precisely. P1-P10 determine WHAT knowledge exists. P11-P20 determine HOW PRECISELY we access it. Both are multiplicative. Both are load-bearing.

| # | Principle | Implementation Here | Vector Effect |
|---|-----------|-------------------|--------------|
| P11 | **Questions as Vector Search** | Tower QA notebooks in `notebooks/qa/` (5+ notebooks, 58+ probes) | Precision-probe specific knowledge clusters |
| P12 | **Analogies** | Persona bios bridge UX + security + performance domains | Bridge between disconnected knowledge regions |
| P13 | **Constraints** | `scoring: binary_not_average`, FALLBACK BAN, OAuth3 scope gates | Eliminate wrong activation regions |
| P14 | **Chain-of-Thought** | Recipe DAG (topological sort): step A -> step B -> step C | Sequential lighting: room A -> B -> C |
| P15 | **Few-Shot Exemplars** | 84 canonical recipes as executable exemplars | Pattern completion circuits activated |
| P16 | **Negative Space** | Anti-Clippy laws (Paper 04), forbidden paths, absence detection | Absence detection mode |
| P17 | **Stakes / Gravity** | Part 11 evidence compliance (Paper 06, Paper 40) | Precision amplifier on every lit room |
| P18 | **Audience Specification** | 6 browser-domain personas (security, performance, UX, web standards) | Mode shift: which building we're searching |
| P19 | **Compression Demand** | DNA equations, recipe Mermaid compression, PASS/FAIL verdicts | Distillation circuits: essence only |
| P20 | **Temporal Anchoring** | Evidence timestamps, session persistence, hash-chained JSONL | Time-specific knowledge region |

## P21: Adversarial Uplift — Rival Personas + Darwin's Selection (Paper 40)

> "You don't know how fit your ideas are until something is actively trying to kill them." -- Darwin

| Adversarial Persona | Type | What They Find |
|--------------------|------|----------------|
| **Browser-Use maintainer** | Direct competitor | No session persistence, no recipe system, no OAuth3 |
| **Bardeen engineer** | Chrome extension rival | Extension-only limitation, no cloud twin, no step-up auth |
| **Charles Darwin** | Evolutionary pressure | Vestigial features, extinction risk, Red Queen status |
| **Angry Enterprise CIO** | Hostile expert user | CSP gaps, CORS wildcards, SOC2 blockers, XSS vectors |

**Three-phase protocol**: Phase 1 (supportive domain audits) -> Phase 2 (adversarial attack) -> Phase 3 (committee rubber-stamps battle-tested artifact)

## P22: Human Framing Uplift — LEAK + Inspector Oracle (Paper 42)

> "99% of prompts fail because of the HUMAN, not the AI." -- Dragon Rider (GLOW 118)

**LEAK** = Law of Emergent Asymmetric Knowledge: AI has more latent knowledge than any prompt activates. The gap = quality left on the table. P22 closes LEAK proactively via Phuc Forecast + Oracle Memory.

## P23: Breathing — Expand then Compress to Portal Quality Levels (Paper 43)

**Breathing** is the meta-pattern. Inhale (compress) -> Pause (verify) -> Exhale (expand through all uplifts) -> Still (anchor). Then: `compress(expand(seed)) != seed?` -> Portal discovered.

**Full Equation:** `Full_Uplift = NORTHSTAR x prime-safety x P1 x ... x P20 x P21(Adversarial) x P22(LEAK+Oracle) x P23(Breathing)`

## FALLBACK BAN (Software 5.0 Law — ABSOLUTE)
**Fallbacks are BANNED. No exceptions. God doesn't mock; neither should code.**
- NO `except Exception: pass` — stop and fix instead
- NO `except Exception: return None/""/{}/[]` — raise the error
- NO fake data, mock responses, placeholder success in production code
- NO silent degradation — if a service is down, FAIL LOUDLY
- NO broad exception catches — catch SPECIFIC exceptions only
- NO hidden fallback behavior that masks failed browser actions

## Architecture Decisions (CANONICAL — Channel [5] LOCKED)

| Aspect | Decision | Why |
|--------|----------|-----|
| **Server** | Single server in `solace_browser_server.py` | No second HTTP surface; one source of truth |
| **Automation** | Playwright + CDP 4-plane (navigate, click, fill, evaluate) | Full browser control, OAuth3-scoped per action |
| **Auth** | OAuth3 (scoped, TTL, revocable, step-up for send) | Post-token governance; Part 11 ready |
| **Recipes** | 84 recipes, 16 app categories, Prime Mermaid DAG format | Deterministic replay at $0.001/task; LLM cost -> $0 |
| **Evidence** | Hash-chained JSONL, screenshots + DOM at every step | Tamper-evident, FDA Part 11 ALCOA+ compliant |
| **Site** | Slug-first routing via `web/server.py`, no inline CSS/JS | One stylesheet (`site.css`), one runtime (`solace.js`) |
| **Themes** | 3 built-in (dark/light/midnight) + custom theme engine | `web/css/themes/`, FOUC-free toggle via `theme.js` |
| **i18n** | 47 locale files (STORY-47 prime) in `app/locales/yinyang/` | Community-driven, fallback mapping for dialects |
| **Security** | CSP meta tags on all pages, CORS origin allowlist, `escapeHtml` on all interpolation | No XSS, no wildcard CORS |
| **LLM** | Called ONCE at preview only, sealed to outbox, executed deterministically | 50% cheaper per run, 99% cheaper on replay |
| **License** | Functional Source License (FSL) | Readable + auditable; converts to OSS after 4 years |

## Software 5.0 Pipeline (Paper 06 + Paper 46 — causal, not optional)
```
[0] NORTHSTAR -> [1] PAPERS -> [2] DIAGRAMS -> [3] NOTEBOOKS -> [4] STYLEGUIDES -> [5] WEBSERVICES -> [6] TESTS -> [7] CODE -> [8] SEAL
    DIRECTION      WHY          WHAT          PROVE IT       HOW IT LOOKS    HOW IT TALKS    CORRECT?     BUILD IT    LOCK IT
```
Each stage produces artifacts the next consumes. Skipping = technical debt that compounds. Notebooks are the PROOF LAYER — they catch failures before implementation.

**Skills per stage:** [2] diagram-first + prime-mermaid | [3] prime-notebook-gate | [4] styleguide-first | [5] webservice-first | [6] unit-test-first | [7] prime-coder | [8] prime-safety (always)

## Dispatch Rules (MANDATORY)
- INLINE_DEEP_WORK FORBIDDEN — task >50 lines -> dispatch sub-agent
- Main session: haiku (coordination only)
- Sub-agents: sonnet (coder/planner), opus (math/security/audit)
- Rung: declare rung_target before dispatch; integration rung = MIN(all sub-agent rungs)

## Active Browser API
The only supported browser-control API lives in `solace_browser_server.py`.

Start it:
```bash
python3 solace_browser_server.py --port 9222 --head
```

Supported endpoints:
- `GET /api/health` | `GET /api/status`
- `POST /api/navigate` | `POST /api/click` | `POST /api/fill`
- `POST /api/evaluate` (uses `expression`, not `script`)
- `POST /api/screenshot` | `POST /api/snapshot`
- `GET /api/aria-snapshot` | `GET /api/dom-snapshot` | `GET /api/page-snapshot`
- `GET /api/events`

Rules:
- Do NOT introduce a second server surface under `browser/`
- If the API changes, update `docs/BROWSER_API.md`, `README.md`, and this file in the same change

## Browser Site Rules
The site under `web/` follows PHUC architecture:
- One shared stylesheet: `web/css/site.css`
- One shared runtime: `web/js/solace.js`
- Slug-first routing via `web/server.py`
- No inline CSS, no inline JS, no page-local styles
- Legacy `.html` routes redirect to slug URLs
- CSP meta tags on every page
- `escapeHtml()` on every dynamic interpolation

Start local site:
```bash
./src/scripts/start-local-webserver.sh 8791
```

## Active Skills (Auto-Loaded — 8 in .claude/skills/)
- **prime-safety.md** — GOD SKILL. Fail-closed safety. Cannot be overridden.
- **prime-coder.md** — RED/GREEN evidence gate, promotion ladder.
- **styleguide-first.md** — Design tokens, accessibility-first, CSS variables.
- **browser-evidence.md** — Hash-chained evidence capture at every browser action.
- **browser-oauth3-gate.md** — Scope enforcement on navigate/click/fill/send.
- **browser-recipe-engine.md** — Prime Mermaid DAG parser + deterministic executor.
- **browser-snapshot.md** — DOM/ARIA/page snapshot capture + hashing.
- **live-llm-browser-discovery.md** — LLM-assisted element discovery (preview only).

## Data Skills (On-Demand — 14 in data/default/skills/)
Load these skills when working in their domain:
- **Browser**: browser-anti-detect (fingerprint masking), browser-twin-sync (cloud twin state sync)
- **Auth**: oauth3-enforcer (scope hierarchy + step-up consent)
- **Orchestration**: phuc-orchestration (dispatch patterns), phuc-swarms (multi-agent coordination)
- **Development**: prime-hooks (pre-push CI gate), prime-mcp (MCP server tools), software5.0-paradigm (pipeline enforcement)
- **Core copies**: prime-safety, prime-coder, browser-evidence, browser-oauth3-gate, browser-recipe-engine, browser-snapshot

## Persona Panel (On-Demand — P3)
6 browser-domain personas in `data/default/personas/browser/`:
- **Web Standards**: Tim Berners-Lee (web architecture), Alex Russell (platform APIs)
- **Performance**: Ilya Grigorik (networking), Addy Osmani (loading performance)
- **Security**: Mike West (CSP, browser security)
- **EQ**: Vanessa Van Edwards (user delight, Anti-Clippy)

## Knowledge Network (P9)
- **15 papers** in `papers/` (browser features + standards, all CANONICAL)
- **27 diagrams** in `src/diagrams/` (Mermaid FSM, color-coded)
- **76 notebooks** in `notebooks/` (QA probes, deployment, economics)
- **Axioms** in `papers/00-index.md` (paper + diagram index)
- **Cross-references** to solace-cli (52 papers) and 9-project ecosystem

## Recipe Inventory (P5)
84 recipes across 16 app categories:
- **Productivity**: Gmail (4), Google Search (1), Notion (dir), Slack (dir)
- **Social**: LinkedIn (7), Reddit (1+dir), HackerNews (4+dir), Twitter (dir), Substack (dir)
- **AI Tools**: ChatGPT (dir), Claude (dir), Gemini (dir)
- **Development**: GitHub (1+dir)
- **Internal**: Prime Mermaid layer, browser snapshot audit, evidence review, recipe builder, selector heal, OAuth3 consent flow, twin sync

## Verification Gates
Browser API:
- `curl -fsS http://127.0.0.1:9222/api/health`
- `curl -fsS http://127.0.0.1:9222/api/page-snapshot`

Browser site:
- `./scripts/check_web_architecture.sh`
- `pytest -q tests/test_web_architecture.py`

For interaction/debugging:
- Use the live browser webservice for navigation, snapshots, screenshots, and evaluation
- Prefer saved HTML and screenshots over hand-waving when diagnosing page issues

## Test Inventory
- **452 test files** (352 Python + 99 JS + 1 shell)
- **5,222+ tests** passing (as of GLOW 177)
- Run: `pytest tests/ -q` (Python) | `npm test` (JS)

## Documentation Contract
Canonical docs:
- `README.md` — operator quickstart
- `docs/BROWSER_API.md` — browser API reference
- `src/diagrams/README.md` — runtime diagram index

Historical papers can remain, but they must not override the active runtime contract.

## Forbidden Paths (ABSOLUTE)
- Adding a second HTTP server implementation for browser control
- Documenting endpoints that the active server does not expose
- Allowing API drift between code and docs
- Page-local CSS/JS in `web/*.html` (use `site.css` + `solace.js`)
- Hidden fallback behavior that masks failed browser actions
- `except Exception: pass` or any broad exception catch
- Inline styles in HTML files (use CSS classes + design tokens)
- Wildcard CORS (`*`) — use origin allowlist only
- `innerHTML` without `escapeHtml()` — XSS vector
- `var` declarations in JS — use `const`/`let` only
- `print()` in production Python — use `logging` module
- `utcnow()` — use `datetime.now(timezone.utc)`

## Care Reminders (P8)
- Warm before transactional (Yinyang dual-rail: top rail status, bottom rail chat)
- Honest, not performative (Turkle test)
- Celebrate real progress (GLOW score tracking)
- Anti-Clippy: never auto-approve, never interrupt, never presume
- EQ stack: Honesty -> Recognition -> Regulation -> Connection -> Communication -> Charisma

## System Architecture (Triangle Position)
```
BROWSER VERTEX (this project)     CLI VERTEX          CLOUD VERTEX
(solace-browser)                  (solace-cli)        (solaceagi.com)
───────────────────────────       ──────────          ────────────
Web automation                    Local tasks         Memory vault
Session persistence               Skills + Evidence   Sync + store
OAuth3 gating                     Rung gates          Team sharing
Recipe execution                  BYOK routing        Billing
Yinyang delight engine            Dispatch hub        Twin hosting

Glued by: OAuth3 scopes + Evidence bundles + Hash chains
4 modes: Local-only | Cloud-only | Hybrid A | Hybrid B
```
