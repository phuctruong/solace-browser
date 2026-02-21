# NORTHSTAR: Phuc_Forecast — SolaceBrowser

> *"Be water, my friend."* — Bruce Lee

## The Reframe: From Tool to Protocol

**Before OAuth3**: SolaceBrowser = browser automation tool (competing on features)
**After OAuth3**: SolaceBrowser = reference implementation of AI delegation standard

```
OAuth3 Spec (OPEN STANDARD)
    │
    ├── solace-browser = reference implementation (OSS) ← THIS PROJECT
    ├── stillwater = verification + governance layer (OSS)
    ├── solace-cli = terminal-native surface (OSS)
    └── solaceagi.com = hosted compliance-grade execution (PAID)

Standard → Ecosystem → Revenue
```

**Why this wins**: Token-revenue vendors (OpenAI, Anthropic, Google) are structurally
incentivized to keep token usage HIGH. OAuth3 reduces token usage to near-zero via
recipe reuse. They CANNOT implement it without cannibalizing their revenue. We can.

**The moat**: First open standard for AI agency delegation. Anyone who implements it
validates our position. Anyone who doesn't is non-compliant.

---

## Software 5.0 Context

SolaceBrowser is **Software 5.0 for personal web automation**:
- Natural language intent ("check my LinkedIn DMs") → **source code**
- Playwright browser agent + recipe engine → **runtime**
- Captured recipes + evidence bundles → **compiled output**
- Stillwater verification (recipe hit rate + task success) → **CI/CD**

The North Star is not the features. The North Star is the **recipe hit rate** — because at 70% hit rate, COGS = $5.75/user/month. Below 70%, the economics break. Recipes ARE the moat. Recipes ARE the intelligence layer persisted outside the LLM session.

> *"Log in once. Solace handles the rest — checking your email, applying to jobs, and monitoring your feeds while you sleep."*

---

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

**Six moats (all competitors have 0–2):**
1. **Recipe system** → 70% cache hit → 3x cheaper COGS
2. **PrimeWiki** → domain-aware navigation (not generic DOM scraping)
3. **Twin architecture** → local browsing + cloud delegation
4. **Anti-detection** → Bezier mouse, fingerprint sync, char-by-char typing
5. **Stillwater verification** → evidence bundle per task (not just screenshots)
6. **OAuth3 protocol** → scoped consent, revocation, audit trail, step-up auth ← UNCOPYABLE

**Why moat #6 is uncopyable**: OpenAI building OAuth3 = OpenAI cannibalizing its token revenue.
We have structural freedom to do what they can't.

**Competitive gaps (Feb 2026)**:
| Competitor | Missing |
|-----------|---------|
| OpenClaw | No evidence trail; no consent model; no revocation |
| Browser-Use | No session persistence; no recipe system; no OAuth3 |
| Bardeen | Chrome extension only; no cloud twin; no step-up auth |
| Vercel agent-browser | Cloud-only; no local twin; no recipe library; no OAuth3 |

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

## Phase 1: MVP UI + LinkedIn Recipes (Current Sprint)

Build spec: `specs/BUILD-SPEC.md` | QA checklist: `specs/QA-CHECKLIST.md`

| Feature | What | Rung |
|---------|------|------|
| Home Page | Custom start page — 6 supported sites with session status + quick actions | 641 |
| Activity View | Post-login view — twin orchestrator logs, PrimeWiki, Mermaid state diagram, HTML viewer | 641 |
| Kanban UI | Recipe task queue (Queue → Running → Done → Failed) | 641 |
| LinkedIn Recipes | 6 MVP recipes: discover-posts, create-post, edit-post, delete-post, react, comment | 641 |

**UI server:** port 9223 (separate from API server at 9222)
**Tech:** Vanilla HTML/CSS/JS, no build step, served by Python stdlib HTTP server

### Differentiation (Free vs solaceagi.com)

| Tier | What you get |
|------|-------------|
| **Free (OSS client)** | All UI, all 6 LinkedIn recipes, local execution |
| **solaceagi.com** | AI-enhanced recipe quality, cloud execution (24/7), scheduled tasks, session vault, 90-day history |

Recipe FORMAT is open. Recipe LIBRARY quality + cloud execution = the paid moat.

## Phase 2: Electron Shell (After Phase 1 validated)

| Layer | Build | Reuse |
|-------|-------|-------|
| Electron shell wrapping Phase 1 UI | BUILD (~1K lines) | Phase 1 HTML/JS |
| Session encrypt/upload | BUILD (~200 lines) | `/save-session` output |
| Cloud task queue | BUILD (thin) | solaceagi FastAPI |
| Everything else | — | REUSE (40+ API endpoints) |

**MVP demo:** Login to LinkedIn in browser → cloud reads your messages → results appear in Activity View.

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
- `specs/BUILD-SPEC.md` — Phase 1 build spec (4 features + 6 LinkedIn recipes)
- `specs/QA-CHECKLIST.md` — QA verification checklist (used by auditor session)
- `CLAUDE.md` — prime-wishes + phuc-cleanup loaded
- `ripples/project.md` — project constraints
- `skills/prime-browser.md` — browser agent skill
- `recipes/*.recipe.json` — cached automation recipes
- `primewiki/*.primewiki.json` — site knowledge graphs
