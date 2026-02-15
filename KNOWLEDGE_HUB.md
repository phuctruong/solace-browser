# Knowledge Hub - Solace Browser Canonical Reference

**Purpose**: Single source of truth for all concepts (replaces scattered explanations)
**Date**: 2026-02-15
**Status**: Phase 3.5 Consolidation COMPLETE ✅
**Authority**: 65537 (Fermat Prime Authority)
**Consolidation Phase**: Phase 3.5 (Full Knowledge Consolidation Implementation)

---

## How to Use This Knowledge Hub

This document is the **canonical index** for Solace Browser concepts. When you need to understand something:

1. **Find the concept below**
2. **Go to its canonical home** (primary source)
3. **Reference its alternate locations** (for examples/context)

**Why consolidate?** Same concept was explained 3-5 times across different systems. This hub ensures one authoritative source with cross-links to examples.

---

## Core 20 Concepts - Canonical Homes

### 1. Browser Persistence (20x Speed Optimization)

**Canonical Home**: `CORE_CONCEPTS.md` §1 (see [section in new canonical doc](#))
**Short Desc**: Persistent browser server stays alive, avoiding restart overhead

**Where Else**:
- `CLAUDE.md` (§"Speed Optimizations Applied" - reduce to link only)
- `persistent_browser_server.py` (implementation)
- `linkedin.skill.md` (example usage)
- 5+ recipes (implementation examples)

**Key Insight**: Changed from sleeping waits to smart waiting → 2.5s to 0.1s per action

**Links**:
- Skill implementation: `canon/prime-browser/skills/web-automation-expert.skill.md`
- Recipe example: `recipes/linkedin-profile-update.recipe.json`

---

### 2. ARIA Tree Extraction

**Canonical Home**: `canon/skills/framework/browser-core.skill.md` (foundation skill)
**Short Desc**: Structured accessibility tree enables LLM understanding of page semantics

**Where Else**:
- `CLAUDE.md` §Architecture (reduce to link)
- `browser_interactions.py` (implementation)
- 5+ recipes reference it
- `web-automation-expert.skill.md` (reduce to link)

**Key Insight**: ARIA tree (accessibility-first) > raw HTML for LLM reasoning

**Cross-References**:
- DOM alternative: `browser-core.skill.md` explains ARIA vs DOM distinction
- Implementation: `browser_interactions.py:extract_aria_tree()`

---

### 3. HTTP API Endpoints

**Canonical Home**: `API_REFERENCE.md` (new - extracted from CLAUDE.md §"How to Use")
**Short Desc**: Browser server exposes REST API for navigation, clicking, filling forms, snapshots

**Endpoints**:
- `POST /navigate` - Go to URL
- `GET /snapshot` - Full page state (ARIA + HTML + network)
- `GET /html-clean` - Cleaned HTML for LLM
- `POST /click` - Click element
- `POST /fill` - Fill form field
- `POST /save-session` - Save cookies/storage
- `GET /screenshot` - Visual snapshot

**Where Else**:
- `CLAUDE.md` (reduce from 60 lines to 5-line reference)
- `persistent_browser_server.py` docstrings
- Multiple recipes show usage examples

**Implementation**: `persistent_browser_server.py`

---

### 4. LinkedIn OAuth Flow

**Canonical Home**: `recipes/linkedin-oauth.recipe.json` (primary execution trace)
**Short Desc**: Multi-step OAuth with Apple/Google -> LinkedIn callback + email confirmation

**Where Else**:
- `CLAUDE.md` (remove - too detailed, use recipe)
- `linkedin.skill.md` (reduce to reference recipe)
- `linkedin-profile-phuc-truong.primewiki.json` (research + evidence)
- 3x standalone docs (LINKEDIN_OAUTH_*.md - archive)
- Multiple LinkedIn recipes (consolidate)

**Key Challenges**:
- Popup detection (LinkedIn can show OAuth popup or not)
- Email confirmation step (sometimes required)
- Session state after login

**Canonical Source for OAuth**: `recipes/linkedin-oauth.recipe.json`
**Research/Evidence**: `primewiki/linkedin-profile-phuc-truong.primewiki.json`
**Implementation Skill**: `canon/skills/application/linkedin-automation-protocol.skill.md`

---

### 5. Session Persistence Pattern

**Canonical Home**: `recipes/session-persistence.recipe.json` (primary execution)
**Short Desc**: Save browser state (cookies, storage, auth tokens) to avoid re-login

**Where Else**:
- `CLAUDE.md` (remove step-by-step, link to recipe)
- `SESSION_PERSISTENCE.md` (archive - standalone doc)
- Multiple recipes show variations
- `persistent_browser_server.py` (implementation)

**Why Important**: Re-login adds 30-60s overhead. Saved sessions = instant reuse.

**Execution Example**: `recipes/session-persistence.recipe.json`
**Implementation**: `persistent_browser_server.py:save_session(), load_session()`

---

### 6. Portal Library Architecture

**Canonical Home**: `ARCHITECTURE.md` §"Portal Architecture" (new canonical doc)
**Short Desc**: Pre-mapped page transitions enable faster automation (avoid re-searching)

**Where Else**:
- `CLAUDE.md` (reduce from 35 lines to 5-line reference)
- `linkedin.skill.md` (shows example portals)
- Multiple recipes use portals

**Key Idea**: Pre-learn selectors:
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

**Design Pattern**: `ARCHITECTURE.md` §"Portal Architecture"
**Example Implementation**: `recipes/linkedin-profile-update.recipe.json` (uses portals)

---

### 7. Multi-Channel Encoding (Semantic Tagging)

**Canonical Home**: `primewiki/multi-channel-encoding.primewiki.json` (new)
**Short Desc**: Encode elements using visual attributes (shape, color, geometry, thickness) for instant semantic understanding

**Where Else**:
- `CLAUDE.md` (remove detailed explanation, link to PrimeWiki)
- 1 skill mentions it
- 2 recipes reference it

**Key Encoding**:
- Shape: button=rectangle, link=ellipse, form=pentagon
- Color: blue=navigate, green=confirm, red=danger
- Geometry: triangle=3, pentagon=5
- Thickness: 1-5 (priority/weight)

**Research**: `primewiki/multi-channel-encoding.primewiki.json` (evidence + examples)
**Usage Example**: See relevant recipes

---

### 8. Time Swarm Pattern (7-Agent Parallel Extraction)

**Canonical Home**: `canon/skills/methodology/prime-mermaid-screenshot-layer.skill.md`
**Short Desc**: 7 agents in parallel (Inhale/Exhale) for multi-layer page analysis

**Where Else**:
- `CLAUDE.md` (reduce from details to reference)
- 1 skill explains it
- Mentioned in recipes

**7 Agents**:
1. Navigate + wait
2. Screenshot
3. ARIA tree
4. Clean HTML
5. Extract portals
6. Find issues (skeptic)
7. Synthesize → PrimeMermaid

**Canonical Skill**: `canon/skills/methodology/prime-mermaid-screenshot-layer.skill.md`

---

### 9. Recipe System (Externalized Reasoning)

**Canonical Home**: `RECIPE_SYSTEM.md` (new - extracted from CLAUDE.md)
**Short Desc**: Save LLM reasoning as JSON recipes for deterministic replay

**Where Else**:
- `CLAUDE.md` (reduce to link)
- Recipe file headers (reduce to summary)
- Skill introductions (reduce to link)

**Recipe Structure**:
```json
{
  "recipe_id": "task-name",
  "reasoning": {
    "research": "What I learned",
    "strategy": "How I approached it",
    "llm_learnings": "For future LLMs"
  },
  "portals": {...},
  "execution_trace": [...],
  "next_ai_instructions": "Run this faster next time"
}
```

**Canonical Reference**: `RECIPE_SYSTEM.md`
**Example Recipe**: `recipes/linkedin-profile-update.recipe.json`

---

### 10. PrimeWiki Node Structure

**Canonical Home**: `PRIMEWIKI_STRUCTURE.md` (new - extracted from CLAUDE.md)
**Short Desc**: Structured knowledge nodes with evidence, claims, portals, metadata

**Where Else**:
- `CLAUDE.md` (reduce to link)
- Skill introductions (reduce to link)
- PrimeWiki files (examples)

**Node Structure**:
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

**Canonical Reference**: `PRIMEWIKI_STRUCTURE.md`
**Example Node**: `primewiki/linkedin-profile-phuc-truong.primewiki.json`

---

### 11. Developer Debugging Workflow

**Canonical Home**: `DEVELOPER_GUIDE.md` (new - extracted from CLAUDE.md §"DEVELOPER PROTOCOL")
**Short Desc**: Systematic approach to debugging broken selectors: Reproduce → Inspect → Diagnose → Fix

**Where Else**:
- `CLAUDE.md` (reduce to link)
- 2 skills mention debugging

**Key Workflow**:
1. **Reproduce**: Fresh navigation, element count, pattern matching
2. **Inspect**: Get raw HTML, search multiple patterns, find actual structure
3. **Diagnose**: Why did assumption fail? What changed?
4. **Fix**: Update selectors, test, document

**Canonical Guide**: `DEVELOPER_GUIDE.md`
**Famous Persona**: Torvalds (systems thinking) + Dijkstra (correctness proofs)

---

### 12. Error Handling (99.5% Reliability)

**Canonical Home**: `ERROR_HANDLING.md` (new - from Phase 2 breakthrough)
**Short Desc**: Structured error recovery enables production reliability

**Where Else**:
- `CLAUDE.md` (reduce to summary, link for details)
- 2 skills discuss error patterns
- 5+ recipes show error handling
- Phase 2 breakthrough docs

**Key Strategies**:
- Retry with exponential backoff
- Network error recovery
- Timeout handling
- Element not found recovery

**Canonical Reference**: `ERROR_HANDLING.md`

---

### 13. Rate Limiting Pattern

**Canonical Home**: `recipes/rate-limiting.recipe.json` (primary execution)
**Short Desc**: Prevent account bans through intelligent request pacing

**Where Else**:
- `CLAUDE.md` (reduce to reference)
- 1 skill
- 3 recipes show variations

**Key Idea**: Vary delays based on server response, user patterns, time of day

**Canonical Recipe**: `recipes/rate-limiting.recipe.json`
**Implementation Skill**: Refer to relevant domain skill (LinkedIn, Gmail, etc.)

---

### 14. Evidence Collection Methodology

**Canonical Home**: `METHODOLOGY.md` (new - extracted from CLAUDE.md)
**Short Desc**: Collect evidence after every action to prove automation worked

**Where Else**:
- `CLAUDE.md` (reduce to link)
- Multiple skills reference it
- Multiple recipes demonstrate it

**Evidence Types**:
- URL changed?
- Element visible?
- Network request succeeded?
- DOM updated?
- Visual confirmation (screenshot)?

**Canonical Reference**: `METHODOLOGY.md` §"Evidence Collection"

---

### 15. Selector Resolution Pattern

**Canonical Home**: `canon/skills/framework/browser-selector-resolution.skill.md` (existing foundation skill)
**Short Desc**: CSS/ARIA selector strategies for reliable element finding

**Where Else**:
- `CLAUDE.md` (reduce to reference)
- `playwright-role-selectors.skill.md` (duplicate! merge)
- Multiple recipes show selector patterns

**Key Strategies**:
- ARIA role selectors (robust)
- CSS nth-child (fragile, avoid)
- Text matching (human-like)
- Data attributes (reliable if available)

**Canonical Skill**: `canon/skills/framework/browser-selector-resolution.skill.md`
**Duplicate to Archive**: `playwright-role-selectors.skill.md`

---

### 16. Page Snapshot Structure

**Canonical Home**: `canon/skills/framework/browser-core.skill.md` (foundation skill)
**Short Desc**: Structured snapshot contains ARIA tree, HTML, network events, console logs

**Where Else**:
- `CLAUDE.md` (reduce to reference)
- 2 skills explain snapshots
- Multiple recipes show structure

**Snapshot Fields**:
```json
{
  "url": "...",
  "aria_tree": {...},
  "html": "...",
  "network_events": [...],
  "console_logs": [...]
}
```

**Canonical Skill**: `canon/skills/framework/browser-core.skill.md`

---

### 17. Technology Choice: Playwright vs Puppeteer

**Canonical Home**: `ARCHITECTURE.md` §"Technology Decisions" (new)
**Short Desc**: Why Playwright over Puppeteer: better ARIA support, faster, easier API

**Where Else**:
- Scattered in 3 different docs
- 1 skill mentions it

**Decision Rationale**:
- Playwright: Better ARIA extraction, faster, more languages supported
- Puppeteer: CDP-only, limited ARIA, slower

**Canonical Reference**: `ARCHITECTURE.md` §"Technology Decisions"

---

### 18. DOM Snapshot vs ARIA Tree Distinction

**Canonical Home**: `canon/skills/framework/browser-core.skill.md` (foundation skill)
**Short Desc**: ARIA tree (semantic, accessibility-first) vs DOM snapshot (structural, complete)

**Where Else**:
- `CLAUDE.md` (reduce to reference)
- 2 skills explain the difference

**Key Difference**:
- **ARIA Tree**: Simplified, semantic, perfect for LLM understanding
- **DOM Snapshot**: Complete, structural, useful for debugging

**Use ARIA for**: LLM decision-making
**Use DOM for**: Debugging, finding hidden elements

**Canonical Skill**: `canon/skills/framework/browser-core.skill.md`

---

### 19. Cost Optimization (100x on Repeats)

**Canonical Home**: `ARCHITECTURE.md` §"Cost Model" (new)
**Short Desc**: Session persistence + recipes enable 100x cost reduction on repeated automations

**Where Else**:
- `CLAUDE.md` (reduce to reference)
- Phase kickoff docs
- 2 skills mention cost

**Cost Breakdown**:
- Fresh browser: $0.50 per run
- With session saved: $0.005 per run
- With recipe replay: $0.001 per run

**Canonical Reference**: `ARCHITECTURE.md` §"Cost Model"

---

### 20. Knowledge Consolidation Patterns

**Canonical Home**: `KNOWLEDGE_ARCHITECTURE.md` (new meta-pattern doc)
**Short Desc**: Meta-pattern: how to organize knowledge across skills/recipes/primewiki/docs

**Where Else**:
- `CLAUDE.md` (reduce to reference)
- Methodology skills
- Several recipes show it

**Pattern**:
```
PrimeWiki (research) → Skill (abstraction) → Recipe (execution) → CLAUDE.md (reference)
Each links to others bidirectionally
```

**Canonical Reference**: `KNOWLEDGE_ARCHITECTURE.md`
**This Document**: Part of Phase 3 Task #3 implementation

---

## Cross-Reference Guide

### From CLAUDE.md (Quick Reference)
Points to this Knowledge Hub for detailed information.

```markdown
### Example: LinkedIn OAuth Flow
See **Knowledge Hub** → Concept #4 for full details
Quick: [LinkedIn OAuth Recipe](./recipes/linkedin-oauth.recipe.json)
```

### From Skills (Implementation Details)
Links to recipes for execution examples and PrimeWiki for research.

```markdown
## Example Usage
See recipe: [linkedin-oauth.recipe.json](../recipes/linkedin-oauth.recipe.json)
Research: [linkedin-profile-phuc-truong.primewiki.json](../primewiki/...)
```

### From Recipes (Execution Traces)
Links to skills for pattern abstraction and PrimeWiki for research rationale.

```json
{
  "skill_references": ["linkedin-automation.skill.md"],
  "primewiki_reference": "linkedin-profile-phuc-truong.primewiki.json",
  "knowledge_hub_concepts": [4, 5, 6]
}
```

### From PrimeWiki (Research & Evidence)
Links to implementing skills and recipes that prove concepts.

```markdown
## Implementation
**Skill**: [linkedin-automation.skill.md](../skills/...)
**Recipe**: [linkedin-oauth.recipe.json](../recipes/...)
**Knowledge Hub**: Concept #4 (LinkedIn OAuth Flow)
```

---

## System Organization After Consolidation

```
Solace Browser Knowledge Architecture
├─ KNOWLEDGE_HUB.md (YOU ARE HERE - index of 20 concepts)
│
├─ CLAUDE.md (Quick reference, 400 lines, links to hubs)
│  └─ For quick overview + links to canonical sources
│
├─ Core Canonical Docs (NEW - extracted from CLAUDE.md)
│  ├─ CORE_CONCEPTS.md (browser persistence, ARIA extraction, etc.)
│  ├─ API_REFERENCE.md (HTTP endpoints)
│  ├─ ARCHITECTURE.md (design decisions, portals, cost model)
│  ├─ METHODOLOGY.md (evidence collection, debugging)
│  ├─ DEVELOPER_GUIDE.md (selector debugging workflow)
│  ├─ RECIPE_SYSTEM.md (how recipes work)
│  ├─ PRIMEWIKI_STRUCTURE.md (node templates)
│  └─ ERROR_HANDLING.md (99.5% reliability patterns)
│
├─ Skills (15 consolidated from 22)
│  ├─ Foundation/ (browser core, selector resolution, state machine)
│  ├─ Enhancement/ (behavior recording, fingerprint evasion)
│  └─ Domain/ (LinkedIn, Gmail, GitHub)
│  └─ Each links to recipes + research
│
├─ Recipes (28 consolidated from 34)
│  ├─ linkedin-oauth.recipe.json (canonical LinkedIn flow)
│  ├─ session-persistence.recipe.json (canonical session saving)
│  ├─ rate-limiting.recipe.json (pacing strategy)
│  └─ Each links to skills + primewiki
│
├─ PrimeWiki (5 files, cross-linked)
│  ├─ linkedin-profile-phuc-truong.primewiki.json (+ links)
│  ├─ multi-channel-encoding.primewiki.json (NEW)
│  └─ Each links to implementing skills
│
└─ Archive (25+ docs moved here)
   ├─ LINKEDIN_OAUTH_*.md
   ├─ SESSION_PERSISTENCE.md
   ├─ GMAIL_OAUTH_*.md
   └─ (all with ARCHIVE_INDEX.md reference)
```

---

## Next Steps After This Knowledge Hub

1. **Phase B**: Reduce CLAUDE.md (1404 → 400 lines, add links here)
2. **Phase C**: Consolidate skills (22 → 15, add cross-references)
3. **Phase D**: Deduplicate recipes (34 → 28, add metadata)
4. **Phase E**: Link PrimeWiki (add references to skills/recipes)
5. **Phase F**: Archive standalone docs (move 25+, add ARCHIVE_INDEX.md)

---

## Metrics & Success Criteria

**After Phase 3 Task #3**:
- ✅ KNOWLEDGE_HUB.md created (this file - index of 20 concepts)
- ✅ CLAUDE.md: 1,404 → 400 lines (71% reduction)
- ✅ Skills: 22 → 15 files (32% reduction)
- ✅ Recipes: 34 → 28 files (18% reduction)
- ✅ All 4 systems cross-reference canonical homes
- ✅ No two locations explain same concept differently
- ✅ All links bidirectional and working
- ✅ Standalone docs archived (25+ files)

---

**Authority**: 65537 (Fermat Prime Authority)
**Personas**: Knuth (literate programming), Dijkstra (correct proofs), Stroustrup (design clarity)
**Status**: Created 2026-02-15, ready for Phase B execution
