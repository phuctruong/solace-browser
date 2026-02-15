# REGISTRY CHEATSHEET - Copy/Paste Commands

**TL;DR**: Before automating ANYTHING, query the registries. This 30-second check saves 100x compute cost.

---

## Query Recipe Registry (30 seconds)

```bash
# Are there recipes for this site?
grep -i "SITE_NAME" RECIPE_REGISTRY.md

# Find all Phase 2 ready recipes
grep "Phase 2 READY" RECIPE_REGISTRY.md

# Find all Phase 2 pending recipes
grep "Phase 2 PENDING" RECIPE_REGISTRY.md

# Count production-ready recipes
grep "✅" RECIPE_REGISTRY.md | wc -l
```

## Query PrimeWiki Registry (30 seconds)

```bash
# Are there knowledge nodes for this site?
grep -i "SITE_NAME" PRIMEWIKI_REGISTRY.md

# Show all landmarks discovered for site
grep -A 2 "SITE_NAME" PRIMEWIKI_REGISTRY.md | grep Landmarks

# Show quality scores
grep "C-Score\|G-Score" PRIMEWIKI_REGISTRY.md
```

## Load Recipe (1 minute)

```bash
# What selectors are used?
cat recipes/RECIPE_NAME.recipe.json | jq '.portals'

# What's the reasoning?
cat recipes/RECIPE_NAME.recipe.json | jq '.reasoning'

# What are the dependencies?
cat recipes/RECIPE_NAME.recipe.json | jq '.dependencies'
```

## Load PrimeWiki (1 minute)

```bash
# What selectors are known?
cat primewiki/SITE.primewiki.json | jq '.selectors'

# What magic words exist?
cat primewiki/SITE.primewiki.json | jq '.magic_words'

# How many landmarks?
cat primewiki/SITE.primewiki.json | jq '.landmarks | length'
```

## Decide Phase (30 seconds)

```bash
# Recipe exists AND Phase 2 READY?
#  → Use Phase 2 (load recipe + cookies, execute, $0.0015)

# Recipe exists AND Phase 2 PENDING?
#  → Test Phase 2 (verify selectors still work, $0.0015)

# Recipe does NOT exist?
#  → Do Phase 1 (live exploration, $0.15)
#  → Create recipe + primewiki
#  → Update registries
```

## Update Registry After Phase 1 (5 minutes)

```bash
# Add recipe entry
echo "- new-site-login.recipe.json" >> RECIPE_REGISTRY.md
echo "  - Task: Login to [site]" >> RECIPE_REGISTRY.md
echo "  - Cost: $0.15 | Phase 2: $0.0015" >> RECIPE_REGISTRY.md
echo "  - Status: Phase 1 complete, Phase 2 pending" >> RECIPE_REGISTRY.md

# Add primewiki entry
echo "### [site]-auth-flow.primewiki.json" >> PRIMEWIKI_REGISTRY.md
echo "- Landmarks: NNN (form fields, buttons)" >> PRIMEWIKI_REGISTRY.md
echo "- Status: Phase 1 complete" >> PRIMEWIKI_REGISTRY.md

# Commit
git add RECIPE_REGISTRY.md PRIMEWIKI_REGISTRY.md && \
git commit -m "docs(registry): Phase 1 [site] exploration complete"
```

## Update Registry After Phase 2 (1 minute)

```bash
# If Phase 2 succeeds, update status
sed -i 's/Phase 2 PENDING/Phase 2 READY/' RECIPE_REGISTRY.md
sed -i 's/pending (not yet Phase 2 tested)/Phase 1 complete and Phase 2 verified/' PRIMEWIKI_REGISTRY.md

# Commit
git add RECIPE_REGISTRY.md PRIMEWIKI_REGISTRY.md && \
git commit -m "docs(registry): Phase 2 verified for [site]"
```

---

## Common Queries

```bash
# Show total recipes vs total Phase 2 ready
echo "Total recipes: $(grep '.recipe.json' RECIPE_REGISTRY.md | wc -l)"
echo "Phase 2 ready: $(grep 'Phase 2 READY' RECIPE_REGISTRY.md | wc -l)"

# Show cost breakdown
echo "Phase 1 total: $(grep 'Phase 1 Cost.*\$' RECIPE_REGISTRY.md | grep -o '\$[0-9.]*' | awk '{sum+=$1} END {print sum}')"

# Show all sites with selectors known
grep -B 2 "Selectors Found" PRIMEWIKI_REGISTRY.md | grep "###"

# Show sites ready for Phase 2 automation
grep "Phase 2 READY" RECIPE_REGISTRY.md | grep -o "^### [^/]*" | sort | uniq
```

---

## THE RULE (memorize this)

> Before you explore or automate anything:
> 1. Query RECIPE_REGISTRY.md (does recipe exist?)
> 2. Query PRIMEWIKI_REGISTRY.md (is site known?)
> 3. If yes → Load recipe/primewiki, use Phase 2 ($0.0015)
> 4. If no → Do Phase 1 exploration ($0.15), then update registries

**This rule, if followed, prevents 99.8% of wasted compute.**

---

## Key Files

- **RECIPE_REGISTRY.md** - All recipes, status, costs, dependencies
- **PRIMEWIKI_REGISTRY.md** - All knowledge nodes, selectors, landmarks
- **REGISTRY_LOOKUP.md** - Detailed guide with examples
- **POSTMORTEM.md** - Why these files exist (session mistakes analysis)
- **CLAUDE.md** - Updated with registry access patterns

---

## Time Cost Comparison

| Task | Without Registry | With Registry |
|------|-----------------|---------------|
| Check if site is known | 0 min (impossible) | 1 min |
| Load existing recipe | N/A | 1 min |
| Execute Phase 2 | N/A | 12 sec |
| Execute Phase 1 (if needed) | 20 min | 20 min |
| **Total per site (first time)** | **20 min** | **21 min** |
| **Total per site (repeat)** | **20 min** | **2.5 min** (8x faster) |

**Savings over 100 site automations: 2000 min → 210 min (90% time savings)**

---

**Auth**: 65537 | Keep this open while working on browser automation tasks.
