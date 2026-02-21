# NORTHSTAR: Phuc_Forecast — SolaceBrowser

> "Log in once. Solace handles the rest — checking your email, applying to jobs, and monitoring your feeds while you sleep."

## The Vision: Twin Browser

SolaceBrowser is **not just another AI browser sidebar**. It is a twin architecture:

```
LOCAL  → Electron browser wrapping persistent_browser_server.py
         User browses normally + AI sidebar for current page
         One-click session sync (AES-256-GCM zero-knowledge encryption)

CLOUD  → Same persistent_browser_server.py running headless on solaceagi.com
         Your sessions + fingerprint, running tasks 24/7 while you sleep
         Recipe system: 70% cache hit → $0.01/task vs $0.20 for competitors
```

**Five moats no competitor has simultaneously:**
1. Deep anti-detection (canvas/WebGL/JA3/Bezier mouse/inertia scroll)
2. Recipe system (externalized reasoning → 70% cache hit → 3x cheaper COGS)
3. Twin architecture (local browsing + cloud AGI delegation)
4. Fingerprint sync (cloud browser identical to user's real browser)
5. Stillwater verification (evidence-based execution, not just screenshots)

## North Star Metric

**Recipe Hit Rate + Task Success Rate**

| Metric | 3mo | 6mo | 12mo | 24mo |
|--------|-----|-----|------|------|
| Recipe hit rate | 50% | 70% | 80% | 90% |
| Cloud task success rate | 70% | 80% | 90% | 95% |
| Paying users | 100 | 1,000 | 5,000 | 25,000 |
| MRR | $1.9K | $19K | $95K | $475K |

**Why recipe hit rate?** At 70% hit, COGS = $5.75/user/month (70% gross margin).
Without recipes: $12.75 COGS (33% margin). Recipes ARE the economic moat.

## Current Phase: Phase 0 — Validate Core Premise

Before writing any Electron code, validate:
- [ ] `storage_state` transfers between machines for 8+ of top 10 sites
- [ ] Sessions survive 7+ days headless for 5+ sites
- [ ] Fingerprint sync passes BotD/CreepJS (cloud looks like local)
- [ ] Headless Docker execution works end-to-end for "check LinkedIn messages"

**Stop if:** session transfer fails for 5+ sites (fundamental premise broken).

## Phase 1: Electron MVP (Weeks 2-4, ~3K lines new code)

| Layer | Build | Reuse |
|-------|-------|-------|
| Electron shell + home screen | BUILD (~1K lines) | — |
| Session encrypt/upload | BUILD (~200 lines) | `/save-session` output |
| Cloud task queue | BUILD (thin) | solaceagi FastAPI |
| Everything else | — | REUSE (40+ API endpoints) |

**MVP demo:** Login to LinkedIn in browser → cloud reads your messages → results appear.

## Model Strategy (Intelligence Layer)

Per IDEAS.md architecture:

| Model | Role |
|-------|------|
| **haiku** | Main session coordinator; task execution in cloud (recipe replays) |
| **sonnet** | Task planning; new recipe creation; coder swarm |
| **opus** | Security audit; zero-knowledge encryption review |

Cloud intelligence layer uses Claude API:
- Sonnet for planning new tasks
- Haiku for executing cached recipes (100x cheaper)

## What Aligns with This Northstar

- Phase 0 validation tests (run before any Electron code)
- Recipe system: every successful task creates/improves a recipe
- Anti-detection: weekly fingerprint-check against BotD/CreepJS
- Evidence-based execution: Stillwater verification bundles per task
- Zero-knowledge sync: user's master password never touches server
- Phuc swarms for all implementation (coder/planner/skeptic typed agents)

## What Does NOT Align

- Building Chromium fork (use Electron)
- Mobile-first (desktop first)
- Scraping/aggregating data (personal task delegation only)
- Running browser automation without sealed wish contract (EXECUTE_WITHOUT_SEALED_WISH)
- Claiming task success without Stillwater evidence bundle

## Key Risks to Monitor

1. Session expiry: Google/LinkedIn expire sessions — monitor weekly
2. Anti-detection degradation: sites update detection — weekly BotD check
3. Chrome Auto Browse: can't do cloud delegation, can't work while sleeping
4. Legal: act as user's authorized agent; never aggregate data

## See Also

- `IDEAS.md` — full 65537-expert analysis (DREAM→FORECAST→DECIDE→ACT→VERIFY)
- `CLAUDE.md` — prime-wishes + phuc-cleanup loaded
- `ripples/project.md` — project constraints
- `skills/prime-browser.md` — browser agent skill (703 lines)
- `recipes/*.recipe.json` — cached automation recipes
- `primewiki/*.primewiki.json` — site knowledge graphs
