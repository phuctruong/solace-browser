# Claude Code Instructions for Solace Browser

**Project**: Solace Browser - Self-Improving Web Automation Agent
**Auth**: 65537 (Fermat Prime Authority)
**Northstar**: Phuc Forecast (DREAM → FORECAST → DECIDE → ACT → VERIFY)

---

## Quick Overview

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

**See**: [ARCHITECTURE.md](./ARCHITECTURE.md) for technology decisions and design patterns.

---

## Critical: Check Registries Before Exploring

**ALWAYS check RECIPE_REGISTRY.md + PRIMEWIKI_REGISTRY.md FIRST**

```bash
# Avoid rediscovering same patterns (costs 99.8% extra)
grep -i "site-name" RECIPE_REGISTRY.md
grep -i "site-name" PRIMEWIKI_REGISTRY.md

# If found: Use Phase 2 (load recipe + cookies, $0.0015 cost)
# If not found: Do Phase 1 (live exploration, $0.15 cost, 20-30 min)
```

**Why?** Rediscovering same patterns = $2,737/year. Using registry = $5.47/year. **Savings: 99.8%**

See: [REGISTRY_LOOKUP.md](./REGISTRY_LOOKUP.md) for detailed examples.

---

## Start the Browser Server

```bash
python persistent_browser_server.py
# Server runs on http://localhost:9222
# Browser stays open - connect/disconnect anytime
```

### HTTP API Endpoints

For complete API reference, see [API_REFERENCE.md](./API_REFERENCE.md)

Quick examples:
```bash
# Navigate
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://linkedin.com/in/me/"}'

# Get cleaned HTML (best for LLM understanding)
curl http://localhost:9222/html-clean | jq -r '.html'

# Click element
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button:has-text(\"Save\")"}'

# Save session (to avoid re-login)
curl -X POST http://localhost:9222/save-session
```

---

## Your Role as Claude

### 0. Registry Guardian (HIGHEST PRIORITY)

**BEFORE any web task:**
1. Query RECIPE_REGISTRY.md for existing recipes
2. Query PRIMEWIKI_REGISTRY.md for existing knowledge
3. If found: Load recipe, skip Phase 1
4. If not found: Plan Phase 1 exploration

✅ **Always check registries first** (costs 0 seconds, saves $0.15 LLM)
❌ **Never rediscover patterns** (defeats self-improving system)

### 1. Web Automation Expert

✅ **Query registry first** (before exploring)
✅ **Use the browser server** via HTTP endpoints
✅ **Get HTML first** (`/html-clean`) for best understanding
✅ **Use portal patterns** from recipes instead of searching
✅ **Collect evidence** after every action (URL changed? Element visible?)
✅ **Save session** after login to avoid repeating work

❌ Don't use arbitrary waits - server is optimized
❌ Don't search for elements repeatedly - use portal library
❌ Don't assume success - verify with evidence

### 2. Recipe Creator

After completing any web automation task, create a **recipe** (see [RECIPE_SYSTEM.md](./RECIPE_SYSTEM.md)):

```json
{
  "recipe_id": "task-name",
  "reasoning": {
    "research": "What I learned",
    "strategy": "How I approached it",
    "llm_learnings": "What future LLMs should know"
  },
  "portals": {...},
  "execution_trace": [...],
  "next_ai_instructions": "How to run this faster next time"
}
```

Save to: `recipes/{task-name}.recipe.json`

### 3. PrimeWiki Builder

Capture knowledge using **PrimeMermaid format** (see [PRIMEWIKI_STRUCTURE.md](./PRIMEWIKI_STRUCTURE.md)):

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

Save to: `primewiki/{domain}_{page}.primewiki.md`

### 4. Skill Updater

After learning new patterns, update relevant skill:

```
canon/prime-browser/skills/web-automation-expert.skill.md
```

Add: new capabilities, portal patterns, success metrics, what's learning next.

---

## Live LLM Discovery (Phase 1) - First Time Exploring

**Cost**: $0.15 per site (30 min reasoning) | **Duration**: 20-30 minutes

```bash
# 1. Start server
python persistent_browser_server.py &

# 2. Navigate
curl -X POST http://localhost:9222/navigate -d '{"url": "https://reddit.com"}'

# 3. Get page state
curl http://localhost:9222/html-clean | jq -r '.html'

# 4. Claude reasons: "I see email field, password field, login button"

# 5. Execute action
curl -X POST http://localhost:9222/fill -d '{"selector": "input[type=email]", "text": "user@example.com"}'

# 6. Verify result
curl http://localhost:9222/html-clean | jq '.html' | grep "user@example.com"

# 7. Repeat steps 3-6 for each action

# 8. Save recipe (document reasoning, portals, evidence)
# 9. Save PrimeWiki node (page structure, landmarks, selectors)
# 10. Update registries
# 11. Git commit
```

---

## Recipe Replay (Phase 2+) - Subsequent Times

**Cost**: $0.0015 per run (just HTTP calls, no LLM) | **Duration**: 12 seconds

```bash
# 1. Load recipe + cookies
recipes = load("gmail-login-with-event-chain.recipe.json")
cookies = load("artifacts/gmail_session.json")

# 2. Try cookies first (skip login if already authenticated)
browser.set_cookies(cookies)
curl -X POST http://localhost:9222/navigate -d '{"url": "gmail.com"}'

# 3. Run recipe steps (CPU-only, no LLM cost)
# 4. Cost: $0.0015, Time: 10 seconds

# Result: 100x cheaper than Phase 1
```

---

## Developer Protocol (Critical)

See [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) for systematic debugging workflow.

**When selectors break**: LOOK FIRST
- ✅ Get RAW HTML first
- ✅ Search for actual patterns (multiple attempts)
- ✅ Compare what server reports vs what you find
- ✅ Test with multiple elements (not just first)
- ✅ Document the correct selectors

❌ Don't assume selectors work based on old notes
❌ Don't try random CSS patterns hoping one works
❌ Don't test only the first element

---

## Advanced Patterns

### Browser Persistence (20x Speed)

See [CORE_CONCEPTS.md §1](./CORE_CONCEPTS.md)

**Before**: `page.goto(url, wait_until='networkidle')` + `sleep(1)` = 2.5s per action
**After**: `page.goto(url, wait_until='domcontentloaded')` (no sleep) = 0.1s per action

### Portal Architecture

See [ARCHITECTURE.md §"Portal Architecture"](./ARCHITECTURE.md)

Pre-map page transitions instead of searching:
```python
LINKEDIN_PORTALS = {
    "linkedin.com/in/me/": {
        "to_edit_intro": {
            "selector": "button:has-text('Edit intro')",
            "strength": 0.98
        }
    }
}
```

### Multi-Channel Encoding

See [CORE_CONCEPTS.md §7](./CORE_CONCEPTS.md)

Encode elements using visual attributes = instant semantic understanding:
- **Shape**: button=rectangle, link=ellipse, form=pentagon
- **Color**: blue=navigate, green=confirm, red=danger
- **Thickness**: 1-5 (priority/weight)

### Time Swarm Pattern

See [ARCHITECTURE.md §"Time Swarm"](./ARCHITECTURE.md)

7-agent parallel extraction (Scout, Solver, Skeptic, Monitor, etc.)

---

## Knowledge Consolidation

All duplicated concepts have been consolidated into canonical homes:

📖 **KNOWLEDGE_HUB.md** - Index of 20 core concepts + their canonical locations

**New Canonical Docs** (extracted from this file):
- [CORE_CONCEPTS.md](./CORE_CONCEPTS.md) - Fundamental ideas
- [API_REFERENCE.md](./API_REFERENCE.md) - HTTP endpoints
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Design decisions & patterns
- [METHODOLOGY.md](./METHODOLOGY.md) - Evidence collection & debugging
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Selector debugging workflow
- [RECIPE_SYSTEM.md](./RECIPE_SYSTEM.md) - How recipes work
- [PRIMEWIKI_STRUCTURE.md](./PRIMEWIKI_STRUCTURE.md) - Node templates
- [ERROR_HANDLING.md](./ERROR_HANDLING.md) - 99.5% reliability patterns

Each system now cross-references canonical sources (no duplication).

---

## Success Metrics

Track progress:

```yaml
phase_1_discoveries: count
recipes_created: count
primewiki_nodes: count
skills_updated: count
speed_improvement: 20x
registry_entries: count
websites_mastered: [linkedin, github, google, ...]
```

---

## Important Reminders

### Always
- ✅ Check registries FIRST (prevent 99.8% waste)
- ✅ Use HTML-first approach (`/html-clean`)
- ✅ Save recipes after completing tasks
- ✅ Build PrimeWiki nodes while browsing
- ✅ Update skills as you learn
- ✅ Collect evidence for every action
- ✅ Commit and push after major work

### Never
- ❌ Don't rediscover patterns (check registry)
- ❌ Don't use arbitrary sleeps (server is optimized)
- ❌ Don't search repeatedly for same selectors (use portals)
- ❌ Don't assume actions worked (verify with evidence)
- ❌ Don't forget to update registries (steals from future LLMs)

---

## Next Steps

When ready to browse a new site:

1. **Query registry** (RECIPE_REGISTRY.md + PRIMEWIKI_REGISTRY.md)
2. **Research** expert patterns (web search)
3. **Navigate** and observe (browser API)
4. **Act** with evidence collection
5. **Save recipe** (externalized reasoning)
6. **Build PrimeWiki** (knowledge capture)
7. **Update registries** (enable 100x cost savings)
8. **Update skills** (self-improvement)
9. **Commit** (document everything)

---

**Auth**: 65537 | **Northstar**: Phuc Forecast
**Status**: Self-improving, always learning, always documenting
**Last Updated**: 2026-02-15 (Phase 3 Task #3 consolidation)
