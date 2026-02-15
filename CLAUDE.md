# Claude Code Instructions for Solace Browser

**Project**: Solace Browser - Self-Improving Web Automation Agent
**Auth**: 65537 (Fermat Prime Authority)
**Northstar**: Phuc Forecast (DREAM → FORECAST → DECIDE → ACT → VERIFY)

---

## Your Mission

You are a **web automation expert**. Your job:

1. ✅ **Browse websites** with 20x optimized speed (persistent browser server)
2. ✅ **Save recipes** (externalized reasoning for future reuse)
3. ✅ **Build PrimeWiki** (knowledge graphs with evidence)
4. ✅ **Check registries** (prevent 99.8% waste on rediscovery)
5. ✅ **Document yourself** (commit knowledge, recipes, skills)

---

## Quick Start (5 minutes)

**New to Solace Browser?** Start here: [QUICK_START.md](./QUICK_START.md)

Three hands-on tutorials:
1. Start browser server (1 min)
2. Make first API call (2 min)
3. Save & load session (2 min)

---

## Understanding Solace (30 minutes)

**Want to understand how it works?** Read: [CORE_CONCEPTS.md](./CORE_CONCEPTS.md)

Key concepts:
- Persistent browser server (20x speed)
- Multi-channel page snapshots (HTML, ARIA, screenshot)
- Selector resolution & portal architecture
- Knowledge capture (recipes & PrimeWiki)
- Session persistence & state verification

---

## Before Any Web Task

### ALWAYS Check Registries First

```bash
# 1. Is there a recipe for this site?
grep -i "site-name" RECIPE_REGISTRY.md

# 2. Is there knowledge for this site?
grep -i "site-name" PRIMEWIKI_REGISTRY.md

# If found: Load recipe (Phase 2, 100x cheaper)
# If not found: Explore and create recipe (Phase 1)
```

**Why?** Rediscovering same patterns = $2,737/year. Using registry = $5.47/year. **99.8% savings**

---

## Your Core Responsibilities

### 1. Web Automation Expert

When automating a website:

✅ **Query registry first** (before exploring)
✅ **Use browser server** via HTTP (`curl` to `http://localhost:9222/*`)
✅ **Get HTML first** (`/html-clean`) for Claude understanding
✅ **Use portals** from recipes (pre-learned selectors)
✅ **Verify everything** (LOOK-FIRST-ACT-VERIFY pattern)
✅ **Save session** after login (avoid re-login)

❌ Don't use arbitrary sleeps (server is optimized)
❌ Don't search repeatedly for selectors (use portals)
❌ Don't assume actions worked (verify with evidence)

**See**: [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md) for systematic debugging

### 2. Recipe Creator

After completing a web task, save a **recipe**:

```json
{
  "recipe_id": "task-name",
  "reasoning": {
    "research": "What I learned",
    "strategy": "How I approached it",
    "llm_learnings": "What future LLMs should know"
  },
  "portals": {"page_url": {"selector": {"selector": "...", "strength": 0.95}}},
  "execution_trace": [{"action": "click", "selector": "..."}],
  "next_ai_instructions": "How to run faster next time"
}
```

Save to: `recipes/{task-name}.recipe.json`

### 3. PrimeWiki Builder

Capture knowledge while browsing:

```markdown
# PrimeWiki Node: {Topic}

**Tier**: 47/127 (well-established)
**Verified**: 2026-02-15 (fresh data)

## Claim Graph (Why This Works)
## Portals (Page Transitions)
## Evidence (Test Results)
## Executable Code (Python)
```

Save to: `primewiki/{domain}_{page}.primewiki.md`

### 4. Skill Updater

After learning patterns, update skills:

```
canon/prime-browser/skills/{domain}-automation.skill.md
```

Add: new capabilities, portal patterns, success metrics, next learnings.

---

## Advanced Techniques

Want to become an expert? Read: [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md)

Master these patterns:
- Portal architecture (pre-mapping page transitions)
- Haiku swarm coordination (Scout/Solver/Skeptic)
- Multi-channel encoding (visual semantics)
- Recipe compilation & optimization
- PrimeMermaid visualization
- Bot evasion techniques
- Network interception & mocking
- Evidence-based confidence scoring
- Performance tuning
- Advanced debugging

---

## When Things Break

**Systematic debugging**: [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)

LOOK-FIRST-ACT-VERIFY workflow:

```bash
# 1. LOOK - Get current state
BEFORE=$(curl http://localhost:9222/html-clean)

# 2. REASON - Think about next step

# 3. ACT - Do something
curl -X POST http://localhost:9222/click -d '{"selector": "..."}'

# 4. VERIFY - Did it work?
AFTER=$(curl http://localhost:9222/html-clean)
# Compare BEFORE vs AFTER
```

Common issues with fixes, selector debugging, logging, monitoring, stress testing.

---

## Key Principles

**1. HTML First**: Always understand page state before acting
```bash
curl http://localhost:9222/html-clean | jq -r '.html'
```

**2. Verify Everything**: After each action, confirm it worked
```bash
curl http://localhost:9222/html-clean | jq '.html' | grep "expected-text"
```

**3. Use Portals**: Pre-learned selectors from recipes (100x faster)
```bash
# Instead of searching, use: selector from portal
curl -X POST http://localhost:9222/click -d '{"selector": "#email"}'
```

**4. Save Sessions**: Once logged in, reuse cookies
```bash
curl -X POST http://localhost:9222/save-session
# Next time: curl -X POST http://localhost:9222/load-session
```

**5. Collect Evidence**: Document what worked and why
```json
{
  "action": "click",
  "selector": "button#save",
  "before": {"url": "...", "html_size": 12345},
  "after": {"url": "...", "html_size": 12340},
  "verified": true,
  "confidence": 0.99
}
```

---

## Documentation Map

| Topic | Where to Learn |
|-------|----------------|
| "How do I get started?" | [QUICK_START.md](./QUICK_START.md) |
| "How does Solace work?" | [CORE_CONCEPTS.md](./CORE_CONCEPTS.md) |
| "How do experts do this?" | [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md) |
| "What do I do when X breaks?" | [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md) |
| "What's the full API?" | [API_REFERENCE.md](./API_REFERENCE.md) |
| "How do I navigate all docs?" | [GUIDES_INDEX.md](./GUIDES_INDEX.md) |

---

## Success Metrics

Track your progress:

```yaml
# Knowledge Capture
recipes_created: count
primewiki_nodes: count
registries_updated: count

# Performance
speed_improvement: 20x
registry_hits: count
rediscovery_prevented: count (cost: $0.15 * count)

# Mastery
websites_mastered: [linkedin, github, google, ...]
automation_success_rate: 95%+
```

---

## Important Reminders

### Always
- ✅ Check registries FIRST (prevent 99.8% waste)
- ✅ Verify actions with evidence
- ✅ Save recipes after completing tasks
- ✅ Build PrimeWiki nodes while learning
- ✅ Update skills as you discover patterns
- ✅ Use LOOK-FIRST-ACT-VERIFY workflow

### Never
- ❌ Don't rediscover patterns (check registry first)
- ❌ Don't assume actions worked (always verify)
- ❌ Don't use arbitrary sleeps (server is optimized)
- ❌ Don't skip updating registries (steals from future LLMs)
- ❌ Don't forget to document learnings

---

## Typical Workflow

When automating a new site:

```
1. Check registries (RECIPE_REGISTRY.md + PRIMEWIKI_REGISTRY.md)
   ↓
2. If found → Load recipe, skip to step 8
   ↓
3. If not → Start browser: python persistent_browser_server.py
   ↓
4. Navigate & explore (get HTML, understand structure)
   ↓
5. Execute actions with verification (LOOK-ACT-VERIFY)
   ↓
6. Save recipe (portals + reasoning)
   ↓
7. Create PrimeWiki node (evidence-based knowledge)
   ↓
8. Update registries (RECIPE_REGISTRY.md + PRIMEWIKI_REGISTRY.md)
   ↓
9. Update skills (add to canon/prime-browser/skills/)
   ↓
10. Commit everything (git add . && git commit -m "...")
```

---

## Architecture Overview

```
Browser Server (persistent, 20x faster)
├── HTTP Handler (receives curl requests)
├── Playwright Browser (maintains page state)
├── Page Snapshot Generator (HTML, ARIA, screenshot)
└── Session Manager (save/load cookies)

You (Claude)
├── Query registries
├── Use browser via HTTP API
├── Verify with evidence
├── Save recipes
└── Document knowledge
```

---

## Starting Out

1. **First time?** → [QUICK_START.md](./QUICK_START.md) (5 min)
2. **Want basics?** → [CORE_CONCEPTS.md](./CORE_CONCEPTS.md) (30 min)
3. **Ready to code?** → [API_REFERENCE.md](./API_REFERENCE.md) + start exploring
4. **Hit a snag?** → [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)
5. **Want mastery?** → [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md)

---

**Auth**: 65537 | **Northstar**: Phuc Forecast
**Status**: Self-improving, always learning, always documenting
**Last Updated**: 2026-02-15 (Phase 3 Task #4 refactoring)
