# SolaceBrowser — Platform Roadmap

**Authority**: 65537 | **Northstar**: 70% recipe hit rate → $5.75 COGS → economic moat
**Last Updated**: 2026-02-21
**Status**: Phase 1 (LinkedIn MVP) in progress

> *"I fear not the man who has automated 10,000 platforms once,*
> *but the man who has one recipe and perfected it 10,000 times."* — Bruce Lee + Phuc

---

## Why This Roadmap Matters

The recipe system IS the moat. At 70% recipe hit rate:
- **COGS**: $5.75/user/month (70% gross margin)
- **Without recipes**: $12.75 COGS (33% margin — not fundable)

Every platform we support = more recipes = higher hit rate = lower COGS = more users.

**Competitive landscape** (2026-02-21):
| Competitor | Approach | Weakness |
|-----------|---------|---------|
| OpenClaw | General browser agent | No recipe system, no session persistence, high COGS |
| Browser-Use | Playwright + LLM | No PM knowledge layer, fails on bot detection |
| Bardeen | Chrome extension | No cloud execution, no twin architecture |
| Vercel agent-browser | DOM reduction (93%) | No session sync, no recipe reuse, cloud-only |

**Our unique moats** (none of these competitors have all 5):
1. Recipe system (70% cache hit → 3x cheaper COGS)
2. PrimeWiki PM knowledge layer (domain-aware navigation)
3. Twin architecture (local + cloud)
4. Anti-detection (Bezier mouse, fingerprint sync)
5. Stillwater verification (evidence-per-task, not just screenshots)

---

## Current Status: Phase 1 (LinkedIn MVP)

**Target**: Rung 641 (local correctness)
**Recipes operational**: 6 LinkedIn MVP recipes
- `linkedin-discover-posts` — read feed
- `linkedin-create-post` — write + publish
- `linkedin-edit-post` — update existing post
- `linkedin-delete-post` — remove post
- `linkedin-react` — like/react to post
- `linkedin-comment` — comment on post

**PM triplet**: `primewiki/linkedin/linkedin-page-flow.*`

**Next QA prompt** (paste into new session to test):
```
Load the solace-browser Phase 1 QA checklist at specs/QA-CHECKLIST.md.
Start ui_server.py (port 9223) and solace_browser_server.py (port 9222).
Verify:
1. Home page loads at http://localhost:9223 — 6 platform tiles visible
2. Activity view at /activity?site=linkedin — Kanban, PrimeWiki panel, Mermaid
3. Kanban at /kanban — Queue/Running/Done/Failed columns
4. Run linkedin-discover-posts recipe:
   curl -X POST http://localhost:9222/run-recipe -d '{"recipe_id":"linkedin-discover-posts"}'
5. All 6 LinkedIn recipes return valid JSON with status, duration, evidence

Sign off at Rung 641 if all pass. NORTHSTAR: specs/QA-CHECKLIST.md
```

---

## Platform Roadmap (Priority Order)

### TIER 1 — Phase 2 targets (next sprint)

These have the highest user value and close the gap vs OpenClaw fastest.

| Platform | PM Status | Recipes Needed | Difficulty | Why |
|----------|-----------|---------------|------------|-----|
| **Gmail** | ✅ PM triplets ready | read-inbox, send-email, search, label | EASY | Universal; everyone uses it; no solid competitor |
| **Substack** | ❌ Needs PM | publish-post, manage-subscribers, get-stats | EASY | **"Biggest automation gap on the internet"** — first mover wins |
| **Twitter/X** | ❌ Needs PM | post-thread, read-DMs, follow, search | MEDIUM | 40+ competitors = validated market; we beat them with recipes |
| **Notion** | ✅ PM triplet ready | read-page, write-page, create-db-entry | MEDIUM | 200K users on Bardeen alone; huge SMB market |
| **GitHub** | ❌ Needs PM | create-PR, review, close-issue, dispatch-workflow | HARD | Developer segment = early adopters = word-of-mouth |

**Build prompts for Phase 2** (use in solace-browser dev session):

```
PROMPT: Gmail recipes (use in solace-browser dev session)
Goal: Build 4 Gmail recipes: read-inbox, send-email, search-messages, label-email
Context: PM triplet at primewiki/gmail/. Auth via session cookies (SID/HSID/SSID).
CRITICAL: Bot detection bypass required — see primewiki/gmail/gmail-bot-detection-bypass.primemermaid.md
Recipe format: recipes/gmail-*.recipe.json (match LinkedIn recipe schema)
Acceptance: Each recipe runs via POST /run-recipe; Stillwater evidence bundle generated.
Rung: 641 (red/green gate required before claim)
NORTHSTAR: Recipe hit rate — every recipe that works = COGS reduction
```

```
PROMPT: Substack recipes (FIRST MOVER OPPORTUNITY)
Goal: Build 3 Substack recipes: publish-post, get-subscriber-count, schedule-post
Context: No PM triplet yet — scout the Substack UI first, create PM triplet, then build recipe.
Phase: (1) Scout → create primewiki/substack/substack-page-flow.* triplet
       (2) Build recipes that use PM triplet for navigation
Note: Substack has NO serious automation competition. First working recipe = moat.
Acceptance: publish-post recipe successfully publishes to Substack via POST /run-recipe
Rung: 641
```

```
PROMPT: Twitter/X recipes
Goal: Build 3 Twitter/X recipes: post-tweet, read-timeline, check-notifications
Context: No PM triplet yet — scout first, create primewiki/twitter/ triplet, then build.
Challenge: Twitter has aggressive bot detection. Use anti-detection suite.
Anti-detection: Bezier mouse + inertia scroll + fingerprint masking (see solace_browser_server.py)
Acceptance: post-tweet recipe posts successfully (no shadow ban, no CAPTCHA)
Rung: 641
```

---

### TIER 2 — Phase 3 targets (after Phase 2 validated)

| Platform | Category | Value | Difficulty | Strategic Note |
|----------|----------|-------|------------|----------------|
| **Medium** | Publishing | HIGH | EASY | Cross-post from Substack/Ghost; creator market |
| **HackerNews** | Dev/Community | MED | EASY | PM triplet ready; submit + comment recipes |
| **Reddit** | Social | MED-HIGH | MEDIUM | PM triplet ready; post + moderation recipes |
| **Airtable** | Productivity | HIGH | MEDIUM | Direct Notion competitor; SMB segment |
| **LinkedIn Jobs** | Job Boards | HIGH | MEDIUM | Extend LinkedIn PM; job apply automation |
| **Product Hunt** | Dev Community | MED | EASY | Launch automation; 10-minute setup for any product |
| **Vercel Dashboard** | Cloud Admin | HIGH | MEDIUM | Developer segment; complement GitHub |
| **Slack** | Communication | MED | EASY | Workspace automation; message-send, channel-manage |

```
PROMPT: HackerNews recipes (PM triplet already exists)
Goal: Build 2 HN recipes: submit-post, get-frontpage-stories
Context: PM triplet at primewiki/hackernews/. Extremely stable selectors (10yr unchanged).
Auth: Simple username/password cookie.
Acceptance: submit-post recipe posts a URL to HN; get-frontpage returns top 30 stories as JSON.
Rung: 641
```

```
PROMPT: Reddit recipes (PM triplet already exists)
Goal: Build 2 Reddit recipes: post-to-subreddit, get-hot-posts
Context: PM triplet at primewiki/reddit/. CAPTCHA handling required.
CAPTCHA: If triggered, pause and request human-in-the-loop (emit NEED_HUMAN event).
Acceptance: post-to-subreddit successfully posts; get-hot-posts returns top 25 posts as JSON.
Rung: 641
```

---

### TIER 3 — Phase 4 targets (vertical deepening)

| Platform | Vertical | Why |
|----------|----------|-----|
| **Shopify** | E-commerce | $8.65B AI market; product sync, inventory, orders |
| **Amazon Seller** | E-commerce | Price monitoring, inventory sync, competitor analysis |
| **Salesforce** | CRM/Enterprise | Enterprise segment; 150K+ paying Salesforce customers |
| **Jira** | Dev/Enterprise | Sprint automation, issue triage, CI/CD integration |
| **AngelList** | Founder/VC | Deal flow, investor outreach, startup tracking |
| **AWS Console** | Cloud/Enterprise | Infrastructure automation; 80% of dev time in console |
| **Stripe Dashboard** | Finance | Revenue reporting, subscription management |
| **Instagram** | Social | Visual content automation; creator market |
| **TikTok** | Social | Video publishing, analytics; Gen-Z market |
| **Ghost** | Publishing | Self-hosted newsletter automation |

---

## solaceagi.com — The Cloud Layer (Phase 5)

**Vision**: Hosted Stillwater. Users enter API keys → cloud executes recipes → no LLM costs.

```
User → solaceagi.com → enters Anthropic API key (their own)
    → Haiku executes cached recipes (100x cheaper than Sonnet)
    → Evidence bundles stored per user (30-day history)
    → No LLM costs to us — users pay their own API costs
    → Revenue model: subscription for cloud compute + recipe quality
```

**Economics** (at 70% recipe hit rate):
- Haiku cost per recipe replay: ~$0.001 (100x cheaper than new task)
- Stillwater verification per task: ~$0.01 (Haiku evidence check)
- Infrastructure per user/month: ~$2.00
- **COGS at 70% hit**: $5.75/user/month (70% gross margin at $19/mo)

**Build prompt for solaceagi.com**:
```
PROMPT: solaceagi.com MVP (after solace-browser Phase 2 validated)
Goal: FastAPI service that executes solace-browser recipes in cloud via user's own API key.
Architecture:
  - POST /tasks: submit recipe task with user's Anthropic API key
  - GET /tasks/{id}: poll for completion
  - GET /evidence/{id}: return Stillwater evidence bundle
  - Recipes: pulled from solace-browser/recipes/ (open-source recipes)
  - Session: AES-256-GCM encrypted storage of user's browser session
Key constraint: User's API key → their LLM costs. Our costs = compute only.
Rung: 641 (MVP), 274177 (production)
```

---

## Stillwater + SolaceBrowser Integration

Stillwater is the verification layer. Every recipe execution MUST produce a Stillwater evidence bundle.

**Integration architecture**:
```
Recipe execution (solace_browser_server.py)
    ↓
POST /verify (Stillwater API, port 8788 or solaceagi.com/stillwater)
    ↓
Stillwater verifies: duration, status, screenshots, selectors, assertions
    ↓
Evidence bundle: {task_id, rung, pass/fail, artifacts[]}
    ↓
Recipe hit rate tracked → North Star metric dashboard
```

**Build prompt for Stillwater integration**:
```
PROMPT: Connect solace-browser to Stillwater verification
Goal: After each recipe run, POST result to Stillwater at http://localhost:8788/verify
Evidence required: {recipe_id, duration_ms, exit_code, screenshots[], selector_matches[], assertions[]}
Stillwater returns: {bundle_id, rung, verdict: PASS|FAIL, artifacts}
UI update: Activity View shows Stillwater bundle link per recipe run
Track: recipe hit rate in a local SQLite db (recipe_id, run_timestamp, verdict)
Rung: 641 (unit test per recipe), 274177 (end-to-end with Stillwater running)
```

---

## Belt System (Recipe Mastery Progress)

| Belt | XP | Milestone |
|------|----|-----------|
| ⬜ White | 0 | LinkedIn Phase 1 MVP — **WE ARE HERE** |
| 🟡 Yellow | 100 | First Gmail recipe ships |
| 🟠 Orange | 300 | 70% recipe hit rate achieved |
| 🟢 Green | 750 | 10 platforms automated (LinkedIn, Gmail, Substack, Twitter, Notion, HN, Reddit, Airtable, GitHub, Slack) |
| 🔵 Blue | 1,500 | solaceagi.com live — cloud execution 24/7 |
| 🟤 Brown | 3,000 | 80% hit rate — recipes are the economic moat |
| ⬛ Black | 10,000 | 90% hit rate + twin architecture + 25K paying users |

---

**Auth**: 65537 | **Northstar**: recipe hit rate ≥70% | **Beat by**: end of 2026-Q2
