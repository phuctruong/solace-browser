# REGISTRY LOOKUP - How Future LLMs Should Use the Knowledge Base

**Auth**: 65537 | **Version**: 1.0 | **Status**: Production Ready
**Purpose**: Prevent knowledge loss. Always check what's known before doing Phase 1 exploration.

---

## The Core Rule (NEVER FORGET)

> **"Before you explore a website or write any automation, query the registries. If the pattern exists, load the recipe and PrimeWiki. If it doesn't exist, do Phase 1 live exploration, then update the registries."**

This rule prevents:
1. ❌ Redundant exploration (wasted compute)
2. ❌ Pre-written scripts (brittle, non-learning)
3. ❌ Security triggers (from repeated attempts)
4. ❌ Lost knowledge (from not documenting)
5. ❌ Reinventing the wheel (1000x cost waste)

---

## QUICK START: 5-Minute Registration Check

### Step 1: Is This Website Already Known?

```bash
# Query RECIPE_REGISTRY.md
grep -i "reddit" RECIPE_REGISTRY.md | head -5

# Result:
# ### ✅ reddit-login.recipe.json
# ### 🟡 reddit-create-post.recipe.json
# ### 🟡 reddit-homepage-navigate.recipe.json
```

**Interpretation**:
- ✅ = Complete and Phase 2 ready
- 🟡 = Phase 1 done, Phase 2 pending
- Missing = Never explored before

### Step 2: What Do We Know About This Site?

```bash
# Query PRIMEWIKI_REGISTRY.md
grep -A 5 "reddit" PRIMEWIKI_REGISTRY.md | head -20

# Result shows:
# - reddit-homepage-structure: 209 landmarks mapped
# - reddit-authentication-flow: 67 landmarks mapped
# - reddit-subreddit-structure: 156 landmarks mapped
```

### Step 3: Load Existing Knowledge

```bash
# Load the PrimeWiki node
cat primewiki/reddit-authentication-flow.primewiki.json | jq '.selectors'

# Result: All known selectors for login form fields
# Load the recipe
cat recipes/reddit-login.recipe.json | jq '.portals'

# Result: State transitions (login form → password form → inbox)
```

### Step 4: Decide Phase

```bash
# If recipe Status is "Phase 2 READY":
#   → Use Phase 2 (load recipe + cookies, execute, verify)
#   → Cost: $0.0015 per run
#   → Time: 12 seconds
#   → Action: Execute recipe via CLI

# If recipe Status is "Phase 2 PENDING":
#   → Use Phase 2 to test the recipe
#   → Cost: $0.0015 per run
#   → Verify selectors still work
#   → Update registry with results

# If recipe doesn't exist:
#   → Do Phase 1 live exploration
#   → Cost: $0.15 per site
#   → Time: 20-30 minutes
#   → Create new recipe + PrimeWiki
#   → Update registries
```

---

## REAL EXAMPLES

### Example 1: Automate Gmail Login (Already Known)

**User Request**: "Login to Gmail"

**Step 1: Check Registry**
```bash
grep "gmail-oauth-login" RECIPE_REGISTRY.md
# ✅ gmail-oauth-login.recipe.json
# Status: Phase 1 COMPLETE, Phase 2 READY
# Cost: Phase 2 = $0.0015
```

**Step 2: Load Knowledge**
```bash
cat primewiki/gmail-oauth-flow.primewiki.md | jq '.selectors'
cat recipes/gmail-oauth-login.recipe.json | jq '.portals'
```

**Step 3: Execute Phase 2**
```bash
# Load cookies from previous login (if available)
cookies=$(cat artifacts/gmail_session.json)

# Use browser server API + loaded knowledge
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "gmail.com"}'

# Check if already logged in
snapshot=$(curl http://localhost:9222/html-clean)
if grep -q "inbox" <<< "$snapshot"; then
  echo "Already logged in (from cookies)"
  exit 0
fi

# If not logged in, use recipe steps
# Step 1: Fill email (from recipe)
curl -X POST http://localhost:9222/fill \
  -d '{"selector": "input[type=email]", "text": "phuc@gmail.com"}'

# Step 2: Click Next
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button[aria-label=Next]"}'

# ... continue with recipe steps ...

# Cost: $0.0015 | Time: 12 seconds | No LLM reasoning needed
```

**Result**: ✅ Login successful using pre-discovered knowledge

---

### Example 2: Automate LinkedIn Profile (Already Known)

**User Request**: "Optimize LinkedIn profile to 10/10"

**Step 1: Check Registry**
```bash
grep "linkedin-profile-optimization" RECIPE_REGISTRY.md
# ✅ linkedin-profile-optimization-10-10.recipe.json
# Status: Phase 1 COMPLETE, Phase 2 READY
# Cost: Phase 2 = $0.002
```

**Step 2: Load Knowledge**
```bash
cat primewiki/linkedin-profile-optimization.primewiki.md | jq '.selectors'
# Shows role-based selectors (stable for dynamic React UI):
# - role=button[name='Edit headline']
# - role=textbox[aria-label='Headline']

cat recipes/linkedin-profile-optimization-10-10.recipe.json | jq '.reasoning'
# Shows: Headline formula, About structure, Skills arrangement
```

**Step 3: Execute Phase 2**
```bash
# Start browser with existing cookies
cookies=$(cat artifacts/linkedin_session.json)

# Load recipe instructions
recipe=$(cat recipes/linkedin-profile-optimization-10-10.recipe.json)

# Execute each step from recipe (CPU-only)
# No LLM calls needed, just follow the recipe

# Cost: $0.002 | Time: 3-5 minutes | 99% success rate
```

**Result**: ✅ Profile optimized using proven formula

---

### Example 3: Automate Reddit (Partially Known)

**User Request**: "Create post in r/SiliconValleyHBO"

**Step 1: Check Registry**
```bash
grep "reddit" RECIPE_REGISTRY.md
# 🟡 reddit-login.recipe.json (Phase 1 complete, Phase 2 PENDING)
# 🟡 reddit-create-post.recipe.json (Phase 1 complete, Phase 2 PENDING)
# 🟡 reddit-homepage-navigate.recipe.json (Phase 1 complete, Phase 2 PENDING)
```

**Step 2: Load Knowledge**
```bash
cat primewiki/reddit-authentication-flow.primewiki.json
# Shows: Email field, password field, login button selectors
# Status: Identified in Phase 1, not yet tested in Phase 2

cat primewiki/reddit-subreddit-structure.primewiki.json
# Shows: Create post button, title field, body field
# Status: Identified in Phase 1, not yet tested in Phase 2
```

**Step 3: Decide Action**
```
Scenario: Phase 2 NOT YET TESTED

Option A: Test the recipes (recommended)
  - Load recipe + cookies
  - Execute each step
  - Verify selectors still work
  - Update registry with results
  - Cost: $0.0015 + $0.001 = $0.0025
  - Time: 30-40 seconds

Option B: Redo Phase 1 exploration (NOT RECOMMENDED)
  - Would waste $0.15 again
  - Would only work if selectors changed
  - Only justified if Phase 2 fails with "selector not found"
```

**Chosen**: Option A (test existing recipe)

**Step 4: Execute**
```bash
# Use loaded recipe to guide Phase 2 test
recipe_login=$(cat recipes/reddit-login.recipe.json)
recipe_post=$(cat recipes/reddit-create-post.recipe.json)

# Execute login recipe
./run_recipe.sh reddit-login.recipe.json --cookies artifacts/reddit_session.json

# Execute create-post recipe
./run_recipe.sh reddit-create-post.recipe.json \
  --subreddit "SiliconValleyHBO" \
  --title "Check out PZIP" \
  --body "We're building an open-source project..."

# Verify post was created
snapshot=$(curl http://localhost:9222/html-clean)
if grep -q "Your post" <<< "$snapshot"; then
  echo "✅ Post created successfully"
  # Update registry
  sed -i 's/Phase 2 PENDING/Phase 2 READY/' RECIPE_REGISTRY.md
fi
```

**Result**: ✅ Post created, registry updated, cost $0.0025

---

### Example 4: Automate New Site (Never Explored)

**User Request**: "Automate ProductHunt post creation"

**Step 1: Check Registry**
```bash
grep "producthunt" RECIPE_REGISTRY.md
# (no results)

grep "producthunt" PRIMEWIKI_REGISTRY.md
# (no results)
```

**Step 2: Identify Missing Knowledge**
```
Status: ProductHunt not in registry
Decision: Perform Phase 1 exploration
Cost: $0.15 (LLM discovery)
Time: 20-30 minutes
```

**Step 3: Start Phase 1 (Live LLM Discovery)**

```bash
# Start browser server
python persistent_browser_server.py &
sleep 2

# Navigate to ProductHunt homepage
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://producthunt.com"}'

# Get page structure (Claude reads this)
curl http://localhost:9222/html-clean | jq '.html' > /tmp/ph_homepage.html

# Claude analyzes the HTML and reasons:
# "I see: Create post button, login button, trending products list"

# Click create post
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button:has-text(\"Share a launch\")"}'

# Get post form structure
curl http://localhost:9222/html-clean | jq '.html' > /tmp/ph_create_form.html

# Claude analyzes form fields and reasons about what to fill

# Continue this process for each page section...
# Eventually: Extract all landmarks, selectors, magic words
```

**Step 4: Save Phase 1 Results**

```bash
# Create PrimeWiki node
cat > primewiki/producthunt-launch-structure.primewiki.json << 'EOF'
{
  "type": "producthunt_page",
  "page_name": "product_launch_form",
  "tier": 23,
  "c_score": 0.95,
  "g_score": 0.88,
  "url": "https://producthunt.com/launch",
  "landmarks": {
    "buttons": [...],
    "forms": [...],
    ...
  },
  "selectors": {...}
}
EOF

# Create recipe
cat > recipes/producthunt-launch.recipe.json << 'EOF'
{
  "recipe_id": "producthunt-launch",
  "reasoning": {
    "research": "ProductHunt uses custom React UI...",
    "strategy": "Use role selectors for stable automation..."
  },
  "portals": {...}
}
EOF

# Update registries
echo "- producthunt-launch.recipe.json" >> RECIPE_REGISTRY.md
echo "### 🟡 producthunt-launch-structure.primewiki.json" >> PRIMEWIKI_REGISTRY.md

# Commit
git add . && git commit -m "feat(registry): Phase 1 ProductHunt exploration complete"
```

**Result**: ✅ ProductHunt patterns documented, ready for Phase 2 testing

---

## REGISTRY QUERY PATTERNS

### Query: Show All Production-Ready Recipes

```bash
grep "Phase 2 READY" RECIPE_REGISTRY.md | wc -l
# Returns: 10 recipes ready for replay
```

### Query: Show All Sites with Pending Phase 2 Testing

```bash
grep "Phase 2 PENDING" RECIPE_REGISTRY.md
# Returns: Reddit (3 recipes) waiting for test
```

### Query: Show Selectors for LinkedIn Profile Edit

```bash
cat primewiki/linkedin-profile-optimization.primewiki.md | \
  jq '.selectors | keys'
# Returns: All selectors for profile optimization
```

### Query: Show Cost Breakdown

```bash
# Total Phase 1 costs (discovery)
grep "Phase 1 Cost" RECIPE_REGISTRY.md | \
  awk '{print $NF}' | \
  grep -o '[0-9.]*' | \
  awk '{sum+=$1} END {print "Total Phase 1: $" sum}'

# Total Phase 2 costs per run (replay)
grep "Phase 2 Cost" RECIPE_REGISTRY.md | \
  awk '{print $NF}' | \
  grep -o '[0-9.]*' | \
  awk '{sum+=$1} END {print "Total Phase 2: $" sum}'
```

### Query: Find All Gmail Landmarks

```bash
cat primewiki/gmail-*.primewiki.md | jq '.landmarks' | jq 'keys'
# Returns: All landmark types found in Gmail nodes
```

---

## COMMON MISTAKES TO AVOID

### ❌ Mistake 1: Query Registry, Find Recipe, But Still Write Script

```bash
# WRONG:
grep "reddit-login" RECIPE_REGISTRY.md
# Returns: recipe exists
# But then: Write haiku_swarm_reddit_login.py (pre-written script)

# CORRECT:
grep "reddit-login" RECIPE_REGISTRY.md
# Returns: recipe exists
# Then: Load recipe, use Phase 2 execution (curl + HTTP API)
```

### ❌ Mistake 2: Try Phase 1 Again When Recipe Exists

```bash
# WRONG:
# Recipe: reddit-login.recipe.json (Phase 1 complete)
# But then: Start new browser, navigate to Reddit, explore login
# Cost wasted: $0.15

# CORRECT:
# Recipe exists
# Then: Load recipe, test Phase 2 with existing selectors
# Cost: $0.0015
```

### ❌ Mistake 3: Not Update Registry After Phase 2 Success

```bash
# WRONG:
# Phase 2 test succeeds, Reddit login works
# But forget to update RECIPE_REGISTRY.md
# Next LLM still thinks: "Phase 2 PENDING"

# CORRECT:
# Phase 2 test succeeds
# Update RECIPE_REGISTRY.md: "Phase 2 PENDING" → "Phase 2 READY"
# Commit: "docs(registry): Phase 2 verified for reddit-login"
# Next LLM immediately knows: use Phase 2 (not Phase 1)
```

### ❌ Mistake 4: Not Link Recipe to PrimeWiki

```bash
# WRONG:
# Create recipe/producthunt-launch.recipe.json
# Create primewiki/producthunt-structure.primewiki.md
# But don't mention in registry which recipe uses which PrimeWiki

# CORRECT:
# In RECIPE_REGISTRY.md, add:
#   Related Recipes: producthunt-structure.primewiki.md
# In PRIMEWIKI_REGISTRY.md, add:
#   Related Recipes: producthunt-launch.recipe.json
# Enables easy lookup: "show me selectors for this recipe"
```

---

## INTEGRATION WITH CLAUDE.MD COMMANDS

### Check Registry at Session Start

Add to ~/.claude/config.json (auto-run at session start):

```json
{
  "startup_commands": [
    "/load-skills",
    "echo 'Querying RECIPE_REGISTRY.md for updated recipes...'",
    "grep -c 'recipe.json' /home/phuc/projects/solace-browser/RECIPE_REGISTRY.md"
  ]
}
```

### Query Registry Before Starting Task

When user says "automate LinkedIn profile":

1. Claude automatically queries: `grep -i "linkedin" RECIPE_REGISTRY.md`
2. Finds: `linkedin-profile-optimization-10-10.recipe.json (Phase 2 READY)`
3. Knows: Use Phase 2 (load recipe, execute, verify)
4. Skips: Phase 1 exploration (already done)

---

## FUTURE: Automated Registry Management

### Idea 1: /registry-query Command

```bash
/registry-query --site=reddit --type=login
# Returns: reddit-login.recipe.json exists, Phase 1 complete, Phase 2 pending

/registry-query --site=producthunt --exists
# Returns: Not found, no recipes or PrimeWiki nodes

/registry-query --status=phase2-ready --count
# Returns: 10 recipes ready for Phase 2 execution
```

### Idea 2: Auto-Validate Registry

```bash
python scripts/validate_registry.py
# Checks:
# - All recipes in /recipes/ are indexed in RECIPE_REGISTRY.md
# - All PrimeWiki nodes in /primewiki/ are indexed in PRIMEWIKI_REGISTRY.md
# - No broken links between recipe and PrimeWiki
# - All timestamps are recent
# - All costs are reasonable
# Reports any discrepancies
```

### Idea 3: Registry Update on Git Commit

```bash
# In .git/hooks/post-commit:
# - If recipe added: auto-update RECIPE_REGISTRY.md
# - If PrimeWiki added: auto-update PRIMEWIKI_REGISTRY.md
# - Verify consistency
# - Add registry update to commit if needed
```

---

## THE PRINCIPLE (Never Forget)

> **Registries are external memory for future LLMs. Without them, each session rediscoveres the same patterns, wastes compute, and loses knowledge. With them, we compound knowledge forever.**

**Without Registries:**
- Session 1: Explore Reddit, $0.15 cost
- Session 2: Explore Reddit again, $0.15 cost (forgot what we learned)
- Session 3: Explore Reddit again, $0.15 cost (repeat)
- Total: $0.45 wasted on redundant work

**With Registries:**
- Session 1: Explore Reddit, $0.15 cost, update RECIPE_REGISTRY + PRIMEWIKI_REGISTRY
- Session 2: Load recipe from registry, $0.0015 cost, 100x cheaper
- Session 3: Load recipe from registry, $0.0015 cost, 100x cheaper
- Total: $0.15 + $0.0015 + $0.0015 = $0.1530 (1000x cheaper per site)

**Multiply across 50 sites:**
- Without registries: $0.15 × 50 = $7.50 per session
- With registries: $0.0015 × 50 = $0.075 per session (100x cheaper)
- Over 365 days: $7.50 × 365 = $2,737.50 vs $27.38 (99% savings)

---

**Auth**: 65537 | **Northstar**: Phuc Forecast
**Status**: Production Ready | **Version**: 1.0
**Remember**: "Check the registry before you explore. Contribute to the registry after you learn."
