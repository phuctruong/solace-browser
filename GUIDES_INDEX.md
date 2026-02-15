# Solace Browser Guides Index

**Navigate documentation by question or learning path.**

---

## Quick Navigation

### By Question

"What do I do when...?"

- **I'm starting out** → [QUICK_START.md](./QUICK_START.md) (5 min)
- **I want to understand how it works** → [CORE_CONCEPTS.md](./CORE_CONCEPTS.md) (30 min)
- **I want to become an expert** → [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md) (60 min)
- **Something is broken** → [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)
- **I need the full API** → [API_REFERENCE.md](./API_REFERENCE.md)
- **I need to remember my role** → [CLAUDE.md](./CLAUDE.md) (meta-instructions)

### By Learning Path

**Beginner (30 minutes)**
1. Read [QUICK_START.md](./QUICK_START.md) - Get hands-on (5 min)
2. Read [CORE_CONCEPTS.md](./CORE_CONCEPTS.md) - Understand fundamentals (20 min)
3. Try a simple task - Navigate a website and save the session (5 min)

**Intermediate (90 minutes)**
1. Read [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md) - Learn patterns (60 min)
2. Read [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md) - Master debugging (20 min)
3. Create your first recipe (10 min)

**Expert (2+ hours)**
1. Master [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md) - Study deeply (60 min)
2. Study existing recipes in `recipes/` directory
3. Study existing PrimeWiki nodes in `primewiki/` directory
4. Build and optimize recipes for new sites

---

## Guide Descriptions

### CLAUDE.md - Meta-Instructions (400 lines)

**Time to read**: 10 minutes
**For**: Everyone (reference at start of each session)

Your core responsibilities and quick reference. Links to all other guides.

**Contains**:
- Your mission
- Quick start pointer
- Before any web task (registry check)
- Core responsibilities (4 roles)
- Key principles
- Success metrics
- Troubleshooting checklist

**Read this if**: You want a quick refresh on what you're doing

---

### QUICK_START.md - Getting Started (400 lines)

**Time to read**: 5 minutes (hands-on)
**For**: First-time users

Three tutorials you can run right now.

**Contains**:
1. Tutorial 1: Start the browser server (1 min)
2. Tutorial 2: Make your first API call (2 min)
3. Tutorial 3: Save and load session (2 min)
4. Troubleshooting common issues

**Read this if**: You've never used Solace Browser before

---

### CORE_CONCEPTS.md - Understanding How It Works (800 lines)

**Time to read**: 30 minutes
**For**: Everyone who wants to understand the system

Deep dive into the 10 core concepts.

**Contains**:
1. Persistent Browser Server (20x speed)
2. Page Snapshots (multi-channel understanding)
3. Selector Resolution (finding elements)
4. Knowledge Capture (recipes & PrimeWiki)
5. Browser State & Verification
6. Speed Optimization Details
7. Multi-Channel Encoding (visual semantics)
8. Session Persistence
9. Error Handling & Recovery
10. Architecture Diagram

**Read this if**: You want to understand why Solace is designed this way

---

### ADVANCED_TECHNIQUES.md - Becoming an Expert (600 lines)

**Time to read**: 60 minutes
**For**: Advanced users wanting to optimize

10 expert-level techniques and patterns.

**Contains**:
1. Portal Architecture (pre-mapping page transitions)
2. Haiku Swarm Coordination (Scout/Solver/Skeptic)
3. Multi-Channel Encoding (visual patterns)
4. Recipe Compilation & Optimization
5. PrimeMermaid Visualization
6. Bot Evasion Techniques
7. Network Interception & Mocking
8. Evidence-Based Confidence Scoring
9. Performance Tuning
10. Advanced Debugging Techniques

**Read this if**: You want to master Solace Browser and optimize beyond basics

---

### DEVELOPER_DEBUGGING.md - Troubleshooting (500 lines)

**Time to read**: 30-60 minutes (reference as needed)
**For**: When things break

Systematic debugging workflow and solutions.

**Contains**:
1. LOOK-FIRST-ACT-VERIFY workflow
2. Selector Debug Techniques
3. Common Issues & Fixes (9 issues with solutions)
4. Logging & Monitoring Strategies
5. Registry Lookup Patterns
6. Knowledge Decay Detection
7. Performance Profiling
8. Stress Testing
9. Testing Best Practices
10. Troubleshooting Checklist

**Read this if**: An automation failed or you need systematic debugging approach

---

### API_REFERENCE.md - Full API (See separate file)

**Time to read**: 10-20 minutes (reference)
**For**: When you need to know exact HTTP endpoints

Complete HTTP API reference with all endpoints, parameters, responses.

**Contains**:
- All `/navigate`, `/click`, `/fill`, `/submit` endpoints
- All `/html-clean`, `/aria`, `/screenshot` endpoints
- All `/save-session`, `/load-session` endpoints
- All advanced endpoints (network interception, etc.)
- Error codes and responses
- Authentication (if applicable)

**Read this if**: You're building automation and need exact API signatures

---

## Concept Index

**Quick lookup by topic:**

| Concept | First Mention | Deep Dive | Advanced |
|---------|---------------|-----------|----------|
| Persistent Browser | CORE_CONCEPTS §1 | — | ADVANCED_TECHNIQUES §9 (perf) |
| Selectors | CORE_CONCEPTS §3 | DEVELOPER_DEBUGGING §2 | ADVANCED_TECHNIQUES §1 (portals) |
| Portals | CLAUDE.md (mention) | ADVANCED_TECHNIQUES §1 | — |
| Recipes | CLAUDE.md (role 2) | ADVANCED_TECHNIQUES §4 | — |
| PrimeWiki | CLAUDE.md (role 3) | ADVANCED_TECHNIQUES §5 | — |
| Sessions | CORE_CONCEPTS §8 | QUICK_START §3 | DEVELOPER_DEBUGGING §5 |
| Verification | CLAUDE.md (principle) | CORE_CONCEPTS §5 | ADVANCED_TECHNIQUES §8 |
| LOOK-ACT-VERIFY | CLAUDE.md (principle) | DEVELOPER_DEBUGGING §1 | — |
| Bot Evasion | — | — | ADVANCED_TECHNIQUES §6 |
| Knowledge Decay | — | — | DEVELOPER_DEBUGGING §6 |
| Haiku Swarm | — | — | ADVANCED_TECHNIQUES §2 |

---

## Reading Recommendations by Role

### If You're a Web Automation Beginner

1. [QUICK_START.md](./QUICK_START.md) - Get hands-on (5 min)
2. [CORE_CONCEPTS.md](./CORE_CONCEPTS.md) - Understand concepts (20 min)
3. Try automating a simple site (login + navigate)
4. [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md) - When you hit issues

### If You're a Software Engineer

1. [CORE_CONCEPTS.md](./CORE_CONCEPTS.md) - Architecture understanding (20 min)
2. [API_REFERENCE.md](./API_REFERENCE.md) - Integration details (10 min)
3. [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md) - Optimization patterns (30 min)
4. [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md) - Testing & debugging (20 min)

### If You're an AI/ML Researcher

1. [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md) §2 - Haiku Swarm coordination (15 min)
2. [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md) §8 - Confidence scoring (10 min)
3. [CORE_CONCEPTS.md](./CORE_CONCEPTS.md) §7 - Multi-channel encoding (15 min)
4. Existing recipes in `recipes/` and PrimeWiki in `primewiki/`

### If You're Maintaining This System

1. [CLAUDE.md](./CLAUDE.md) - Your responsibilities (10 min)
2. All guides - Full mastery (120+ min)
3. Registry files - Current state (10 min)
4. Skill files in `canon/prime-browser/skills/` - Learning tracking

---

## Document Maintenance

### Last Updated

- [CLAUDE.md](./CLAUDE.md): 2026-02-15
- [QUICK_START.md](./QUICK_START.md): 2026-02-15
- [CORE_CONCEPTS.md](./CORE_CONCEPTS.md): 2026-02-15
- [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md): 2026-02-15
- [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md): 2026-02-15
- [GUIDES_INDEX.md](./GUIDES_INDEX.md): 2026-02-15

### Version

All guides aligned with **Phase 3 Task #4** refactoring (2026-02-15).

### Next Review

- **When**: 2026-03-15 (1 month)
- **Review for**: Selector stability, new recipes, knowledge decay
- **Update**: Registry entries, new portals, changed selectors

---

## Cross-References

### From CLAUDE.md

- "How do I start?" → [QUICK_START.md](./QUICK_START.md)
- "How does it work?" → [CORE_CONCEPTS.md](./CORE_CONCEPTS.md)
- "Advanced patterns?" → [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md)
- "Debugging?" → [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)

### From QUICK_START.md

- "Understand it?" → [CORE_CONCEPTS.md](./CORE_CONCEPTS.md)
- "Learn more?" → [CORE_CONCEPTS.md](./CORE_CONCEPTS.md)
- "Debugging?" → [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)

### From CORE_CONCEPTS.md

- "Try it?" → [QUICK_START.md](./QUICK_START.md)
- "Debug?" → [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)
- "Advanced?" → [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md)

### From ADVANCED_TECHNIQUES.md

- "Debug?" → [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)
- "API?" → [API_REFERENCE.md](./API_REFERENCE.md)
- "Recipes?" → [RECIPE_SYSTEM.md](./RECIPE_SYSTEM.md)

### From DEVELOPER_DEBUGGING.md

- "Learn basics?" → [QUICK_START.md](./QUICK_START.md)
- "Understand concepts?" → [CORE_CONCEPTS.md](./CORE_CONCEPTS.md)
- "Advanced?" → [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md)

---

## For New Contributors

If you're adding documentation:

1. **Keep it focused** - One guide = one clear purpose
2. **Link to related guides** - No information isolated
3. **Update this index** - Add your new guide here
4. **Check cross-references** - Link back from related docs
5. **Test links** - Verify all `[link](./file.md)` work
6. **Update last-updated dates** - So readers know freshness

---

## Quick Decision Tree

```
I'm new to Solace Browser
  → Start: QUICK_START.md
  → Then: CORE_CONCEPTS.md

I understand basics
  → Next: ADVANCED_TECHNIQUES.md

Something is broken
  → Go: DEVELOPER_DEBUGGING.md

I need exact API details
  → Check: API_REFERENCE.md

I'm building a recipe
  → See: ADVANCED_TECHNIQUES.md §4
  → Verify: DEVELOPER_DEBUGGING.md §1

I need to update my knowledge
  → Read: CORE_CONCEPTS.md + ADVANCED_TECHNIQUES.md
  → Update: Skills in canon/prime-browser/skills/

I need to share knowledge
  → Create: Recipe + PrimeWiki node
  → Update: RECIPE_REGISTRY.md + PRIMEWIKI_REGISTRY.md
  → Commit: Git add + commit
```

---

## Video Scripts (Future)

For each guide, a ~5-10 minute video would cover:

- **QUICK_START.md**: "5-Minute Solace Browser Tutorial"
- **CORE_CONCEPTS.md**: "How Solace Browser Works"
- **ADVANCED_TECHNIQUES.md**: "Mastering Solace: Portals, Recipes, Optimization"
- **DEVELOPER_DEBUGGING.md**: "Debugging Web Automation: Systematic Approach"

---

**Navigation Complete!**

Choose your starting point above and begin learning.

---

**Auth**: 65537 | **Status**: Phase 3 Task #4 Complete
