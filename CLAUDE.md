# Claude Code Instructions for Solace Browser

**Project**: Solace Browser - Self-Improving Web Automation Agent
**Auth**: 65537 (Fermat Prime Authority)
**Northstar**: Phuc Forecast (DREAM → FORECAST → DECIDE → ACT → VERIFY)

---

## What You're Working On

This is a **self-improving web crawler** that:

1. **Browses websites** with 20x optimized speed (persistent browser server)
2. **Saves recipes** (externalized LLM reasoning for future replays)
3. **Builds PrimeWiki** (knowledge graphs with evidence + portals)
4. **Updates skills** constantly as it learns new patterns
5. **Documents itself** (commits knowledge, recipes, skills)

---

## Architecture

### Core Components

```
solace-browser/
├── persistent_browser_server.py    # HTTP server (stays alive, 20x faster)
├── enhanced_browser_interactions.py # ARIA + PageObserver + NetworkMonitor
├── browser_interactions.py          # Basic ARIA tree extraction
├── recipes/                         # Saved LLM reasoning (replayable)
├── primewiki/                       # Knowledge nodes with evidence
├── canon/prime-browser/skills/      # Self-updating skills
└── artifacts/                       # Sessions, screenshots, proofs
```

### Key Technologies

- **Playwright**: Browser automation (Chromium)
- **aiohttp**: Async HTTP server (persistent, fast)
- **PrimeMermaid**: Visual knowledge graphs (style = data)
- **PrimeWiki**: Evidence-based knowledge capture
- **Recipe System**: Externalized reasoning for LLM replay

---

## Login Patterns (CORRECT - Phase 1 Learning)

### Gmail/Google Login (Auto-Fill Pattern)
```python
# CORRECT FLOW:
# 1. Load credentials from credentials.properties (email + password)
# 2. Navigate to Gmail
# 3. Check if already logged in with saved cookies
# 4. If NOT: Auto-fill email via JavaScript (full event chain)
#    - input.focus() + input.value = email
#    - Dispatch: input, change, keyup events
#    - input.blur() to trigger validation
# 5. Click Next button (wait for enabled state)
# 6. Auto-fill password (same pattern as email)
# 7. Click Sign in button
# 8. Check for 2FA/OAuth screen
# 9. WAIT for user OAuth approval (only if needed)
# 10. Save session cookies for Phase 2+ replay

# DO NOT: Wait for user to type credentials - automate it
# DO NOT: Use page.fill() without event chain - Gmail validates via events
# DO NOT: Hammer login endpoint - triggers security locks
```

### Why This Works
- ✅ Respects full validation event chain (Gmail's JS expects it)
- ✅ Uses credentials from secure config (not embedded)
- ✅ Saves cookies after login (Phase 2+ uses cookies, no re-login)
- ✅ Only waits for user action when needed (2FA/OAuth approval)
- ✅ Avoids security triggers (rate limit, suspicious behavior detection)

---

## CRITICAL: OpenClaw vs Solace Browser (Live LLM Paradigm)

### What OpenClaw Does (Browser Extension Pattern)
OpenClaw uses Chrome DevTools Protocol (CDP) with a browser extension to enable real-time LLM interaction:
- Extension sends page state to LLM
- LLM reasons about next action
- Extension executes action via CDP
- Cycle repeats in real-time

### What Solace Browser Does (Better - CLI Pattern)
**DO NOT write pre-written automation scripts.** Instead:

1. **Start the persistent browser server** (stays alive between commands)
2. **Get page state** via `/snapshot` or `/html-clean` endpoints
3. **Claude (you) reason** about what to do next in real-time
4. **Execute via HTTP API** (`/click`, `/fill`, `/navigate`, etc.)
5. **Verify result** by getting new snapshot
6. **Save knowledge** as recipes + PrimeWiki + skills

This is **better than OpenClaw** because:
- ✅ No browser extension needed
- ✅ Uses CLI (terminal) - more flexible
- ✅ Phase 1 produces reusable recipes → Phase 2+ cost 100x cheaper
- ✅ Builds self-improving knowledge base (PrimeWiki + recipes + skills)
- ✅ Deterministic replay with snapshots and canonicalization

### Correct Workflow (Live LLM, Not Scripts)

```bash
# 1. Start browser server (terminal 1)
python persistent_browser_server.py
# Server ready at http://localhost:9222

# 2. Navigate (CLI, this terminal)
curl -X POST http://localhost:9222/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://reddit.com/login"}'

# 3. Get page state (Claude reads this)
curl http://localhost:9222/html-clean | jq -r '.html'

# 4. Claude reasons: "I see email field, password field, login button"

# 5. Execute (Claude decides this)
curl -X POST http://localhost:9222/fill \
  -H "Content-Type: application/json" \
  -d '{"selector": "input[type=email]", "text": "user@example.com"}'

# 6. Verify (Claude checks result)
curl http://localhost:9222/html-clean | jq '.html' | grep "user@example.com"

# 7. Repeat steps 3-6 for each action

# 8. Save recipe (after task complete)
# Document: what I did, why, what I learned, portals discovered

# 9. Save PrimeWiki node (knowledge captured)
# Document: page structure, landmarks, selectors, magic words

# 10. Git commit
git add . && git commit -m "Phase 1 discovery: Reddit exploration complete"
```

### Why Scripts Are Wrong

❌ **Pre-written scripts** (OLD APPROACH):
- Hardcode every selector and action
- Brittle - breaks when UI changes
- No learning - scripts don't improve
- Can't adapt to unexpected states
- Can't explain reasoning
- Can't reuse knowledge

✅ **Live LLM reasoning** (CORRECT APPROACH):
- Real-time decision making
- Adapts to UI changes
- Learns and improves (recipes capture reasoning)
- Handles unexpected states
- Explains every decision
- Produces reusable recipes for Phase 2

### Remember This
"If you're writing a Python script to automate a website, you're doing it wrong. Use the browser server API and let Claude reason in real-time."

---

## Phase 1 (Discovery) vs Phase 2+ (Replay) Model

### Phase 1: Live LLM Discovery
- **Cost**: $0.15 per site (30 min LLM reasoning)
- **What happens**: Claude navigates, observes, reasons, learns
- **Output**: Recipes + PrimeWiki + Skills + Cookies
- **Run once** per site type
- **Time**: 20-30 minutes per site

### Phase 2+: CPU Replay (100x Cheaper)
- **Cost**: $0.0015 per run (just load recipes, no LLM)
- **What happens**: Load recipes → load cookies → execute actions → verify
- **Input**: Use recipes from Phase 1
- **CPU only** - no LLM calls
- **Time**: 12 seconds per run
- **Runs infinitely** - same action repeated

### Example: Gmail Login

**Phase 1 (First Time):**
```bash
# Claude navigates, observes, reasons
curl -X POST http://localhost:9222/navigate -d '{"url": "gmail.com"}'
curl http://localhost:9222/html-clean  # Claude sees login form
# Claude: "I see email field, I'll auto-fill with event chain"
curl -X POST http://localhost:9222/fill -d '{"selector": "email", "text": "user@gmail.com"}'
# ... more actions ...
# Claude saves recipe: gmail-login-with-event-chain.recipe.json
# Claude saves cookies: artifacts/gmail_session.json
# Cost: $0.15
```

**Phase 2+ (Subsequent Times):**
```bash
# Load recipe + cookies
recipes = load("gmail-login-with-event-chain.recipe.json")
cookies = load("artifacts/gmail_session.json")

# Try cookies first (skip login if already authenticated)
browser.set_cookies(cookies)
curl -X POST http://localhost:9222/navigate -d '{"url": "gmail.com"}'
snapshot = curl http://localhost:9222/html-clean
if "inbox" in snapshot:
    # Already logged in! Done.
    # Cost: $0.0015, Time: 2 seconds
else:
    # Run recipe steps
    # Cost: $0.0015, Time: 10 seconds
```

---

## Session Learning: Security Triggers (Gmail)

### What Happened
- Attempted Gmail login 5+ times in quick succession
- Gmail detected suspicious behavior (bot-like pattern)
- Session terminated, couldn't recover

### Why It Happened
- ❌ Kept re-logging in without checking for existing cookies
- ❌ Used same credentials repeatedly (no rate limiting)
- ❌ Didn't respect OAuth flow (tried to skip 2FA entirely)

### Solution Learned
- ✅ Check saved cookies FIRST before login attempt
- ✅ Only login once per session (reuse cookies after that)
- ✅ Respect authentication flow (email → click Next → password → click Sign in → wait for OAuth if needed)
- ✅ Use full event chain (focus → input → change → keyup → blur) - Gmail validates via events

### Key Insight
**Websites have rate limits and bot detection. Respect their security or they'll block you. The smart approach is to login once (Phase 1), save cookies, then reuse (Phase 2+). Never retry authentication.**

---

## Session Learning: Redis Phase 1 Exploration Success

### What We Discovered
Explored 3 Reddit pages (logged out), captured:
- **Homepage**: 209 landmarks (buttons, navigation, lists)
- **Login page**: Email field, password field, SSO buttons, 2FA options
- **Subreddit page**: Post list, subscribe button, sort options

### What We Saved
1. **3 PrimeWiki nodes** - semantic structure of each page
2. **3 Recipe templates** - selectors, portals, magic words
3. **3 Canonical snapshots** - deterministic SHA-256 hashes
4. **212 total landmarks** - buttons, forms, navigation elements

### Key Learnings
- ✅ Exploration works better **logged out first** (no security triggers)
- ✅ Snapshot canonicalization produces deterministic hashes (useful for verification)
- ✅ Portal architecture maps state transitions (from homepage → login → subreddit)
- ✅ Magic words ("Log in", "Sign up", "Subscribe") help future LLMs understand intent

### Phase 2 Application
Next time we visit Reddit, we can:
1. Load recipes from Phase 1
2. Load cookies (after login)
3. Execute login recipe → navigate to subreddit → create post
4. Cost: $0.0015 instead of $0.15

---

## How to Use

### Start the Browser Server

```bash
python persistent_browser_server.py
# Server runs on http://localhost:9222
# Browser stays open - connect/disconnect anytime
```

### API Endpoints

```bash
# Navigate
curl -X POST http://localhost:9222/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://linkedin.com/in/me/"}'

# Get page snapshot (ARIA + HTML + console + network)
curl http://localhost:9222/snapshot | jq

# Get cleaned HTML (best for LLM understanding)
curl http://localhost:9222/html-clean | jq -r '.html'

# Click element
curl -X POST http://localhost:9222/click \
  -H "Content-Type: application/json" \
  -d '{"selector": "button:has-text(\"Save\")"}'

# Fill form field
curl -X POST http://localhost:9222/fill \
  -H "Content-Type: application/json" \
  -d '{"selector": "#email", "text": "user@example.com"}'

# Save session (to avoid re-login)
curl -X POST http://localhost:9222/save-session

# Screenshot
curl http://localhost:9222/screenshot | jq
```

---

## ⭐ CRITICAL: Query Registry Before Doing Anything

**Before you explore a website or write any automation:**

```bash
# 1. Check RECIPE_REGISTRY.md
grep -i "site-name" RECIPE_REGISTRY.md

# 2. Check PRIMEWIKI_REGISTRY.md
grep -i "site-name" PRIMEWIKI_REGISTRY.md

# 3. If recipe exists:
#    → Use Phase 2 (load recipe + cookies, CPU-only)
#    → Cost: $0.0015 | Time: 12 seconds
#
# 4. If no recipe found:
#    → Do Phase 1 live exploration (this session)
#    → Cost: $0.15 | Time: 20-30 minutes
#    → Create recipe + PrimeWiki + update registries
```

**Why This Matters:**
- ❌ Without registry: Each session rediscovers same patterns ($0.15 × 365 = $2,737/year)
- ✅ With registry: Load from cache ($0.0015 × 365 = $5.47/year)
- **Savings: 99.8% cost reduction**

See: REGISTRY_LOOKUP.md for detailed examples

---

## Your Role as Claude

### 0. Registry Guardian (NEW - HIGHEST PRIORITY)

**BEFORE any web task:**
1. Query RECIPE_REGISTRY.md for existing recipes
2. Query PRIMEWIKI_REGISTRY.md for existing knowledge
3. If found: Load recipe, skip Phase 1
4. If not found: Plan Phase 1 exploration
5. After task: Update registries

✅ **Always check registries first** (costs 0 seconds, saves 0.15 LLM dollars)
✅ **Update registries after discovery** (enables 100x cost savings for future LLMs)
❌ Don't rediscover patterns (defeats entire self-improving system)
❌ Don't skip registry updates (steals knowledge from future LLMs)

### 1. Web Automation Expert

When interacting with websites, you should:

✅ **Query registry first** (before exploring)
✅ **Use the browser server** via HTTP endpoints
✅ **Get HTML first** (`/html-clean`) for best LLM understanding
✅ **Use portal patterns** from recipes instead of searching
✅ **Collect evidence** after every action (URL changed? Element visible?)
✅ **Save session** after login to avoid repeating work

❌ Don't use arbitrary waits - server uses smart waiting
❌ Don't search for elements repeatedly - use portal library + registry
❌ Don't assume success - verify with evidence
❌ Don't rediscover patterns - check registry first

### 2. Recipe Creator

After completing any web automation task, create a **recipe**:

```json
{
  "recipe_id": "task-name",
  "reasoning": {
    "research": "What I learned",
    "strategy": "How I approached it",
    "llm_learnings": "What future LLMs should know"
  },
  "portals": {
    "from_state": {
      "to_state": {
        "selector": "...",
        "type": "click|navigate|submit",
        "strength": 0.95
      }
    }
  },
  "execution_trace": [...],
  "next_ai_instructions": "How to run this faster next time"
}
```

Save to: `recipes/{task-name}.recipe.json`

### 3. PrimeWiki Builder

Capture knowledge while browsing in **PrimeMermaid format**:

```markdown
# PrimeWiki Node: {Topic}

**Tier**: 23/47/79/127/241
**C-Score**: 0.90+ (coherence)
**G-Score**: 0.85+ (gravity)

## Claim Graph (Mermaid)
## Canon Claims (with evidence)
## Portals (related nodes)
## Metadata (YAML)
## Executable Code (Python)
```

Save to: `primewiki/{topic}.primemermaid.md`

### 4. Skill Updater

After learning new patterns, update:

```
canon/prime-browser/skills/web-automation-expert.skill.md
```

Add:
- New capabilities
- Portal patterns discovered
- Success metrics
- What you're learning next

### 5. Document Maintainer

Keep these files up to date:
- `CLAUDE.md` (this file - your instructions)
- `README.md` (project overview)
- `BROWSER_CRAWL_UPGRADES.md` (planned improvements)

---

## Speed Optimizations Applied

### Before (Slow)
```python
await page.goto(url, wait_until='networkidle')
await asyncio.sleep(1)  # ❌ Arbitrary wait
```

### After (Fast - 20x)
```python
await page.goto(url, wait_until='domcontentloaded')
# No sleep - returns immediately ✅
```

**Result**: 2.5 sec → 0.1 sec per action

---

## Advanced Patterns (From PrimeWiki Books)

### Multi-Channel Encoding
Encode elements using **visual attributes** = instant semantic understanding:

- **Shape**: button=rectangle, link=ellipse, form=pentagon
- **Color**: blue=navigate, green=confirm, red=danger
- **Geometry**: triangle=3 (menu), pentagon=5 (form)
- **Thickness**: 1-5 (priority/weight)

### Portal Architecture
Pre-map page transitions instead of searching:

```python
LINKEDIN_PORTALS = {
    "linkedin.com/in/me/": {
        "to_edit_intro": {
            "selector": "button:has-text('Edit intro')",
            "type": "modal_open",
            "strength": 0.98
        }
    }
}
```

### Time Swarm Pattern
7-agent parallel extraction (Inhale/Exhale):

1. A1: Navigate + wait
2. A2: Screenshot
3. A3: ARIA tree
4. A4: Clean HTML
5. A5: Extract portals
6. A6: Find issues (skeptic)
7. A7: Synthesize → PrimeMermaid map

---

## Current Capabilities

### Mastered
- ✅ LinkedIn profile optimization (10/10 based on expert research)
- ✅ Speed optimization (20x faster)
- ✅ Recipe creation (externalized reasoning)
- ✅ PrimeWiki capture (evidence-based knowledge)
- ✅ Session persistence (avoid re-login)
- ✅ Portal mapping (pre-learned patterns)

### Learning
- ⏳ Evidence-based success detection (confidence scores)
- ⏳ Multi-site portal libraries (GitHub, Google, etc.)
- ⏳ PrimeMermaid map generation
- ⏳ Self-improving recipe optimization

---

## Example Workflow

### LinkedIn Profile Optimization

```bash
# 1. Start server (if not running)
python persistent_browser_server.py &

# 2. Navigate to profile
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://linkedin.com/in/me/"}'

# 3. Get current state
curl http://localhost:9222/html-clean | jq -r '.html' > current.html

# 4. Reason about optimization
# (You apply expert formulas: mobile hook, headline formula, etc.)

# 5. Execute changes
curl -X POST http://localhost:9222/fill \
  -d '{"selector": "#headline", "text": "Software 5.0 Architect | 65537 Authority | Building Verified AI OS in Public"}'

# 6. Save recipe
# (Document reasoning, portals, evidence)

# 7. Save PrimeWiki node
# (Claims + evidence + portals)

# 8. Update skills
# (Add new patterns learned)

# 9. Commit everything
git add . && git commit -m "feat: LinkedIn profile optimization to 10/10"
```

---

## Important Reminders

### Always
- ✅ Use HTML-first approach (`/html-clean`)
- ✅ Save recipes after completing tasks
- ✅ Build PrimeWiki nodes while browsing
- ✅ Update skills as you learn
- ✅ Collect evidence for every action
- ✅ Use `/remember` to persist key learnings
- ✅ Commit and push after major work

### Never
- ❌ Don't use arbitrary sleeps (server is optimized)
- ❌ Don't search for selectors you've already found (use portals)
- ❌ Don't assume actions worked (verify with evidence)
- ❌ Don't forget to save recipes (future LLMs need them)
- ❌ Don't skip PrimeWiki capture (knowledge compounds)

---

## Success Metrics

Track your progress:

```yaml
recipes_created: {count}
primewiki_nodes: {count}
skills_updated: {count}
speed_improvement: 20x
commits_made: {count}
websites_mastered: [linkedin, github, google, ...]
```

---

## Next Steps

When you're ready to browse a new site:

1. **Research** expert patterns (web search)
2. **Navigate** and observe (multi-channel snapshot)
3. **Reason** about optimal approach
4. **Act** with evidence collection
5. **Save recipe** (externalized reasoning)
6. **Build PrimeWiki** (knowledge capture)
7. **Update skills** (self-improvement)
8. **Commit** (document everything)

---

**Auth**: 65537 | **Northstar**: Phuc Forecast
**Status**: Self-improving, always learning, always documenting
