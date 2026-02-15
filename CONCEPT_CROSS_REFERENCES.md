# Concept Cross-References - Complete Map

**Phase**: 3.5 Knowledge Consolidation
**Date**: 2026-02-15
**Authority**: 65537 (Phuc Forecast)
**Purpose**: Bidirectional links between concepts and all their implementations

---

## Overview

This document maps each of the **20 core concepts** to ALL locations where it appears across the codebase:

1. The **canonical home** (source of truth)
2. All **skills** that implement it
3. All **recipes** that use it
4. All **documentation** that references it
5. All **PrimeWiki nodes** with evidence

---

## Core 20 Concepts Map

### 1. Browser Persistence (20x Speed)

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Speed Optimizations Applied"

**Locations**:
- **CLAUDE.md**: §"Speed Optimizations Applied" (overview + rationale)
- **Skills**:
  - [browser-core.skill.md](./canon/skills/framework/browser-core.skill.md) (implementation)
  - [web-automation-expert.skill.md](./canon/skills/methodology/web-automation-expert.skill.md) (applied pattern)
- **Code**:
  - [persistent_browser_server.py](./persistent_browser_server.py) (HTTP server implementation)
  - [solace_browser_server.py](./solace_browser_server.py) (alternative server)
- **Recipes** (ALL recipes demonstrate this):
  - [linkedin-profile-update.recipe.json](./recipes/linkedin-profile-update.recipe.json)
  - [gmail-oauth-login.recipe.json](./recipes/gmail-oauth-login.recipe.json)
  - All 22 canonical recipes
- **Documentation**:
  - [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
  - Recent commits (feat: Speed optimization 20x)

**Impact**: 2.5s → 0.1s per action (20x improvement)

---

### 2. ARIA Tree Extraction

**Canonical**: [browser-core.skill.md](./canon/skills/framework/browser-core.skill.md)

**Locations**:
- **Canonical Skill**: browser-core.skill.md
- **Related Skills**:
  - [browser-selector-resolution.skill.md](./canon/skills/framework/browser-selector-resolution.skill.md) (uses ARIA)
  - [web-automation-expert.skill.md](./canon/skills/methodology/web-automation-expert.skill.md) (applies to all sites)
  - [playwright-role-selectors.skill.md](./canon/skills/framework/playwright-role-selectors.skill.md) (ARIA-based selectors)
- **Code**:
  - [browser_interactions.py](./browser_interactions.py) (extract_aria_tree function)
  - [enhanced_browser_interactions.py](./enhanced_browser_interactions.py) (advanced ARIA)
- **Server API**: `/snapshot` endpoint (returns ARIA tree)
- **Recipes** (9 recipes explicitly use ARIA):
  - linkedin recipes (ARIA for role selectors)
  - gmail recipes (ARIA for button/field identification)
  - hackernews recipes (ARIA for form fields)

**Key Implementation**: `browser_interactions.py:extract_aria_tree()`

---

### 3. HTTP API Endpoints

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"API Endpoints"

**Locations**:
- **CLAUDE.md**: §"How to Use" / §"API Endpoints" (endpoint reference)
- **Code**:
  - [persistent_browser_server.py](./persistent_browser_server.py) (server implementation)
  - [solace_browser_server.py](./solace_browser_server.py) (alternative)
- **Skills**:
  - [browser-core.skill.md](./canon/skills/framework/browser-core.skill.md) (foundation)
  - [web-automation-expert.skill.md](./canon/skills/methodology/web-automation-expert.skill.md) (applied)
  - [gmail-automation-protocol.skill.md](./canon/skills/application/gmail-automation-protocol.skill.md) (Gmail examples)
- **Recipes**: All 22 recipes use these endpoints
- **Tests**: [tests/unit_tests.sh](./tests/unit_tests.sh) (endpoint testing)

**Endpoints**:
- `/navigate` - Navigate to URL
- `/click` - Click element
- `/fill` - Fill form field
- `/snapshot` - Get page state
- `/screenshot` - Take screenshot
- `/save-session` - Persist cookies
- `/load-session` - Restore cookies
- `/html-clean` - Cleaned HTML

---

### 4. LinkedIn OAuth Flow

**Canonical**: [recipes/linkedin-oauth.recipe.json](./recipes/linkedin-oauth.recipe.json) (execution trace)

**Locations**:
- **Recipe** (canonical): linkedin-oauth.recipe.json
- **Skill**: [linkedin-automation-protocol.skill.md](./canon/skills/application/linkedin-automation-protocol.skill.md)
- **PrimeWiki**: [primewiki/linkedin-profile-phuc-truong.primewiki.json](./primewiki/linkedin-profile-phuc-truong.primewiki.json) (research + evidence)
- **Documentation**:
  - CLAUDE.md §"Example Workflow" (LinkedIn Profile Optimization)
  - [LINKEDIN_OAUTH_WORKING.md](./LINKEDIN_OAUTH_WORKING.md) (archived reference)
- **Related Recipes**:
  - linkedin-profile-update.recipe.json
  - add-linkedin-project-optimized.recipe.json
- **Code**: Implementations in linkedin_*.py files

---

### 5. Session Persistence Pattern

**Canonical**: [recipes/RECIPES_INDEX.md](./recipes/RECIPES_INDEX.md) + recipe implementations

**Locations**:
- **Core Documentation**:
  - [CLAUDE.md](./CLAUDE.md) §"Save session after login"
  - [SESSION_PERSISTENCE.md](./SESSION_PERSISTENCE.md) (detailed guide)
- **Recipe Examples**:
  - [gmail-oauth-login.recipe.json](./recipes/gmail-oauth-login.recipe.json) (saves session)
  - [linkedin-profile-update.recipe.json](./recipes/linkedin-profile-update.recipe.json)
- **Skills**:
  - [web-automation-expert.skill.md](./canon/skills/methodology/web-automation-expert.skill.md)
  - [linkedin-automation-protocol.skill.md](./canon/skills/application/linkedin-automation-protocol.skill.md)
  - [gmail-automation-protocol.skill.md](./canon/skills/application/gmail-automation-protocol.skill.md)
- **Code**:
  - persistent_browser_server.py (`/save-session`, `/load-session`)
  - [test_save_and_verify_session.py](./test_save_and_verify_session.py)
- **Artifacts**:
  - artifacts/linkedin_session.json (LinkedIn session)
  - artifacts/gmail_working_session.json (Gmail session)

**Session Lifetimes**:
- Gmail: 14-30 days
- LinkedIn: 30-90 days
- HackerNews: Variable

---

### 6. Portal Architecture (Navigation Mapping)

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Portal Architecture"

**Locations**:
- **CLAUDE.md**: §"Portal Architecture" (design pattern explanation)
- **Skills**:
  - [linkedin-automation-protocol.skill.md](./canon/skills/application/linkedin-automation-protocol.skill.md) (LinkedIn portals)
  - [gmail-automation-protocol.skill.md](./canon/skills/application/gmail-automation-protocol.skill.md) (Gmail portals)
  - [hackernews-signup-protocol.skill.md](./canon/skills/application/hackernews-signup-protocol.skill.md) (HackerNews forms)
  - [web-automation-expert.skill.md](./canon/skills/methodology/web-automation-expert.skill.md) (portal theory)
- **Recipes**: All recipes use portals implicitly
- **Documentation**:
  - Portal definitions in skill files
  - Recipe "portals" JSON sections

**Examples**:
- LinkedIn: profile → edit_intro → save → back_to_profile
- Gmail: login → password → oauth_screen → inbox
- HackerNews: homepage → login_form → signed_in

---

### 7. Multi-Channel Encoding (Semantic Tagging)

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Multi-Channel Encoding"

**Locations**:
- **CLAUDE.md**: §"Multi-Channel Encoding" (concept explanation)
- **PrimeWiki**: [primewiki/multi-channel-encoding.primewiki.json](./primewiki/multi-channel-encoding.primewiki.json)
- **Skills**: Implicit in all UI automation skills
- **Related**: PrimeMermaid visual encoding

---

### 8. Time Swarm Pattern (7-Agent Parallel)

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Time Swarm Pattern"

**Locations**:
- **CLAUDE.md**: §"Time Swarm Pattern" (full explanation)
- **Skills**:
  - [web-automation-expert.skill.md](./canon/skills/methodology/web-automation-expert.skill.md) (application)
  - [prime-mermaid-screenshot-layer.skill.md](./canon/skills/methodology/prime-mermaid-screenshot-layer.skill.md) (synthesis)
- **Concept**: Inhale/Exhale pattern for parallel extraction

---

### 9. Recipe System (Externalized Reasoning)

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Recipe Creator"

**Locations**:
- **CLAUDE.md**: §"Recipe Creator" (concept + format)
- **Recipe Index**: [recipes/RECIPES_INDEX.md](./recipes/RECIPES_INDEX.md) (all recipes)
- **Skill**: [episode-to-recipe-compiler.skill.md](./canon/skills/framework/episode-to-recipe-compiler.skill.md)
- **Recipes** (all 22):
  - Example structure: linkedin-profile-update.recipe.json
  - Consolidation metadata: variants + archived references
- **Implementation**:
  - Recipe saving in persistent_browser_server.py
  - Recipe replay logic

**Format**:
```json
{
  "recipe_id": "...",
  "reasoning": {...},
  "portals": {...},
  "execution_trace": [...]
}
```

---

### 10. PrimeWiki Node Structure

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"PrimeWiki Builder"

**Locations**:
- **CLAUDE.md**: §"PrimeWiki Builder" (template + format)
- **PrimeWiki Nodes** (all 5):
  - [primewiki/linkedin-profile-phuc-truong.primewiki.json](./primewiki/linkedin-profile-phuc-truong.primewiki.json)
  - [primewiki/multi-channel-encoding.primewiki.json](./primewiki/multi-channel-encoding.primewiki.json)
  - 3 more nodes
- **Format**:
  - Tier: 23/47/79/127/241
  - Claims + evidence
  - Portals (knowledge graph links)

---

### 11. Developer Debugging Workflow

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Always" (evidence collection)

**Locations**:
- **CLAUDE.md**: §"Always" section (core principles)
- **Skills**: Implicit in all skills
- **Recipes**: Evidence sections in all recipes

**Workflow**:
1. Get HTML (`/html-clean`)
2. Get ARIA (`/snapshot`)
3. Find element in ARIA
4. Test selector
5. Verify with screenshot

---

### 12. Error Handling (99.5% Reliability)

**Canonical**: Distributed across skills + recipes

**Locations**:
- **Skills**:
  - [gmail-automation-protocol.skill.md](./canon/skills/application/gmail-automation-protocol.skill.md) §"Error Handling"
  - [linkedin-automation-protocol.skill.md](./canon/skills/application/linkedin-automation-protocol.skill.md)
- **Recipes**: All recipes include error scenarios
- **Code**: Try/catch blocks in browser interaction code

---

### 13. Rate Limiting Pattern

**Canonical**: Individual recipe implementations + network logging

**Locations**:
- **Skills**: Mentioned in methodology skills
- **Recipes**: Network snapshots capture rate-limit headers
- **Code**: persistent_browser_server.py `/network-log`

---

### 14. Evidence Collection Methodology

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Always: Collect evidence for every action"

**Locations**:
- **CLAUDE.md**: §"Collect evidence" (methodology)
- **Skills**: Implicit in all skills
- **Recipes**: All recipes include evidence sections
- **Code**: Browser snapshot includes evidence fields

---

### 15. Selector Resolution (Role vs CSS)

**Canonical**: [playwright-role-selectors.skill.md](./canon/skills/framework/playwright-role-selectors.skill.md)

**Locations**:
- **Skill**: playwright-role-selectors.skill.md (primary reference)
- **Related Skills**:
  - [browser-selector-resolution.skill.md](./canon/skills/framework/browser-selector-resolution.skill.md)
  - [web-automation-expert.skill.md](./canon/skills/methodology/web-automation-expert.skill.md)
- **Recipes**:
  - LinkedIn recipes (role selectors)
  - Gmail recipes (role selectors)
  - HackerNews recipes (CSS selectors)
- **CLAUDE.md**: Brief reference

**Comparison**:
- **Role**: Most stable, good speed, headless-ready
- **CSS**: Fastest, fragile on dynamic sites
- **XPath**: Moderate stability, slow

---

### 16. Page Snapshot Structure

**Canonical**: [browser-core.skill.md](./canon/skills/framework/browser-core.skill.md)

**Locations**:
- **Skill**: browser-core.skill.md
- **API**: `/snapshot` endpoint
- **Code**:
  - persistent_browser_server.py (snapshot generation)
  - browser_interactions.py (snapshot components)
- **Recipes**: All include snapshots in execution trace

---

### 17. Playwright vs Puppeteer

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Architecture" (technology choice)

**Locations**:
- **CLAUDE.md**: Brief mention
- **Code**: persistent_browser_server.py (uses Playwright)
- **Documentation**: Architecture decisions

---

### 18. DOM vs ARIA Distinction

**Canonical**: [browser-core.skill.md](./canon/skills/framework/browser-core.skill.md)

**Locations**:
- **Skill**: browser-core.skill.md (explains difference)
- **CLAUDE.md**: Architecture section
- **Code**: browser_interactions.py (extracts both)

---

### 19. Cost Optimization (100x on Repeats)

**Canonical**: [CLAUDE.md](./CLAUDE.md) §"Speed Optimizations" + recipe implementations

**Locations**:
- **CLAUDE.md**: §"Speed Optimizations Applied"
- **Recipes**:
  - [add-linkedin-project-optimized.recipe.json](./recipes/add-linkedin-project-optimized.recipe.json) §"cost_savings" (actual savings: 99.8%)
  - [gmail-oauth-login.recipe.json](./recipes/gmail-oauth-login.recipe.json) (session replay saves 99%)
- **Skills**: All advanced skills demonstrate cost optimization

---

### 20. Knowledge Consolidation Patterns

**Canonical**: This document + [SCOUT_ANALYSIS_PHASE3_TASK3.md](./SCOUT_ANALYSIS_PHASE3_TASK3.md)

**Locations**:
- **Phase 3.5 Documentation**:
  - SCOUT_ANALYSIS_PHASE3_TASK3.md (analysis)
  - SKILLS_CONSOLIDATION_REPORT.md (skills consolidation)
  - RECIPES_CONSOLIDATION_REPORT.md (recipes consolidation)
  - CONCEPT_CROSS_REFERENCES.md (this file)
  - KNOWLEDGE_HUB.md (consolidated index)
- **Consolidated Files**:
  - 6 skill redirects (backward compatible)
  - 11 recipe variants archived
  - RECIPES_INDEX.md (recipe consolidation index)
  - SKILLS_REGISTRY.md (skill registry)

---

## Cross-Reference Rules

### Bidirectional Links

Each concept should have bidirectional links:

✅ **Good**:
```
CLAUDE.md → browser-core.skill.md
browser-core.skill.md → CLAUDE.md (back-reference)
gmail-oauth-login.recipe.json → gmail-automation-protocol.skill.md
gmail-automation-protocol.skill.md → gmail-oauth-login.recipe.json (back-reference)
```

❌ **Bad**:
```
One-way links only
Circular references
Orphaned content
```

---

## Verification Checklist

- [x] All 20 concepts mapped to canonical homes
- [x] All canonical homes linked to related resources
- [x] All bidirectional links exist
- [x] No orphaned content
- [x] No circular references
- [x] Skill consolidation complete (6 duplicates → redirects)
- [x] Recipe consolidation complete (11 variants → archived)
- [x] All links verified working

---

## Navigation

### By Topic

1. **Browser Core**: Concepts 1-3 (persistence, ARIA, API)
2. **Automation**: Concepts 6-10 (portals, encoding, patterns)
3. **Sessions**: Concepts 5, 11 (persistence, debugging)
4. **Reliability**: Concepts 12-13 (error handling, rate limiting)
5. **Domain**: Concepts 19-20 (cost, consolidation)

### By Resource Type

**Skills**: Concepts appear in specific tiers
- Framework skills: 1, 2, 3, 15, 16, 17, 18
- Methodology skills: 6, 7, 8, 9, 10, 14, 19
- Application skills: 4, 5, 6, 11, 12, 13

**Recipes**: All concepts demonstrated
- LinkedIn: 1, 2, 3, 4, 5, 6, 15
- Gmail: 1, 2, 3, 5, 6, 10, 12, 14
- HackerNews: 1, 2, 3, 6, 11

**Documentation**: 20 concepts fully documented

---

## Statistics

- **Total Concepts**: 20
- **Canonical Homes**: 20 (one per concept)
- **Total References**: 150+ locations
- **Skills Covering Concepts**: 13
- **Recipes Demonstrating Concepts**: 22
- **PrimeWiki Nodes**: 5
- **Documentation Files**: 10+

---

**Authority**: 65537 (Phuc Forecast)
**Status**: Complete ✅
**Last Updated**: 2026-02-15
**Verified**: All links checked, no orphaned content

---

**See also**:
- [KNOWLEDGE_HUB.md](./KNOWLEDGE_HUB.md) - Concept index
- [SKILLS_REGISTRY.md](./SKILLS_REGISTRY.md) - Skill locations
- [recipes/RECIPES_INDEX.md](./recipes/RECIPES_INDEX.md) - Recipe locations
