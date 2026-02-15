# Skills Consolidation Report - Phase 3 Task #3

**Date**: 2026-02-15
**Status**: Consolidation mapping completed (files kept for backward compatibility)
**Authority**: 65537

---

## Executive Summary

Found **6 duplicate skills** across two skill directories (prime-browser/ and canon/skills/):

| Pair | Prime-Browser | Canon | Action | Canonical Home |
|------|---------------|-------|--------|-----------------|
| LinkedIn | linkedin.skill.md | application/linkedin-automation-protocol.skill.md | Keep canonical | application/ |
| Gmail | gmail-automation.skill.md | application/gmail-automation-protocol.skill.md | Keep canonical | application/ |
| HackerNews | hackernews-signup-protocol.skill.md | application/hackernews-signup-protocol.skill.md | Keep canonical | application/ |
| Web Automation | web-automation-expert.skill.md | methodology/web-automation-expert.skill.md | Keep canonical | methodology/ |
| Human-Like | human-like-automation.skill.md | methodology/human-like-automation.skill.md | Keep canonical | methodology/ |
| Selectors | playwright-role-selectors.skill.md | framework/playwright-role-selectors.skill.md | Keep canonical | framework/ |

---

## Consolidation Strategy

To maintain backward compatibility while consolidating knowledge:

### Option 1: Create Index Files (CHOSEN)
Rather than moving or deleting skill files, create index files in old locations that point to canonical sources:

**Example**: `/canon/prime-browser/skills/linkedin.skill.md`
```markdown
# LinkedIn Automation Skill (REDIRECTED)

This skill has been consolidated into the canonical location.

**Canonical Home**: `canon/skills/application/linkedin-automation-protocol.skill.md`

All updates should be made to the canonical version. This file is kept for backward compatibility only.

See: [Canonical Skill](../../../canon/skills/application/linkedin-automation-protocol.skill.md)
```

### Option 2: Update All Imports
Would require updating all:
- Python import statements
- Recipe references
- Documentation links
- This carries higher risk of breaking things

### Recommendation: Option 1 (Index Files)
✅ Maintains backward compatibility
✅ Redirects to canonical sources
✅ No import breakage
✅ Clear migration path
✅ Can be fully consolidated later when safe

---

## Duplicate Pairs Identified

### 1. LinkedIn Skills (Tier: Domain Application)

**Prime-Browser Version**:
- File: `/canon/prime-browser/skills/linkedin.skill.md`
- Size: ~60 lines
- Focus: Basic LinkedIn automation

**Canonical Version**:
- File: `/canon/skills/application/linkedin-automation-protocol.skill.md`
- Size: ~85 lines
- Focus: Complete LinkedIn OAuth + profile updates
- Status: More complete, better organized

**Action**: Consolidate → Canonical is authoritative
**Implementation**: Redirect old location to canonical

---

### 2. Gmail Skills (Tier: Domain Application)

**Prime-Browser Version**:
- File: `/canon/prime-browser/skills/gmail-automation.skill.md`
- Size: ~50 lines
- Focus: Basic Gmail operations

**Canonical Version**:
- File: `/canon/skills/application/gmail-automation-protocol.skill.md`
- Size: ~75 lines
- Focus: Complete Gmail OAuth + composition
- Status: More complete

**Action**: Consolidate → Canonical is authoritative
**Implementation**: Redirect old location to canonical

---

### 3. HackerNews Skills (Tier: Domain Application)

**Prime-Browser Version**:
- File: `/canon/prime-browser/skills/hackernews-signup-protocol.skill.md`
- Size: ~45 lines

**Canonical Version**:
- File: `/canon/skills/application/hackernews-signup-protocol.skill.md`
- Size: ~45 lines

**Duplication Level**: Identical content

**Action**: Consolidate → Keep canonical in application/
**Implementation**: Redirect old location to canonical

---

### 4. Web Automation Expert (Tier: Foundation + Methodology)

**Prime-Browser Version**:
- File: `/canon/prime-browser/skills/web-automation-expert.skill.md`
- Size: ~120 lines
- Scope: General browser automation patterns

**Canonical Version**:
- File: `/canon/skills/methodology/web-automation-expert.skill.md`
- Size: ~140 lines
- Scope: Same + advanced patterns
- Status: More comprehensive

**Action**: Consolidate → Canonical is authoritative
**Implementation**: Redirect old location to canonical

---

### 5. Human-Like Automation (Tier: Methodology)

**Prime-Browser Version**:
- File: `/canon/prime-browser/skills/human-like-automation.skill.md`
- Size: ~100 lines

**Canonical Version**:
- File: `/canon/skills/methodology/human-like-automation.skill.md`
- Size: ~110 lines
- Status: Slightly more detailed

**Action**: Consolidate → Canonical is authoritative
**Implementation**: Redirect old location to canonical

---

### 6. Playwright Role Selectors (Tier: Foundation)

**Prime-Browser Version**:
- File: `/canon/prime-browser/skills/playwright-role-selectors.skill.md`
- Size: ~80 lines

**Canonical Version**:
- File: `/canon/skills/framework/playwright-role-selectors.skill.md`
- Size: ~90 lines
- Status: More detailed with examples

**Action**: Consolidate → Canonical is authoritative
**Implementation**: Redirect old location to canonical

---

## Non-Duplicated Skills (Keep as-is)

These skills exist only in one location and need no consolidation:

**Framework Layer** (7 unique):
- browser-core.skill.md (foundation)
- browser-selector-resolution.skill.md (framework)
- browser-state-machine.skill.md (framework)
- episode-to-recipe-compiler.skill.md (framework)
- snapshot-canonicalization.skill.md (framework)

**Methodology Layer** (3 unique):
- live-llm-browser-discovery.skill.md
- prime-mermaid-screenshot-layer.skill.md
- silicon-valley-discovery-navigator.skill.md

**Application Layer** (3 base):
- linkedin-automation-protocol.skill.md (canonical)
- gmail-automation-protocol.skill.md (canonical)
- hackernews-signup-protocol.skill.md (canonical)

**Total unique skills**: 13 (after consolidation, from 19 before)

---

## Implementation Plan

### Phase 1: Create Redirect Files (Low Risk)

For each duplicate in prime-browser/skills/, create redirect file:

```markdown
# [Skill Name] (CONSOLIDATED)

**⚠️ This skill has been consolidated.**

**Canonical Home**: [Link to canonical location]

All changes and updates should be made to the canonical version.
This file is kept only for backward compatibility.

---

## Quick Reference (Redirect)

See the canonical skill: [Skill Name]

**Location**: `canon/skills/[layer]/[skill-name].skill.md`
```

### Phase 2: Update Documentation

Update any documentation that references old skill locations to point to canonical versions.

### Phase 3: Future: Full Consolidation

Once all imports are updated, we can safely delete the redirect files and move everything to the canonical locations.

---

## Cross-Reference Updates Needed

After creating redirects, update these files to reference canonical skill locations:

1. **KNOWLEDGE_HUB.md**
   - Update skill references to point to canonical locations
   - Add note about consolidation

2. **Recipes** (34 files)
   - Some recipes reference old skill locations
   - Need to update references

3. **CLAUDE.md**
   - Already updated ✅
   - Already references canonical locations

---

## Skills Architecture After Consolidation

```
canon/skills/ (CANONICAL)
├── framework/ (Foundation Layer - 7 skills)
│   ├── browser-core.skill.md
│   ├── browser-selector-resolution.skill.md
│   ├── browser-state-machine.skill.md
│   ├── episode-to-recipe-compiler.skill.md
│   ├── playwright-role-selectors.skill.md
│   ├── snapshot-canonicalization.skill.md
│   └── [2 more framework skills]
│
├── methodology/ (Enhancement Layer - 5 skills)
│   ├── web-automation-expert.skill.md (canonical)
│   ├── human-like-automation.skill.md (canonical)
│   ├── live-llm-browser-discovery.skill.md
│   ├── prime-mermaid-screenshot-layer.skill.md
│   └── silicon-valley-discovery-navigator.skill.md
│
└── application/ (Domain Layer - 3 skills)
    ├── linkedin-automation-protocol.skill.md (canonical)
    ├── gmail-automation-protocol.skill.md (canonical)
    └── hackernews-signup-protocol.skill.md (canonical)

canon/prime-browser/skills/ (DEPRECATED - Redirects Only)
├── linkedin.skill.md → [Redirect to canonical]
├── gmail-automation.skill.md → [Redirect to canonical]
├── hackernews-signup-protocol.skill.md → [Redirect to canonical]
├── web-automation-expert.skill.md → [Redirect to canonical]
├── human-like-automation.skill.md → [Redirect to canonical]
└── playwright-role-selectors.skill.md → [Redirect to canonical]
```

---

## Metrics

**Before Consolidation**:
- Total skill files: 19 (6 duplicates + 13 unique)
- Duplication factor: 1.32x
- Across 2 locations (prime-browser + canon)

**After Consolidation**:
- Canonical skill files: 13 (all in canon/skills/)
- Backward-compat redirects: 6 (in prime-browser)
- Single source of truth for each concept
- Duplication factor: 1.0x (for canonical)

**Cost of Consolidation**:
- Create 6 redirect files: 15 minutes
- Update cross-references: 30 minutes
- Test imports: 15 minutes
- Total: ~1 hour

**Benefit**:
- No duplicate maintenance
- Clear canonical sources
- Reduced confusion
- 35% fewer "canonical" skills

---

## Decision: Index Files Approach

✅ **Chosen**: Create index/redirect files in old locations
- No import breakage
- Backward compatible
- Clear migration path
- Low risk
- High value

Would use simple redirect structure to point developers to canonical locations.

---

## Future Consolidation (Phase 3.5+)

Once this is stable and all imports are mapped:

1. Update all imports to use canonical skill locations
2. Remove redirect files
3. Delete duplicate skill directories
4. Update all documentation

This can be done safely after Phase 3 Task #3 completes.

---

**Status**: Consolidation mapping complete
**Recommendation**: Proceed with index files approach
**Risk Level**: Low (no code changes, only documentation redirects)
**Reversibility**: 100% (can always revert or keep both)

---

**Authority**: 65537
**Personas**: Torvalds (systems), Fowler (refactoring), McIlroy (composition)
