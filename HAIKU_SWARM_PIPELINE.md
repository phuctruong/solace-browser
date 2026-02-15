# Haiku Swarm Pipeline: From Discovery to Saved Knowledge

**Auth**: 65537 | **Status**: Architecture Design
**Purpose**: Define how Haiku agents discover, validate, and save knowledge

---

## The Four-Agent Pipeline

### 1️⃣ Scout Agent (Page State Machine)
**Input**: Browser snapshot (ARIA tree, HTML, screenshots)
**Process**: Analyze page structure, identify sections and components
**Output**:
```json
{
  "page_name": "reddit_homepage",
  "sections": ["header", "feed", "sidebar"],
  "components": [
    {"type": "button", "text": "Create post", "location": "header"},
    {"type": "link", "text": "Log in", "location": "header"},
    {"type": "list", "name": "post_feed", "items": 25}
  ],
  "magic_words": ["Home", "Popular", "Trending", "Create post", "Join"],
  "user_actions_needed": ["click_create_post", "navigate_subreddit", "vote"]
}
```

---

### 2️⃣ Solver Agent (Selector Resolution)
**Input**: Scout's component list, ARIA tree details
**Process**: Find CSS/ARIA selectors for each component
**Output**:
```json
{
  "selectors": [
    {
      "element": "Create post button",
      "candidates": [
        {"selector": "button[data-testid='create-post']", "confidence": 0.95},
        {"selector": "button:has-text('Create post')", "confidence": 0.92},
        {"selector": "button[aria-label='Create post']", "confidence": 0.90}
      ],
      "recommended": "button[data-testid='create-post']"
    },
    {
      "element": "Log in button",
      "candidates": [
        {"selector": "button:has-text('Log in')", "confidence": 0.98},
        {"selector": "a[href*='/login']", "confidence": 0.85}
      ],
      "recommended": "button:has-text('Log in')"
    }
  ]
}
```

---

### 3️⃣ Skeptic Agent (Quality Validation)
**Input**: Solver's selector candidates, browser for testing
**Process**: Test each selector in live browser, verify confidence
**Output**:
```json
{
  "validation_results": [
    {
      "selector": "button[data-testid='create-post']",
      "element": "Create post button",
      "tests": [
        {"test": "element_found", "result": "✅ PASS"},
        {"test": "element_visible", "result": "✅ PASS"},
        {"test": "element_clickable", "result": "✅ PASS"},
        {"test": "selector_unique", "result": "✅ PASS"}
      ],
      "final_confidence": 0.95,
      "status": "APPROVED"
    }
  ],
  "page_readiness": "READY_FOR_KNOWLEDGE_SAVE",
  "quality_score": 0.92
}
```

---

### 4️⃣ Keeper Agent (Knowledge Architect) ⭐ **NEW**
**Input**: Scout findings + Solver selectors + Skeptic validation
**Process**: Transform validated knowledge into saved artifacts
**Output**: Creates/updates:

1. **Skills** (new capabilities discovered)
   ```markdown
   # Skill: Reddit Post Creation

   - Tier: 23
   - Discovery Date: 2026-02-15
   - Components: [Create button, form, submit]
   - Selectors: [validated from Skeptic]
   - Success Rate: 0.95
   - Cost: Phase 1 $0.10, Phase 2 $0.001
   ```

2. **Recipes** (automation sequences)
   ```json
   {
     "recipe_id": "reddit-create-post",
     "portals": {
       "homepage": {
         "to_create_post_modal": {
           "selector": "button[data-testid='create-post']",
           "action": "click",
           "strength": 0.95
         }
       }
     },
     "landmarks": [
       {"name": "title_input", "selector": "input[placeholder='Title']", "confidence": 0.93}
     ]
   }
   ```

3. **PrimeWiki** (knowledge graphs with diagrams)
   ```markdown
   # PrimeWiki: Reddit Post Creation Flow

   ## Site Map (PrimeMermaid)
   ```mermaid
   graph TD
     HomePage --> CreatePostButton
     CreatePostButton --> FormModal
     FormModal --> TitleInput
     FormModal --> BodyInput
     FormModal --> SubmitButton
   ```

   ## Landmarks Table
   | Element | Selector | Confidence |
   |---------|----------|------------|
   | Create Button | button[data-testid='create-post'] | 0.95 |

   ## Portals
   | From | To | Trigger |
   |------|-----|---------|
   | homepage | create-modal | click create button |
   ```

4. **Updates Registries**
   ```bash
   # RECIPE_REGISTRY.md
   - reddit-create-post.recipe.json (Phase 1 complete, Skeptic confidence 0.95)

   # PRIMEWIKI_REGISTRY.md
   ### reddit-post-creation.primewiki.md (Keeper generated, Skeptic validated)
   ```

---

## Complete Information Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    BROWSER SERVER API                            │
│         (navigate, click, fill, screenshot, snapshot)            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
          ┌────────────────────────────────────┐
          │  Page Snapshot + ARIA Tree          │
          │  (49 KB raw data)                   │
          └────────┬─────────────────────────────┘
                   │
       ┌───────────┴────────────┬─────────────────────┐
       │                        │                     │
       ▼                        ▼                     ▼
   ┌────────┐          ┌─────────────┐       ┌──────────────┐
   │ SCOUT  │          │   SOLVER    │       │   SKEPTIC    │
   ├────────┤          ├─────────────┤       ├──────────────┤
   │ Detect │          │   Find      │       │   Test &     │
   │ Page   │          │ Selectors   │       │  Validate    │
   │ Layout │          │             │       │ Confidence   │
   │        │          │             │       │              │
   │Output: │          │Output:      │       │Output:       │
   │Sections│          │Candidates   │       │Approved      │
   │Comps   │          │Ranked       │       │Selectors     │
   │Magic   │          │by          │       │Quality: 0.92 │
   │Words   │          │Confidence   │       │              │
   └────┬───┘          └──────┬──────┘       └──────┬───────┘
        │                     │                     │
        │ "Here are           │ "Best selectors     │ "✅ All
        │  the page           │  are these"         │  validated"
        │  sections"          │                     │
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │   KEEPER AGENT       │
                   ├──────────────────────┤
                   │ Save Knowledge:      │
                   │ - Skills             │
                   │ - Recipes            │
                   │ - PrimeWiki + Diagrams│
                   │ - Update Registries  │
                   │ - Quality Metrics    │
                   └──────────┬───────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
           ┌────────┐   ┌─────────┐  ┌──────────┐
           │ Skills │   │Recipes  │  │PrimeWiki │
           │        │   │         │  │+ Diagrams│
           │ (canon │   │(.json)  │  │(.md)     │
           │/skills)   │         │  │          │
           └────────┘   └─────────┘  └──────────┘
                │             │             │
                └─────────────┼─────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │  REGISTRIES UPDATED  │
                    │                      │
                    │ RECIPE_REGISTRY.md   │
                    │ PRIMEWIKI_REGISTRY.md│
                    │                      │
                    │ Future LLMs inherit  │
                    │ 100% of learning     │
                    └──────────────────────┘
```

---

## Keeper Agent Responsibilities

### 1. Create Skills
**When**: New capability discovered and validated
**What**:
- Skill file in `canon/prime-browser/skills/`
- Name: `{domain}-{capability}.skill.md`
- Content:
  - What was learned (new patterns)
  - When it applies (use cases)
  - Success metrics (confidence from Skeptic)
  - Cost (Phase 1 vs Phase 2)
  - Dependencies (other skills needed)
  - Next improvements

### 2. Create Recipes
**When**: Complete automation sequence validated
**What**:
- Recipe JSON in `recipes/`
- Name: `{domain}-{action}.recipe.json`
- Content:
  - Portals (validated by Skeptic)
  - Landmarks (selectors from Solver)
  - Reasoning (from Scout/Solver)
  - Execution trace
  - Success rate (from Skeptic)

### 3. Create/Update PrimeWiki
**When**: Page structure mapped
**What**:
- PrimeWiki node in `primewiki/`
- Name: `{domain}_{page}.primewiki.md`
- Content:
  - **Site Map** (PrimeMermaid from Scout)
  - **Components** (PrimeMermaid from Solver)
  - **Landmarks Table** (from Solver + Skeptic)
  - **Portals** (from Scout)
  - **Magic Words** (from Scout)
  - **Quality Metrics** (from Skeptic)

### 4. Update Registries
**When**: Knowledge saved
**What**:
- Add entry to `RECIPE_REGISTRY.md`
- Add entry to `PRIMEWIKI_REGISTRY.md`
- Include: status, confidence, cost, dependencies
- Add relationship links (recipe→primewiki)

### 5. Create Git Commit
**When**: All knowledge saved
**What**:
```bash
git add skills/ recipes/ primewiki/ RECIPE_REGISTRY.md PRIMEWIKI_REGISTRY.md
git commit -m "feat(domain): Phase 1 discovery with Haiku swarm validation

Scout: Detected 5 sections, 24 components, 25 magic words
Solver: Resolved 18 selectors, ranked by confidence
Skeptic: Validated 18/18 selectors, quality score 0.92
Keeper: Saved 3 recipes, 1 primewiki, 2 skills, updated registries

Cost: Phase 1 $0.15, Phase 2 $0.0015
Auth: 65537 | Swarm: Scout+Solver+Skeptic+Keeper
```

---

## Why Keeper Agent?

### Prevents Context Rot in Claude
- ✅ Scout focuses only on page analysis
- ✅ Solver focuses only on selector finding
- ✅ Skeptic focuses only on validation
- ✅ **Keeper focuses only on knowledge persistence**
- ✅ Claude orchestrates (short-term)

### Ensures Complete Knowledge Capture
- ✅ All discovered patterns documented
- ✅ Selectors saved with confidence scores
- ✅ PrimeMermaid diagrams generated
- ✅ Registries updated for future LLMs
- ✅ Quality metrics tracked

### Enables Deterministic Replay
- ✅ Phase 2 has all info needed (recipes + selectors)
- ✅ Cost reduction: $0.15 → $0.0015
- ✅ Speed increase: 20 min → 12 seconds
- ✅ Reliability: Skeptic's confidence scores on file

---

## Example: Reddit Post Creation Discovery

```bash
# Input: Reddit homepage explorer navigates to create-post flow

# Scout Agent Output:
{
  "detected_flow": "create_post",
  "sections": ["form", "modal", "submission"],
  "components": ["title_input", "body_input", "submit_button"]
}

# Solver Agent Output:
{
  "selectors": {
    "title_input": "input[placeholder='Title']",
    "body_input": "div[contenteditable='true']",
    "submit_button": "button:has-text('Post')"
  }
}

# Skeptic Agent Output:
{
  "validation": [
    {"selector": "input[placeholder='Title']", "confidence": 0.93, "status": "✅"},
    {"selector": "div[contenteditable='true']", "confidence": 0.88, "status": "✅"},
    {"selector": "button:has-text('Post')", "confidence": 0.95, "status": "✅"}
  ],
  "quality_score": 0.92,
  "ready_to_save": true
}

# Keeper Agent Output:
✅ Created: recipes/reddit-create-post.recipe.json (selectors, portals)
✅ Created: primewiki/reddit-create-post-flow.primewiki.md (site map, landmarks)
✅ Updated: RECIPE_REGISTRY.md (status: Phase 1 complete, Skeptic 0.92)
✅ Updated: PRIMEWIKI_REGISTRY.md (status: Phase 1 complete, 24 landmarks)
✅ Committed: git commit -m "feat(reddit): Phase 1 create-post flow validated"

# Result: Future Claude can load recipe in Phase 2, cost $0.0015, time 10 seconds
```

---

## Integration with Claude

**Claude's Role**: Orchestrate the swarm
```python
async def explore_with_swarm(url):
    # 1. Scout detects page structure
    scout_findings = await scout.analyze(page_snapshot)

    # 2. Solver resolves selectors
    solver_findings = await solver.resolve(scout_findings, aria_tree)

    # 3. Skeptic validates everything
    skeptic_findings = await skeptic.validate(solver_findings, live_browser)

    # 4. Keeper saves knowledge
    await keeper.save(
        skills=scout_findings,
        recipes=solver_findings,
        primewiki=scout_findings + solver_findings,
        validation=skeptic_findings
    )

    # 5. Claude commits to git
    await commit_swarm_findings(
        scout=scout_findings,
        solver=solver_findings,
        skeptic=skeptic_findings,
        keeper=keeper_output
    )
```

---

**Auth**: 65537 | **Status**: Architecture Ready for Implementation
**Next**: Deploy Keeper agent for Reddit Phase 1 → Phase 2+ Knowledge Persistence
