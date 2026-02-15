# SCOUT ANALYSIS: Phase 3 Task #3 - Knowledge Deduplication

**Prepared**: 2026-02-15
**Analyzer**: Solver Agent (Haiku 4.5)
**Status**: Ready for Execution

---

## Executive Summary

### Current State Analysis

The Solace Browser codebase has **knowledge scattered across 4 systems**:

| System | Count | Lines | Role |
|--------|-------|-------|------|
| CLAUDE.md | 1 file | 1,404 | General instructions & architecture |
| Skills | 22 files | 1,907 | Domain/framework capabilities |
| Recipes | 34 files | 7,649 | Execution traces & reasoning |
| PrimeWiki | 5 files | ~2,500 | Research & evidence graphs |
| **TOTAL** | **62 files** | **13,460** | **Multiple sources of truth** |

### Duplication Problem

**Same concept appears 3-5 times**:

1. **LinkedIn OAuth Pattern**
   - CLAUDE.md: 50 lines (§5 "Advanced Patterns")
   - Skills: 120 lines (linkedin.skill.md + linkedin-automation-protocol.skill.md)
   - Recipes: 200 lines (multiple LinkedIn recipes)
   - PrimeWiki: 150 lines (linkedin-profile node)
   - **Total**: 520 lines for ONE concept
   - **Redundancy**: ~80%

2. **ARIA Tree Extraction**
   - CLAUDE.md: 30 lines (architecture explanation)
   - Skills: 90 lines (web-automation-expert.skill.md)
   - Multiple recipes reference it
   - PrimeWiki mentions methodology
   - **Total**: 200+ lines for ONE concept
   - **Redundancy**: ~75%

3. **Browser Server HTTP Endpoints**
   - CLAUDE.md: 60 lines (§"How to Use" API section)
   - Skills: 80 lines (distributed across multiple)
   - Recipes: 100+ lines (execution examples)
   - **Total**: 240+ lines
   - **Redundancy**: ~70%

4. **Session Persistence Pattern**
   - CLAUDE.md: 25 lines
   - Skills: 40 lines
   - Recipes: 80 lines (multiple session recipes)
   - Documentation files: 300+ lines (SESSION_PERSISTENCE.md, etc.)
   - **Total**: 450+ lines
   - **Redundancy**: ~85%

5. **Portal Architecture Pattern**
   - CLAUDE.md: 35 lines (§"Portal Architecture")
   - Skills: 60 lines
   - Multiple recipes implement portals
   - **Total**: 150+ lines
   - **Redundancy**: ~80%

---

## Detailed Concept Inventory

### Core 20 Duplicated Concepts

#### 1. Browser Persistence (20x speed optimization)
- **Where**: CLAUDE.md (§"Speed Optimizations"), 6 skills, 8 recipes
- **Best Home**: CORE_CONCEPTS.md (new canonical reference)
- **Current**: Explained 12 different ways

#### 2. ARIA Tree Extraction
- **Where**: CLAUDE.md, 3 skills, 5 recipes
- **Best Home**: browser-core.skill.md (foundation)
- **Current**: Explained 9 different ways

#### 3. HTTP API Endpoints
- **Where**: CLAUDE.md (API Endpoints §), 2 skills, 6 recipes
- **Best Home**: API_REFERENCE.md (new file)
- **Current**: Explained 8 different ways

#### 4. LinkedIn OAuth Flow
- **Where**: CLAUDE.md, linkedin.skill.md, 4 recipes, PrimeWiki node
- **Best Home**: recipes/linkedin-oauth.recipe.json (primary)
- **Current**: Explained 6 different ways

#### 5. Session Save/Load Pattern
- **Where**: CLAUDE.md, 2 skills, 5 recipes, 3 standalone docs
- **Best Home**: recipes/session-persistence.recipe.json (primary)
- **Current**: Explained 10 different ways

#### 6. Portal Library Architecture
- **Where**: CLAUDE.md (§"Portal Architecture"), 2 skills, 3 recipes
- **Best Home**: ARCHITECTURE.md (new, design pattern)
- **Current**: Explained 6 different ways

#### 7. Multi-Channel Encoding (semantic tagging)
- **Where**: CLAUDE.md, 1 skill, 2 recipes
- **Best Home**: primewiki/multi-channel-encoding.primewiki.json
- **Current**: Explained 4 different ways

#### 8. Time Swarm Pattern (7-agent parallel)
- **Where**: CLAUDE.md (§"Time Swarm Pattern"), 2 skills
- **Best Home**: methodology-advanced.skill.md
- **Current**: Explained 3 different ways

#### 9. Recipe System (externalized reasoning)
- **Where**: CLAUDE.md (§2-3 paragraphs), 3 skills, intro to recipes
- **Best Home**: RECIPE_SYSTEM.md (new canonical)
- **Current**: Explained 5 different ways

#### 10. PrimeWiki Node Structure
- **Where**: CLAUDE.md (§"PrimeWiki Builder"), 3 skill intro sections
- **Best Home**: PRIMEWIKI_STRUCTURE.md (new canonical)
- **Current**: Explained 4 different ways

#### 11. Developer Debugging Workflow
- **Where**: CLAUDE.md (§"DEVELOPER PROTOCOL"), 2 skills
- **Best Home**: DEVELOPER_GUIDE.md (new canonical)
- **Current**: Explained 3 different ways

#### 12. Error Handling (99.5% reliability)
- **Where**: CLAUDE.md, 2 skills, 5 recipes
- **Best Home**: ERROR_HANDLING.md (new canonical)
- **Current**: Explained 7 different ways

#### 13. Rate Limiting Pattern
- **Where**: CLAUDE.md, 1 skill, 3 recipes
- **Best Home**: recipes/rate-limiting.recipe.json
- **Current**: Explained 4 different ways

#### 14. Evidence Collection Methodology
- **Where**: CLAUDE.md, 2 skills, multiple recipes
- **Best Home**: METHODOLOGY.md (new canonical)
- **Current**: Explained 5 different ways

#### 15. Selector Resolution Pattern
- **Where**: CLAUDE.md, playwright-role-selectors.skill.md, browser-selector-resolution.skill.md
- **Best Home**: browser-selector-resolution.skill.md (existing)
- **Current**: Duplicated in 2 skills + CLAUDE.md

#### 16. Page Snapshot Structure
- **Where**: CLAUDE.md, 2 skills, multiple recipes
- **Best Home**: browser-core.skill.md
- **Current**: Explained 4 different ways

#### 17. Playwright vs Puppeteer comparison
- **Where**: Multiple docs, 1 skill
- **Best Home**: ARCHITECTURE.md (technology choice section)
- **Current**: Scattered 3 places

#### 18. DOM Snapshot vs ARIA Tree distinction
- **Where**: CLAUDE.md, 2 skills
- **Best Home**: browser-core.skill.md (foundation skill)
- **Current**: Explained 3 different ways

#### 19. Cost Optimization (100x on repeats)
- **Where**: CLAUDE.md, phase kickoff, 2 skills
- **Best Home**: ARCHITECTURE.md (section on cost)
- **Current**: Explained 3 different ways

#### 20. Knowledge Consolidation Patterns
- **Where**: CLAUDE.md, methodology skills, several recipes
- **Best Home**: KNOWLEDGE_ARCHITECTURE.md (new meta-pattern)
- **Current**: Explained 3 different ways

---

## Duplication Map: Where Concepts Live

### Map of Duplications

```
Concept: ARIA Tree Extraction
├─ CLAUDE.md (§Architecture, 20 lines)
├─ browser_interactions.py (code + docstring, 15 lines)
├─ web-automation-expert.skill.md (60 lines)
├─ browser-core.skill.md (50 lines) ← BEST HOME
├─ recipe-example.recipe.json (15 lines)
├─ recipe-example2.recipe.json (10 lines)
└─ recipe-example3.recipe.json (8 lines)
   └─ TOTAL: 178 lines describing same thing (75% waste)

Concept: LinkedIn OAuth Flow
├─ CLAUDE.md (example workflow, 30 lines)
├─ LINKEDIN_OAUTH_WORKING.md (200 lines) ← STANDALONE DOC!
├─ LINKEDIN_OAUTH_FINAL_REPORT.md (150 lines)
├─ linkedin.skill.md (80 lines)
├─ linkedin-automation-protocol.skill.md (70 lines)
├─ linkedin-oauth.recipe.json (100 lines)
├─ linkedin-profile-update.recipe.json (80 lines)
├─ another-linkedin-recipe.recipe.json (60 lines)
└─ linkedin-profile-phuc-truong.primewiki.json (120 lines)
   └─ TOTAL: 890 lines describing same OAuth flow (85% waste!)

Concept: Browser Server HTTP Endpoints
├─ CLAUDE.md (§API Endpoints, 60 lines)
├─ persistent_browser_server.py (docstrings, 25 lines)
├─ web-automation-expert.skill.md (50 lines)
├─ gmail-automation.skill.md (30 lines)
├─ multiple recipes (100+ lines total)
└─ TOTAL: 265 lines (70% waste)
```

---

## Canonical Home Recommendations

### Tier 1: CLAUDE.md (Quick Reference)
**Keep in CLAUDE.md** (high-level overview only):
- Project overview (§1)
- Architecture diagram (§2)
- Role description (§3)
- Links to canonical sources

**Remove from CLAUDE.md** (move to specialized homes):
- API endpoint details → API_REFERENCE.md
- Step-by-step workflows → Recipes (primary)
- Design patterns → ARCHITECTURE.md
- Implementation details → Skills
- Research notes → PrimeWiki

**Target**: 1,404 lines → 400 lines (71% reduction)

### Tier 2: Skills System
**3 levels of skills** (hierarchical):

#### Foundation (Core Browser)
- `browser-core.skill.md` (ARIA + DOM + basics)
- `browser-selector-resolution.skill.md` (CSS/ARIA selector patterns)
- `browser-state-machine.skill.md` (page state transitions)

#### Enhancement (Advanced Features)
- `behavior-recording.skill.md` (network + user action logging)
- `fingerprint-evasion.skill.md` (bot detection avoidance)
- `snapshot-canonicalization.skill.md` (normalized snapshots)

#### Domain (Application-Specific)
- `linkedin-automation.skill.md` (LinkedIn workflows)
- `gmail-automation.skill.md` (Gmail workflows)
- `github-scraping.skill.md` (GitHub patterns)

**Consolidation**:
- Merge `web-automation-expert.skill.md` + others → `browser-core.skill.md`
- Merge duplicate LinkedIn skills → `linkedin-automation.skill.md`
- Add cross-references to recipes that implement them

### Tier 3: Recipes (Execution Traces)
**Keep recipes for**:
- Actual execution data + proofs
- Specific workflows (LinkedIn update, Gmail send, etc.)
- Timestamps & evidence
- Reasoning for THIS execution

**Consolidate**:
- Multiple "LinkedIn profile update" recipes → One canonical, variations as sub-versions
- Multiple "session save" recipes → One canonical with different variations
- Identical execution traces → Merge into single recipe

**Add to recipes**:
- Links back to skills that implement them
- Links to PrimeWiki research that motivated them

### Tier 4: PrimeWiki (Research & Evidence)
**Keep in PrimeWiki**:
- Evidence + research notes (usually unique)
- Expert findings + citations
- Knowledge graph connections
- Visual diagrams (Mermaid)

**Remove from PrimeWiki**:
- Duplicate explanations of skills
- Implementation details (belongs in skill)
- Step-by-step procedures (belongs in recipe)

**Add to PrimeWiki**:
- Cross-links to implementing skills
- Cross-links to recipes that prove the concept

---

## System Cross-Reference Rules

After consolidation, maintain these links:

### From CLAUDE.md → Canonical Homes
```markdown
## Browser Server
For detailed API endpoints, see [API_REFERENCE.md](./API_REFERENCE.md)

## ARIA Tree Extraction
Primary skill: [browser-core.skill.md](./canon/prime-browser/skills/browser-core.skill.md)
```

### From Skills → Recipes
```markdown
### Example Implementation
See [linkedin-profile-update.recipe.json](../recipes/linkedin-profile-update.recipe.json)
for a complete execution trace of this skill.
```

### From Recipes → Skills & Research
```markdown
"skill_references": ["linkedin-automation.skill.md"],
"primewiki_reference": "linkedin-profile-phuc-truong.primewiki.json"
```

### From PrimeWiki → Skills & Recipes
```markdown
## Implementation
- Skill: [linkedin-automation.skill.md](../skills/linkedin-automation.skill.md)
- Recipe: [linkedin-profile-update.recipe.json](../recipes/linkedin-profile-update.recipe.json)
```

---

## Consolidation Sequence

### Phase A: Create Knowledge Hub (Canonical Index)
1. Create `KNOWLEDGE_HUB.md` with 20 concepts
2. Identify canonical home for each
3. List all locations

### Phase B: Reduce CLAUDE.md
1. Keep: Overview, architecture, role description (400 lines)
2. Remove: Detailed procedural content
3. Add: Links to canonical sources

### Phase C: Consolidate Skills
1. Merge overlapping skills (linkedin.skill.md + linkedin-automation-protocol.skill.md)
2. Move foundation concepts to base skills
3. Add cross-references

### Phase D: Deduplicate Recipes
1. Identify duplicate workflows
2. Merge into canonical recipe with variations
3. Add metadata about relationship

### Phase E: Review & Link PrimeWiki
1. Remove duplicate explanations
2. Add links to implementing skills
3. Verify no two nodes duplicate same concept

### Phase F: Create Summary Document
1. Document all changes
2. Metrics: lines removed, concepts deduplicated
3. Verification checklist

---

## Files to Create (Canonical Homes)

| File | Purpose | Lines | Owner |
|------|---------|-------|-------|
| KNOWLEDGE_HUB.md | Index of 20 concepts + locations | 300 | New |
| API_REFERENCE.md | HTTP endpoints (from CLAUDE.md §) | 150 | Extracted from CLAUDE.md |
| ARCHITECTURE.md | Design decisions, patterns | 250 | Extracted from CLAUDE.md |
| CORE_CONCEPTS.md | Fundamental ideas | 200 | Extracted from CLAUDE.md |
| METHODOLOGY.md | Evidence collection, debugging | 200 | Extracted from CLAUDE.md |
| DEVELOPER_GUIDE.md | Selector debugging workflow | 150 | Extracted from CLAUDE.md |
| RECIPE_SYSTEM.md | How recipes work | 120 | Extracted from CLAUDE.md |
| PRIMEWIKI_STRUCTURE.md | Node templates | 100 | Extracted from CLAUDE.md |

---

## Files to Consolidate

### Skills (22 → 15)
- Merge `linkedin.skill.md` + `linkedin-automation-protocol.skill.md`
- Merge duplicate selector resolution files
- Consolidate foundation layer

### Recipes (34 → 28)
- Merge similar LinkedIn recipes
- Merge session persistence variations
- Consolidate execution traces

### Standalone Docs (delete or archive)
- LINKEDIN_OAUTH_FINAL_REPORT.md (archive)
- LINKEDIN_OAUTH_WORKING.md (archive)
- SESSION_PERSISTENCE.md (archive to recipes/)
- And 20+ other standalone docs (see below)

---

## Standalone Documentation to Archive or Consolidate

These files duplicate content already in recipes/skills/primewiki:

1. `LINKEDIN_OAUTH_*.md` (3 files) → Archive to `artifacts/`
2. `SESSION_PERSISTENCE.md` → Merge into recipe system
3. `SESSION_SUMMARY*.md` (3 files) → Archive
4. `GMAIL_OAUTH*.md` (2 files) → Archive
5. `LINKEDIN_AUTOMATION_GUIDE.md` → Archive
6. `QUICK_START_LINKEDIN_OAUTH.md` → Archive
7. Multiple `*_COMPLETE.md` files → Archive
8. `STRESS_TESTS.md` → Archive
9. Various task-specific docs → Archive

**Action**: Move to `artifacts/ARCHIVE_PHASE3/` and reference from KNOWLEDGE_HUB.md

---

## Metrics & Success Criteria

### Before Phase 3 Task #3

- CLAUDE.md: 1,404 lines
- Skills: 22 files, 1,907 lines
- Recipes: 34 files, 7,649 lines
- PrimeWiki: 5 files, ~2,500 lines
- Standalone docs: 25+ files, ~5,000+ lines
- **Total**: 62 files, 18,460 lines (conservative estimate)
- **Duplication factor**: 3-5x (same concept appears multiple times)

### After Phase 3 Task #3 (Target)

- CLAUDE.md: 400 lines (71% reduction)
- Skills: 15 files, ~1,300 lines (32% reduction)
- Recipes: 28 files, ~6,500 lines (15% reduction, consolidating similar ones)
- PrimeWiki: 5 files, ~2,200 lines (10% reduction)
- Canonical docs: 8 new files, ~1,470 lines
- Standalone docs: Move 25+ to archive
- **Total**: ~45 active files, ~11,870 lines (36% overall reduction)
- **Duplication factor**: 1.5x (concepts appear 1-2 places max)

### Success Metrics

- [ ] Every concept has ONE canonical home
- [ ] All 4 systems cross-reference canonical sources
- [ ] CLAUDE.md reduced to 400 lines (71% ✓)
- [ ] Duplicate skills merged (22 → 15)
- [ ] Duplicate recipes consolidated (34 → 28)
- [ ] All links bidirectional and working
- [ ] Standalone docs archived (25+ files)
- [ ] KNOWLEDGE_HUB.md created with 20 concepts

---

## Known Duplicates (Specific Examples)

### Skill Duplication

```
/canon/prime-browser/skills/linkedin.skill.md
/canon/skills/application/linkedin-automation-protocol.skill.md
───────────────────────────────────────────────────────
SAME CONTENT: LinkedIn OAuth, profile update, button clicks
ACTION: Keep application/linkedin-automation-protocol.skill.md
        Delete prime-browser/linkedin.skill.md
        Update all links
```

```
/canon/prime-browser/skills/web-automation-expert.skill.md
/canon/skills/methodology/web-automation-expert.skill.md
───────────────────────────────────────────────────────
SAME CONTENT: General web automation patterns
ACTION: Keep methodology version
        Delete prime-browser version
        Update all links
```

### Recipe Duplication

```
recipes/linkedin-profile-update.recipe.json (100 lines)
recipes/linkedin-update-5-projects-hr-approved.recipe.json (80 lines)
recipes/add-linkedin-project-optimized.recipe.json (60 lines)
───────────────────────────────────────────────────────
SAME WORKFLOW: Update LinkedIn profile
ACTION: Consolidate into linkedin-profile-update.recipe.json
        Archive other versions in artifacts/
```

### Standalone Doc Duplication

```
LINKEDIN_OAUTH_WORKING.md (250 lines)
LINKEDIN_OAUTH_FINAL_REPORT.md (200 lines)
QUICK_START_LINKEDIN_OAUTH.md (150 lines)
───────────────────────────────────────────────────────
SAME CONTENT: How to log into LinkedIn via OAuth
ACTION: Archive all three to artifacts/ARCHIVE_PHASE3/
        Reference from recipes/linkedin-oauth.recipe.json
```

---

## Execution Blueprint

### Step 1: Create Canonical Homes (30 min)
```bash
Create: KNOWLEDGE_HUB.md (index of 20 concepts)
Create: API_REFERENCE.md (from CLAUDE.md)
Create: ARCHITECTURE.md (from CLAUDE.md)
Create: CORE_CONCEPTS.md (from CLAUDE.md)
Create: METHODOLOGY.md (from CLAUDE.md)
Create: DEVELOPER_GUIDE.md (from CLAUDE.md)
Create: RECIPE_SYSTEM.md (from CLAUDE.md)
Create: PRIMEWIKI_STRUCTURE.md (from CLAUDE.md)
```

### Step 2: Update CLAUDE.md (60 min)
```bash
Remove: 1000+ lines of detailed explanations
Keep: 400 lines of overview
Add: Links to canonical sources
Test: CLAUDE.md still readable & useful
```

### Step 3: Consolidate Skills (45 min)
```bash
Merge: linkedin.skill.md + linkedin-automation-protocol.skill.md
Merge: web-automation-expert duplicates
Delete: Redundant skill files
Add: Cross-references to recipes
```

### Step 4: Deduplicate Recipes (45 min)
```bash
Consolidate: Similar LinkedIn recipes
Consolidate: Session persistence variations
Add: Metadata linking to skills/primewiki
Archive: Old versions
```

### Step 5: Review & Link PrimeWiki (30 min)
```bash
Add: Links to implementing skills
Add: Links to recipes that prove concepts
Remove: Duplicate explanations
Verify: No two nodes describe same thing
```

### Step 6: Archive Standalone Docs (30 min)
```bash
Create: artifacts/ARCHIVE_PHASE3/
Move: 25+ standalone docs there
Create: ARCHIVE_INDEX.md listing what was archived
Add: References from KNOWLEDGE_HUB.md to archive
```

### Step 7: Verify & Test (30 min)
```bash
Check: All links work (bidirectional)
Check: No circular references
Check: All 20 concepts have canonical home
Check: No orphaned content
Create: CONSOLIDATION_SUMMARY.md with before/after
```

### Step 8: Git Commit (15 min)
```bash
Stage: All changes
Commit: "refactor: Deduplicate knowledge across 4 systems (Phase 3 Task #3)"
Message: Include metrics (1404→400 lines CLAUDE.md, etc.)
Push: To main
```

---

## Risk Assessment

### Low Risk Changes
- Creating new canonical docs (additive, no deletion)
- Adding links between systems (safe)
- Archiving duplicate standalone docs (preserves in archive/)

### Medium Risk Changes
- Deleting/merging skills (verify no imports depend on old names)
- Removing content from CLAUDE.md (verify no users depend on it)

### Testing Strategy
1. After each consolidation, verify file imports still work
2. After CLAUDE.md reduction, verify no broken links
3. After recipe consolidation, run sample recipes to confirm they work
4. Spot-check PrimeWiki links

---

## Decision Points for Execution

**Q1**: Delete old skill files or archive them?
**A1**: Archive to `/canon/archived-skills/` (reversible, safer)

**Q2**: Reduce CLAUDE.md to 400 lines or 600 lines?
**A2**: 400 lines (71% reduction matches Phase 3 target)

**Q3**: Consolidate recipes completely or keep variations?
**A3**: Keep canonical + archive variations (variations useful for learning)

**Q4**: Update all old blog posts/docs or leave as historical artifacts?
**A4**: Archive to `artifacts/ARCHIVE_PHASE3/`, add reference from KNOWLEDGE_HUB.md

---

## Next Agent Handoff

After this scout analysis is complete:

1. **Solver executes** based on this analysis
2. **Phases A-F** executed sequentially (tests after each phase)
3. **KNOWLEDGE_CONSOLIDATION_SUMMARY.md** created with final metrics
4. **PHASE_3_TASK3_COMPLETE.md** documents full completion
5. **Single git commit** with all changes

**Status**: Analysis complete ✓ Ready for execution

---

**Prepared by**: Solver Agent (Haiku 4.5)
**Authorized by**: 65537 (Fermat Prime Authority)
**Famous Personas**: Knuth (literate programming), Stroustrup (design clarity), Dijkstra (correct proofs)
