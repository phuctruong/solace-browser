# NORTHSTAR: Phuc_Forecast — Solace Browser v1.0
# OAuth3 Reference Implementation + PM Triplets + Recipe Engine
# Software 5.0 Edition | Updated: 2026-02-25

> "The best way to understand something is to build it." — Richard Feynman
> "OAuth3 is not a feature—it's the law of the dojo." — Phuc Truong

---

## THE VISION

**Solace Browser = The Open Standard for Delegated AI Agency**

```
Layer 1: Playwright/Selenium (browser automation)
         ↓ (execution surface)

Layer 2: OAuth3 Scope Gates (authorization)
         Every click requires explicit scope
         Every action is revocable
         ↓

Layer 3: Recipe Engine (deterministic execution)
         Prime Mermaid recipes
         Reproducible, auditable, cached
         ↓

Layer 4: PM Triplets (context model)
         User model + Task model + Context model
         Enables composition (output of A = input to B)
         ↓

solace-browser = Proving ground for OAuth3 + browser automation
                 = Reference implementation for solaceagi.com
                 = Community-driven recipe library
```

**Why This Matters:**
- **OAuth3 is uncopyable:** Token vendors (OpenAI, Anthropic) cannot implement it—cannibalizes revenue
- **Browser automation is commoditized:** Selenium/Playwright exist, but none have OAuth3 + auditing
- **Recipes compound:** Each recipe submission makes hit rate higher → margins better → attracts more users
- **Open source builds trust:** No black box. Users see exactly what the agent does.

---

## NORTH STAR METRIC: Recipe Hit Rate

### The Question
**"How do we build a browser automation platform where the majority of tasks complete without calling an LLM?"**

### The Answer: Recipe Flywheel
```
Phase 1: Build recipe engine (Prime Mermaid parser)
         Hit rate: 0% (no recipes)

Phase 2: Ship 10 hand-written recipes (email, LinkedIn, etc.)
         Hit rate: 5% (rare perfect match)

Phase 3: Community submission opens (Stillwater Store integration)
         + Recipe caching + hit rate tracking
         Hit rate: 20% (some tasks match exactly)

Phase 4: Recipe refinement (ML feedback loop)
         + Reward high-hit recipes
         + Prune low-hit recipes
         Hit rate: 50%

Phase 5: Specialization (per-domain recipe training)
         + Gmail recipe ≠ LinkedIn recipe
         + Fine-tuned for specific workflows
         Hit rate: 70%+

Economics at 70% hit rate:
  Recipe task cost: $0.001 (Haiku at scale)
  LLM task cost:    $0.01 (Sonnet, medium)
  If 70% recipes:   $0.007/task avg → 30% of cold-call cost
```

---

## STRATEGIC METRICS

| Metric | Phase 1 | Phase 4 | Phase 6 |
|--------|---------|---------|---------|
| **Browser recipes shipped** | 0 | 10 | 50+ |
| **Recipe hit rate** | 0% | 30% | 70%+ |
| **GitHub stars** | 0 | 500 | 5,000 |
| **Community recipe submissions** | 0 | 5/mo | 50/mo |
| **Platforms supported** | 0 | 1-2 | 10+ |
| **Rung 65537 recipes** | 0% | 20% | 80% |

---

## CORE FEATURES

### 1. OAuth3 Reference Implementation
```
What it proves:
  ✓ OAuth3 spec is implementable (not vaporware)
  ✓ Token vendors CAN'T do it (breaks their model)
  ✓ Users WANT it (scoped, revocable, auditable)

Scope gates:
  browser.read  → inspect + read pages only
  browser.click → click elements
  browser.fill  → fill forms + type text
  browser.send  → send emails/messages (requires step-up)

Evidence:
  Every action logged (JSONL)
  Hash-chained (tamper-evident)
  Exportable for audit
```

### 2. Recipe Engine (Prime Mermaid Parser)
```
Recipe = Deterministic task definition:

Input:
  ```mermaid
  graph LR
    A["Fetch Gmail Inbox"] --> B["Extract Emails"]
    B --> C["Classify Importance"]
    C --> D["Generate Summary"]
    D --> E["Save to Outbox"]
  ```

Output:
  Summary JSON + evidence bundle

Execution:
  Same seed → same output (forever)
  Cached → $0.001/task (vs $0.01 with LLM)
```

### 3. PM Triplets (Context Model)
```
User Model:
  - Identity (who is using the agent)
  - Preferences (tone, language, style)
  - Constraints (budget, time, scope)

Task Model:
  - Goal (what does the agent need to do)
  - Inputs (what data does it start with)
  - Success criteria (when is the task done)

Context Model:
  - Current state (where are we in the task)
  - Decisions made (what has the agent done so far)
  - Remaining steps (what's left)

Enables composition:
  Email summarizer (output = summary)
    → LinkedIn poster (input = summary, output = draft)
    → Human approval (input = draft, output = approved/rejected)
```

### 4. Multi-Platform Recipes
```
Phase 1: Gmail (email triage, draft reply, send)
Phase 2: LinkedIn (post, comment, message)
Phase 3: Slack (channel summary, thread reply)
Phase 4: GitHub (issue triage, PR comment)
Phase 5: Notion (create page, sync data)
Phase 6+: Twitter, Stripe, Shopify, HubSpot, Calendly, etc.

Each platform:
  - Canonical task recipes
  - OAuth2/OAuth3 scopes mapped
  - Evidence capture (screenshots, DOM diffs)
  - Community refinement
```

### 5. Part 11 Audit Trail (Browser Edition)
```
Browser execution is especially auditable:
  - Visual evidence (screenshots at each step)
  - DOM snapshots (exact HTML before/after click)
  - Network log (what was requested)
  - Timing (how long each step took)

Audit bundle includes:
  ✓ oauth3_audit.jsonl (authorization events)
  ✓ action_audit.jsonl (every click, fill, submit)
  ✓ visual/ (screenshot at each step)
  ✓ dom/ (DOM snapshots)
  ✓ manifest.json (metadata, hashes)
  ✓ bundle.sha256 (tamper detection)

Auditor sees:
  "Agent clicked button #submit at 2:34:12"
  "Scopes: browser.send (✓ in scope)"
  "Screenshot before: [image]"
  "Screenshot after: [image]"
```

---

## ARCHITECTURE: 4 Layers

### Layer 1: Browser Automation
```
Playwright (preferred) or Selenium
  ├── Page navigation
  ├── Element selection + interaction
  ├── Screenshot + DOM capture
  └── Network interception
```

### Layer 2: OAuth3 Scope Gates
```
Every action wrapped in:
  ├── Check user token
  ├── Verify scope (browser.click required for click())
  ├── Record action (evidence chain)
  └── Execute or reject
```

### Layer 3: Recipe Execution Engine
```
Prime Mermaid parser:
  ├── Parse recipe DAG
  ├── Execute each node (deterministic)
  ├── Cache result (if recipe = known good)
  └── Return output + evidence
```

### Layer 4: PM Triplet Context
```
User + Task + Context models:
  ├── User preferences (tone, budget, constraints)
  ├── Task definition (goal, inputs, success criteria)
  └── Context state (what's been done, what's left)
```

---

## PROJECT PHASES (7 Phases, 14 Sessions)

| Phase | Name | Goal | Rung | Sessions | Dependencies |
|-------|------|------|------|----------|--------------|
| **0** | Foundation | Directory structure, docs, skeleton | 641 | 1 | None |
| **1** | OAuth3 Core | Token management, scope gates | 274177 | 2 | Phase 0 |
| **2** | Browser Automation | Playwright + recipe runner | 641 | 2 | Phase 1 |
| **3** | Recipe Engine | Prime Mermaid parser | 641 | 2 | Phase 2 |
| **4** | PM Triplets | User/Task/Context models | 641 | 2 | Phase 3 |
| **5** | Store Integration | Stillwater Store (read + submit) | 641 | 2 | Phase 4 + solaceagi Phase 3 |
| **6** | Multi-Platform | Gmail, LinkedIn, Slack, GitHub, Notion | 641 | 3 | Phase 5 |

**Total:** 14 sessions to rung 65537 (production ready)

**See:** `ROADMAP.md` (full specification)

---

## COMPETITIVE POSITION

| Competitor | Gap | Solace Browser Advantage |
|-----------|-----|------------------------|
| Selenium | No scope gates, no revocation, no evidence | OAuth3 + audit trail + recipe caching |
| Playwright | Same as Selenium | OAuth3 + audit trail + recipe caching |
| Browser-Use | No OAuth3, no recipe caching, vague evidence | Scoped, revocable, evidence-first |
| OpenClaw | No evidence, thousands of vulns | Part 11 architected, rung-gated |
| Bardeen | Chrome extension only, centralized control | Open source, local+cloud, federated |

### Why Uncopyable
```
1. OAuth3 is the dojo law
   No competitor can implement it without breaking their token model

2. Recipe library compounds
   Each community submission raises hit rate
   → lower COGS → better margins → attracts more users

3. Evidence by default
   Browser automation + audit trail = compliance ready
   Other platforms are opaque (screenshots or nothing)

4. Open source + community
   GitHub stars + community recipes = defensible moat
   Proprietary alternatives can't match pace of improvement
```

---

## ECOSYSTEM ROLE

Solace Browser fits into 9-project ecosystem:

```
stillwater/cli (OSS)
  ↓ (base CLI, anyone uses)

solace-browser (OSS)  ← YOU ARE HERE
  ├── OAuth3 reference impl
  ├── Recipe engine + caching
  ├── PM triplets
  └── Multi-platform recipes

  ↓ (feeds into)

solaceagi.com (PAID, hosted platform)
  ├── solace-browser + cloud twin
  ├── LLM router (L1–L5)
  ├── Memory Vault (search + diffs)
  └── Belt progression system
```

---

## RUNG LADDER

| Phase | Target Rung | Quality Gate | Example Test |
|-------|-------------|--------------|--------------|
| **0-4** | 641 | Unit tests pass locally | OAuth3 token issue/revoke works |
| **1, 5** | 274177 | Same recipe → same output (replay) | Issue + revoke token → actions blocked |
| **6** | 65537 | Survives adversarial | Revocation mid-action → immediate halt |

---

## BELT PROGRESSION

| Belt | Milestone | Achievement |
|------|-----------|-------------|
| White | First recipe runs | GitHub fork + modify recipe |
| Yellow | 5 recipes submitted | Stillwater Store submissions accepted |
| Orange | Recipe hit rate > 30% | Real user adoption, cache hits tracked |
| Green | Rung 65537 achieved | Full test suite + adversarial tests pass |
| Blue | 1,000+ GitHub stars | Community momentum |
| Black | OAuth3 external adopters | Other platforms adopt spec |

---

## QUICK START

### Run Phase 0
```bash
/build Phase_0_Foundation
```

### Then Phase 1 (OAuth3 Core)
```bash
/build Phase_1_OAuth3_Core
```

### See Progress
```bash
/status
cat scratch/todo/Phase_*.md
```

---

## KEY FILES

| File | Purpose |
|------|---------|
| NORTHSTAR.md | This file (vision + metrics) |
| CLAUDE.md | Directives (phases, skills, dispatch rules) |
| ROADMAP.md | Full build plan (workstreams, acceptance criteria) |
| README.md | Getting started for developers |
| scratch/todo/ | Phase checklists (Codex builds these) |

---

## SEE ALSO

- `ROADMAP.md` — Full build plan (7 phases, 14 sessions)
- `CLAUDE.md` — Project constraints + skills
- `README.md` — Developer quick start
- `/home/phuc/projects/solaceagi/NORTHSTAR.md` — Hosted platform (integrates this)
- `/home/phuc/projects/stillwater/` — Core OS + skills

---

**Signature:** Software 5.0 Edition
**Rung Target:** 65537 (production-ready, community-driven)
**Vision:** Open standard for OAuth3 + browser automation + recipes
**Status:** 🎯 Ready for Phase 0
