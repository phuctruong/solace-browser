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
| MRR (blended belt mix) | ~$5K | ~$18.3K | ~$91K | ~$457K |

**Belt-blended MRR at 1,000 users** (example mix):
$8×300 + $48×200 + $88×50 + $188×10 = $2,400 + $9,600 + $4,400 + $1,880 = **$18,280/mo**

**Why recipe hit rate?** At 70% hit, COGS = $5.75/user/month (70%+ gross margin).
Without recipes: $12.75 COGS (33% margin — not fundable). Recipes ARE the economic moat.
"I fear not the man who has practiced 10,000 kicks once, but I fear the man who has practiced one kick 10,000 times." — Bruce Lee. This is recipe replay.

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

### Differentiation (Belt Tiers via solaceagi.com)

| Belt | Price | What you get | Browsing History |
|------|-------|-------------|-----------------|
| White (Free) | $0 | All UI, all 6 LinkedIn recipes, local execution, BYOK | 100 snapshots, 7-day retention |
| Yellow (Student) | $8/mo | Managed LLM (no API key), 30-day evidence, 20 tokens, replay priority | 1,000 snapshots, 30-day retention |
| Orange (Warrior) | $48/mo | Cloud twin (24/7), OAuth3 vault, 90-day evidence, production skills (rung 65537) | 10,000 snapshots, 90-day retention |
| Green (Master) | $88/user/mo | Team tokens, SOC2 audit, private Stillwater Store, SAML SSO | Unlimited snapshots, 1-year retention |
| Black (Grandmaster) | $188+/mo | Dedicated nodes, on-prem, custom governance | Unlimited snapshots, forever retention |

**Near-unlimited browsing history**: Full HTML snapshots, not screenshots. See exactly what your AI did.
PZip compression makes this affordable: 100 LinkedIn pages stored as ~5 pages worth of data.
"See exactly what your AI did — actual pages, not screenshots."

Recipe FORMAT is open. Recipe LIBRARY quality + cloud execution + belt progression + browsing history = the paid moat.
"This isn't SaaS — it's a dojo."

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

## PZip-Powered Browsing History (Secret Sauce Moat #7)

PZip (`/home/phuc/projects/pzip/`) enables a browsing history feature no competitor can match economically.

```
PZip + Global Asset Registry (GAR) — 3 layers of dedup:
  Layer 1: Global assets — React, jQuery, Bootstrap, fonts = stored ONCE for ALL users
  Layer 2: Domain assets — site CSS, site JS, logos = stored ONCE per domain
  Layer 3: User deltas — only unique text/form data = ~11KB per page (vs ~730KB raw)

Why this achieves 45:1 to 80:1 effective compression:
  - Typical page = 80% shared assets + 15% template + 5% unique content
  - With GAR: ~11KB stored per page (asset refs + delta + unique)
  - Static HTML (no JS): even smaller (~3-5KB delta)
  - Same JS/CSS libraries cached GLOBALLY (React 150KB = stored once, period)
  - Same images/logos/fonts cached per DOMAIN
  - Form fills captured with before/after state (highlighted yellow)
  - Kanban-style UI → users see agent actions as visual card timeline

At scale (the math that wins):
  10K users × 1000 pages = 7.3TB raw → 160GB with GAR = $3.20/mo
  That's $0.00032/user/month for full browsing history
  Competitors: $146/mo for same data without PZip (if they store it at all)

What this enables (no competitor offers this):
  - "See exactly what your AI did — actual pages, not screenshots"
  - Replay exactly what the agent did step-by-step
  - Inspect form fills: see what the agent typed before/after
  - Full-text search across your entire browsing history
  - Kanban view: session → page cards → click → full HTML render (iframe)
```

**Snapshot schema** (every page visit captures):
```json
{
  "snapshot_id": "sha256(url + timestamp + html_hash)",
  "url": "https://linkedin.com/feed",
  "title": "LinkedIn Feed",
  "timestamp": "ISO8601",
  "html": "<!DOCTYPE html>...",
  "form_state": {"input#search": "software engineer"},
  "form_changes": [{"selector": "input#search", "before": "", "after": "software engineer"}],
  "viewport": {"width": 1920, "height": 1080},
  "scroll_position": {"x": 0, "y": 450}
}
```

**Build prompt**: See `ROADMAP.md` — HTML Snapshot Capture build prompt (Phase 2 / PZip integration)

## What Aligns with This Northstar

- Phase 0 validation tests (run before any Electron code)
- Recipe system: every successful task creates/improves a recipe
- Anti-detection: weekly fingerprint-check against BotD/CreepJS
- Evidence-based execution: Stillwater verification bundles per task
- Zero-knowledge sync: user's master password never touches server
- Phuc swarms for all implementation (coder/planner/skeptic typed agents)
- **PZip HTML snapshots**: full page capture + form fill recording + cross-file compression

## What Does NOT Align

- Building Chromium fork (use Electron)
- Mobile-first (desktop first)
- Scraping/aggregating data (personal task delegation only)
- Running browser automation without sealed wish contract (EXECUTE_WITHOUT_SEALED_WISH)
- Claiming task success without Stillwater evidence bundle
- Storing screenshots instead of HTML snapshots (lossy → can't inspect → can't replay)
- Storing uncompressed HTML (always PZip before storage)

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
