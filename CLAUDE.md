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

## Your Role as Claude

### 1. Web Automation Expert

When interacting with websites, you should:

✅ **Use the browser server** via HTTP endpoints
✅ **Get HTML first** (`/html-clean`) for best LLM understanding
✅ **Use portal patterns** from recipes instead of searching
✅ **Collect evidence** after every action (URL changed? Element visible?)
✅ **Save session** after login to avoid repeating work

❌ Don't use arbitrary waits - server uses smart waiting
❌ Don't search for elements repeatedly - use portal library
❌ Don't assume success - verify with evidence

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
