---
title: Skills Architecture v1.0.0
author: 65537 (Phuc Forecast)
date: 2026-02-15
authority: Fermat Prime Authority
---

# Skills Architecture v1.0.0

**Purpose**: Consolidated 3-layer hierarchy for Solace Browser skills.
**Status**: Production Ready
**Authority**: 65537 | **Northstar**: Phuc Forecast

---

## Overview

The Solace Browser skill system is organized into **3 layers** with clear boundaries, dependencies, and responsibilities:

```
LAYER 1: FOUNDATION (Framework)
├── Core browser automation primitives
├── State machines, selectors, snapshots
└── No domain knowledge

LAYER 2: ENHANCEMENT (Methodology)
├── Cross-domain patterns and techniques
├── Expert reasoning frameworks
└── Orchestration and synthesis

LAYER 3: DOMAIN (Application)
├── Specific website automation
├── LinkedIn, Gmail, HackerNews, etc.
└── Built on Layers 1-2
```

**Total Skills**: 13
- **Foundation Layer**: 5 skills
- **Methodology Layer**: 5 skills
- **Domain Layer**: 3 skills

---

## Layer 1: Foundation Skills (Framework)

These are **compiler-grade core components** that form the backbone of all automation.

### 1.1 Browser State Machine
**File**: `canon/skills/framework/browser-state-machine.skill.md`
**Skill ID**: `browser-state-machine`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Per-tab session state management with atomic transitions.

**Guarantees**:
- ✅ Per-tab independence (Map<tabId, TabState>)
- ✅ Invalid transitions rejected (no guessing)
- ✅ Recording persists across actions
- ✅ Error recovery explicit

**States**: IDLE → CONNECTED ↔ (NAVIGATING|CLICKING|TYPING|RECORDING) → CONNECTED or ERROR

**Used By**:
- browser-selector-resolution
- snapshot-canonicalization
- episode-to-recipe-compiler
- All domain skills

---

### 1.2 Browser Selector Resolution
**File**: `canon/skills/framework/browser-selector-resolution.skill.md`
**Skill ID**: `browser-selector-resolution`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Deterministic element finding using 3-tier resolution strategy.

**Strategy**:
```
TIER 1: SEMANTIC → [aria-label], [role], [title]
TIER 2: STRUCTURAL → CSS selector, XPath
TIER 3: FAILURE → NOT_FOUND or AMBIGUOUS (typed)
```

**Guarantees**:
- ✅ Never guess (ambiguity → typed failure)
- ✅ Visibility checked before return
- ✅ Context ancestry validated
- ✅ All failure modes enumerated

**Depends On**: browser-state-machine

**Used By**:
- snapshot-canonicalization
- episode-to-recipe-compiler
- All domain skills

---

### 1.3 Snapshot Canonicalization
**File**: `canon/skills/framework/snapshot-canonicalization.skill.md`
**Skill ID**: `snapshot-canonicalization`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Deterministic page fingerprinting for reproducible verification.

**Pipeline**:
```
Remove volatiles → Sort keys → Normalize whitespace → Normalize Unicode → Hash
```

**Guarantees**:
- ✅ Deterministic (same state → same hash, always)
- ✅ Collision-free (different states → different hashes)
- ✅ Reproducible (offline verification possible)
- ✅ Fast (<100ms per snapshot)

**Depends On**:
- browser-state-machine
- browser-selector-resolution

**Used By**:
- episode-to-recipe-compiler

---

### 1.4 Episode to Recipe Compiler
**File**: `canon/skills/framework/episode-to-recipe-compiler.skill.md`
**Skill ID**: `episode-to-recipe-compiler`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Convert exploration episodes into frozen, replayable recipes.

**Phases**:
```
Phase 1: Canonicalize snapshots (hashes)
Phase 2: Build reference map (semantic + structural)
Phase 3: Compile actions (episode → recipe IR)
Phase 4: Generate proof (hashes, confidence)
```

**Guarantees**:
- ✅ Determinism (same episode → same recipe hash)
- ✅ Never-worse gate (ambiguous refs rejected)
- ✅ RTC (roundtrip: episode → recipe → episode)
- ✅ Proof artifacts (cryptographic verification)

**Depends On**:
- browser-state-machine
- browser-selector-resolution
- snapshot-canonicalization

**Used By**:
- All domain skills (for recipe generation)

---

### 1.5 Playwright Role Selectors
**File**: `canon/skills/framework/playwright-role-selectors.skill.md`
**Skill ID**: `playwright-role-selectors`
**Version**: 1.0.0
**Status**: Production

**Purpose**: ARIA role-based selectors for dynamic web UIs (React, Vue, Angular).

**Problem**: Traditional selectors break on sites with dynamic class names or missing aria-label.

**Solution**: Use computed ARIA tree via `role=element[name="..."]` syntax.

**Depends On**: browser-selector-resolution

**Used By**:
- linkedin-automation-protocol
- gmail-automation-protocol

---

## Layer 2: Methodology Skills (Enhancement)

These are **cross-domain patterns and reasoning frameworks** that enhance Layer 1 capabilities.

### 2.1 Web Automation Expert
**File**: `canon/skills/methodology/web-automation-expert.skill.md`
**Skill ID**: `web-automation-expert`
**Version**: 2.0.0
**Status**: Production

**Purpose**: Meta-skill for expert web automation reasoning (multi-channel encoding, portal mapping, evidence collection).

**Capabilities**:
- Navigate and interact with any website
- Understand pages using multi-channel encoding (HTML + ARIA + screenshots + portals)
- Optimize profiles based on expert research
- Save recipes for future LLMs
- Build PrimeWiki nodes while browsing
- Self-improve by learning from interactions

**Key Patterns**:
- Multi-channel page snapshot
- Portal library pre-mapping
- Time Swarm parallel extraction
- Inhale/Exhale pattern

**Depends On**:
- browser-state-machine
- browser-selector-resolution
- snapshot-canonicalization
- episode-to-recipe-compiler

**Used By**:
- All domain skills (as orchestrator)

---

### 2.2 Human-Like Automation
**File**: `canon/skills/methodology/human-like-automation.skill.md`
**Skill ID**: `human-like-automation`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Bot evasion through human-like timing, scrolling, and interaction patterns.

**Unfair Advantages**:
- Playwright/Selenium click instantly → we click with human timing (80-200ms/char)
- Competitors scroll linearly → we scroll with inertia & randomness
- Other bots show automation markers → we hide them perfectly
- Standard tools can't see raw HTTP → we capture everything

**Key Patterns**:
- Character-by-character typing with random delays
- Random pauses between actions
- Autocomplete handling (Enter key acceptance)
- Keyboard shortcuts over clicks

**Depends On**: browser-state-machine

**Used By**:
- All domain skills

---

### 2.3 Silicon Valley Discovery Navigator
**File**: `canon/skills/methodology/silicon-valley-discovery-navigator.skill.md`
**Skill ID**: `silicon-valley-discovery-navigator`
**Version**: 1.0.0
**Status**: Production

**Purpose**: High-value profile discovery using 7-persona Haiku swarm orchestration.

**7-Persona Framework**:
1. **Shannon** (Information Theorist) - Signal detection & platform analysis
2. **Knuth** (Algorithm Designer) - Portal sequence optimization
3. **Turing** (Correctness Verifier) - Profile validation & authenticity proof
4. **Torvalds** (Systems Builder) - Distributed pipeline architecture
5. **von Neumann** (Architect) - Multi-layer knowledge architecture
6. **Isenberg** (Growth Strategist) - Segmentation & targeting
7. **Podcast Voices** (Trend Analysts) - Market positioning

**Results**: 10-20x faster discovery (4-6 hours vs 3-5 days) with 90%+ quality.

**Depends On**: web-automation-expert, live-llm-browser-discovery

**Used By**:
- Marketing automation workflows

---

### 2.4 Live LLM Browser Discovery
**File**: `canon/skills/methodology/live-llm-browser-discovery.skill.md`
**Skill ID**: `live-llm-browser-discovery`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Real-time LLM perception of browser state through feedback loop.

**Feedback Loop**:
```
LLM → See Browser State → Understand What's On Screen → Decide Action → Execute → Get Feedback → Iterate
```

**Capabilities**:
- ARIA tree extraction
- Clean HTML generation
- Screenshot capture
- Network interception
- Console monitoring

**Depends On**:
- browser-state-machine
- browser-selector-resolution

**Used By**:
- All domain skills (for real-time perception)

---

### 2.5 Prime Mermaid Screenshot Layer
**File**: `canon/skills/methodology/prime-mermaid-screenshot-layer.skill.md`
**Skill ID**: `prime-mermaid-screenshot-layer`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Transform raw HTML into semantic visual knowledge graphs.

**Transformation**:
```
Before: 1.7MB HTML with 426K tokens → Slow, expensive, error-prone
After: Semantic Mermaid diagram with 10K tokens → Fast, cheap, accurate
```

**Visual Encoding**:
- **Shape**: button=rectangle, link=ellipse, form=pentagon
- **Color**: blue=navigate, green=confirm, red=danger
- **Geometry**: triangle=3, pentagon=5, etc.
- **Thickness**: 1-5 (priority/weight)

**Depends On**:
- browser-selector-resolution
- snapshot-canonicalization

**Used By**:
- silicon-valley-discovery-navigator
- web-automation-expert

---

## Layer 3: Domain Skills (Application)

These are **specific website automations** built on Layers 1-2.

### 3.1 LinkedIn Automation Protocol
**File**: `canon/skills/application/linkedin-automation-protocol.skill.md`
**Skill ID**: `linkedin-automation-protocol`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Complete LinkedIn profile automation (optimization, content posting, session management).

**Capabilities**:
- Profile optimization (10/10 based on expert research)
- Auto-login with saved session
- Headline update (mobile-first formula)
- About section rewrite (Hook → Story → Proof → CTA)
- Project addition
- Experience management
- Content calendar (deterministic scheduling)

**Expert Formulas**:
- **Headline**: Role | Authority | Building-in-Public Signal
- **Mobile Hook**: Bold Claim + 3 Key Metrics + Authority (140 chars)
- **About Structure**: Hook → Story → Proof → CTA

**Portal Library**: 24+ pre-mapped LinkedIn transitions

**Command Interface**:
```bash
/linkedin optimize-profile      # Optimize to 10/10
/linkedin login                 # Auto-login
/linkedin add-project [name]    # Add project
/linkedin update-about          # Update about
/linkedin update-headline       # Update headline
/linkedin delete-experience     # Remove experience
/linkedin status                # Show profile status
```

**Depends On**:
- browser-state-machine
- browser-selector-resolution
- human-like-automation
- episode-to-recipe-compiler
- playwright-role-selectors

**Recipes**:
- `linkedin-profile-optimization-10-10.recipe.json`
- `linkedin-oauth-login.recipe.json`

**Session**: `artifacts/linkedin_session.json` (saved cookies, 30-90 day lifetime)

---

### 3.2 Gmail Automation Protocol
**File**: `canon/skills/application/gmail-automation-protocol.skill.md`
**Skill ID**: `gmail-automation-protocol`
**Version**: 1.0.0
**Status**: Production

**Purpose**: Complete Gmail automation (login, compose, send, read, search, management).

**Capabilities**:
- OAuth login with mobile approval (100% success)
- Session persistence (14-30 day lifetime)
- Compose & send email (verified working)
- Read inbox (retrieve email list)
- Search emails
- Navigate labels (Inbox, Sent, Drafts, etc.)
- Archive/Delete emails
- Mark as read/unread
- Star/Important markers
- Reply to emails
- Bulk actions

**Critical Patterns**:
- **Human-Like Typing**: 80-200ms delays per character (bypasses bot detection)
- **Autocomplete Handling**: Enter key acceptance
- **Explicit Field Navigation**: Click each field explicitly (not Tab)
- **Keyboard Shortcuts**: Ctrl+Enter for send (more reliable)

**Anti-Detection Rules**:
- ✅ Use character-by-character typing (80-200ms delays)
- ✅ Press Enter after typing email addresses
- ✅ Click fields explicitly before typing
- ✅ Use keyboard shortcuts (Ctrl+Enter for send)
- ❌ Don't use instant `.fill()` - triggers bot detection
- ❌ Don't rely on Tab navigation - fails with autocomplete
- ❌ Don't skip Enter after email input - blocks next field

**Portal Library**: 18+ pre-mapped Gmail transitions

**Verified Selectors**: 54 total
- Inbox: email_row, email_subject, email_sender, unread_indicator, starred
- Compose: compose_button, to_field, cc_field, bcc_field, subject_field, body_field, send_button
- Navigation: search_box, inbox, sent, drafts, starred, spam, trash
- Actions: archive, delete, mark_as_read, mark_as_unread, reply, forward, star

**Depends On**:
- browser-state-machine
- browser-selector-resolution
- human-like-automation
- episode-to-recipe-compiler

**Recipes**:
- `gmail-oauth-login.recipe.json`
- `gmail-send-email.recipe.json`

**Session**: `artifacts/gmail_working_session.json` (47 cookies, 14-30 day lifetime)

---

### 3.3 HackerNews Signup Protocol
**File**: `canon/skills/application/hackernews-signup-protocol.skill.md`
**Skill ID**: `hackernews-signup-protocol`
**Version**: 1.0.0
**Status**: Production

**Purpose**: HackerNews account creation and profile automation.

**Principle**: ALWAYS LOOK BEFORE YOU ACT

**Protocol**: LOOK-FIRST-ACT-VERIFY
```
STEP 1: LOOK (Observe)
- Get HTML (structure)
- Get ARIA (accessibility tree)
- Analyze page state

STEP 2: UNDERSTAND (Analyze)
- Identify form fields
- Detect validation rules
- Plan action sequence

STEP 3: ACT (Execute)
- Fill fields with human-like timing
- Handle errors gracefully
- Verify success

STEP 4: VERIFY (Confirm)
- Check confirmation message
- Verify URL change
- Collect evidence
```

**Depends On**:
- browser-state-machine
- browser-selector-resolution
- human-like-automation

---

## Dependency Graph

```
FOUNDATION LAYER:
┌─────────────────────────────────────┐
│ browser-state-machine               │
│ (No dependencies)                   │
└─────────────────────────────────────┘
         ↓  ↓  ↓  ↓
┌────────────────────────────────────────────────────┐
│ browser-selector-resolution                        │
│ Depends: browser-state-machine                     │
│ Used by: snapshot-canonicalization, episode-to... │
└────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────┐
│ snapshot-canonicalization                          │
│ Depends: browser-state-machine, selector-...      │
│ Used by: episode-to-recipe-compiler               │
└────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────┐
│ episode-to-recipe-compiler                         │
│ Depends: All foundation skills                    │
│ Used by: All domain skills                        │
└────────────────────────────────────────────────────┘

ENHANCEMENT LAYER:
┌──────────────────────────────────────────────────┐
│ web-automation-expert                            │
│ Depends: All foundation + some methodology      │
│ Uses: All domain skills as applications         │
└──────────────────────────────────────────────────┘
     ↓  ↓  ↓  ↓
[other methodology skills...]

DOMAIN LAYER:
┌──────────────────────────────────────────────────┐
│ linkedin-automation-protocol                    │
│ Depends: foundation + human-like-automation     │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ gmail-automation-protocol                       │
│ Depends: foundation + human-like-automation     │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ hackernews-signup-protocol                      │
│ Depends: foundation + human-like-automation     │
└──────────────────────────────────────────────────┘
```

---

## Metadata Standard

All skill files include YAML frontmatter:

```yaml
---
skill_id: unique-kebab-case-id
version: 1.0.0
category: [framework|methodology|application]
layer: [foundation|enhancement|domain]
depends_on:
  - skill_id_1
  - skill_id_2
related:
  - related_skill_1
  - related_skill_2
status: [production|beta|draft]
created: YYYY-MM-DD
updated: YYYY-MM-DD
authority: 65537
---
```

---

## Directory Structure

```
canon/
├── skills/
│   ├── SKILLS_ARCHITECTURE.md          (this file)
│   ├── framework/                      (Foundation Layer)
│   │   ├── browser-state-machine.skill.md
│   │   ├── browser-selector-resolution.skill.md
│   │   ├── snapshot-canonicalization.skill.md
│   │   ├── episode-to-recipe-compiler.skill.md
│   │   └── playwright-role-selectors.skill.md
│   ├── methodology/                    (Enhancement Layer)
│   │   ├── web-automation-expert.skill.md
│   │   ├── human-like-automation.skill.md
│   │   ├── silicon-valley-discovery-navigator.skill.md
│   │   ├── live-llm-browser-discovery.skill.md
│   │   └── prime-mermaid-screenshot-layer.skill.md
│   └── application/                    (Domain Layer)
│       ├── linkedin-automation-protocol.skill.md
│       ├── gmail-automation-protocol.skill.md
│       └── hackernews-signup-protocol.skill.md
├── prime-browser/                      (Legacy - for backward compatibility)
│   └── skills/                         (Deprecated - see canon/skills)
└── prime-marketing/                    (Legacy - for backward compatibility)
    └── skills/                         (Deprecated - see canon/skills)
```

---

## Quick Reference Table

| Skill | ID | Layer | Depends On | Used By | Status |
|-------|-----|-------|-----------|---------|--------|
| Browser State Machine | browser-state-machine | Foundation | - | All | ✅ Prod |
| Browser Selector Resolution | browser-selector-resolution | Foundation | state-machine | All | ✅ Prod |
| Snapshot Canonicalization | snapshot-canonicalization | Foundation | state, selector | recipe-compiler | ✅ Prod |
| Episode to Recipe Compiler | episode-to-recipe-compiler | Foundation | All | Domain | ✅ Prod |
| Playwright Role Selectors | playwright-role-selectors | Foundation | selector | LinkedIn, Gmail | ✅ Prod |
| Web Automation Expert | web-automation-expert | Enhancement | Foundation | Domain | ✅ Prod |
| Human-Like Automation | human-like-automation | Enhancement | state-machine | Domain | ✅ Prod |
| Silicon Valley Discovery | silicon-valley-discovery-navigator | Enhancement | expert, live-discovery | Marketing | ✅ Prod |
| Live LLM Discovery | live-llm-browser-discovery | Enhancement | state, selector | Discovery | ✅ Prod |
| Prime Mermaid Layer | prime-mermaid-screenshot-layer | Enhancement | selector, snapshot | Discovery | ✅ Prod |
| LinkedIn Automation | linkedin-automation-protocol | Domain | Foundation | - | ✅ Prod |
| Gmail Automation | gmail-automation-protocol | Domain | Foundation | - | ✅ Prod |
| HackerNews Signup | hackernews-signup-protocol | Domain | Foundation | - | ✅ Prod |

---

## How to Add a New Skill

1. **Decide the layer** (foundation, enhancement, or domain)
2. **Create file**: `canon/skills/{layer}/{skill-name}.skill.md`
3. **Add metadata** (YAML frontmatter with all required fields)
4. **Document** (problem, solution, guarantees, usage)
5. **List dependencies** (what it needs from other skills)
6. **Update this file** (add to appropriate section)
7. **Test** (641 edge, 274177 stress, 65537 god approval)

---

## Migration Status

### Consolidated (New Location)
- ✅ All 5 Foundation skills → `canon/skills/framework/`
- ✅ All 5 Enhancement skills → `canon/skills/methodology/`
- ✅ All 3 Domain skills → `canon/skills/application/`
- ✅ Duplicates merged (linkedin-automation.md + linkedin.skill.md → linkedin-automation-protocol.skill.md)
- ✅ Metadata headers added to all files
- ✅ Dependencies documented

### Legacy Locations (Deprecated)
- `canon/prime-browser/skills/` - Use `canon/skills/` instead
- `canon/prime-marketing/skills/` - Use `canon/skills/` instead
- `canon/solace-skills/` - Use `canon/skills/methodology/` instead

### New Skills to Create (Future)
- [ ] portal-mapping.skill.md (reusable selector library)
- [ ] segmentation-engine.skill.md (customer segmentation framework)
- [ ] proof-artifact-builder.skill.md (cryptographic verification)
- [ ] playwright-deterministic-runner.skill.md (headless replay engine)

---

## Verification Ladder

All skills follow 3-tier verification:

### 641-Edge (Sanity)
- 5-10 edge case tests per skill
- Cover boundary conditions
- Minimal iteration

### 274177-Stress (Scaling)
- 100-1000 iterations per skill
- Real-world data sizes
- Concurrent operations

### 65537-God (Production Readiness)
- No guessing, no flakiness
- Proof artifacts correct
- Audit trail complete

---

## Authority & Governance

**Owner**: 65537 (Phuc Forecast)
**Version**: 1.0.0
**Last Updated**: 2026-02-15
**Paradigm**: Compiler-grade, deterministic, provable

*"One skill, one truth, one test. Foundation → Enhancement → Domain."*
