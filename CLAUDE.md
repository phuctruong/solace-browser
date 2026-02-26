# CLAUDE.md — Solace Browser
# Stillwater v1.5.0 | Software 5.0 Edition | Updated: 2026-02-25

## Project Identity
```
RUNG_TARGET:     65537 (production-ready, community-driven)
NORTHSTAR:       Phuc_Forecast
PROJECT:         Solace Browser
DOMAIN:          OAuth3 Reference Implementation
                 Browser Automation + Recipe Engine + PM Triplets
ARCHITECTURE:    Phase 0-6 (foundation → multi-platform) + 14 sessions
VISIBILITY:      OSS (open source, GitHub public)
VISION:          Reference implementation of OAuth3 spec
                 Proves OAuth3 is feasible + necessary
                 Feeds into solaceagi.com (cloud twin)
```

---

## CRITICAL LAW: Software 5.0 Non-Negotiables

### 1. FALLBACK BAN (Absolute — No Exceptions)
**Rule: Fallbacks are a blackhole for AI hallucination. Stop and fix instead.**

✗ FORBIDDEN:
```python
except Exception: pass
except Exception: return None/""/{}/[]
# fake browser states, mock responses in production code
# silent failure (if login fails, FAIL LOUDLY)
# broad exception catches
```

✓ REQUIRED:
```python
except SpecificError as e:
    evidence.log_event("ERROR", e)
    raise  # Fail loud
```

**LEC Crystallized:** `LEC-FALLBACK-BAN` (2026-02-24)

---

### 2. DISPATCH RULES (Mandatory)
**Rule: Complex work belongs with specialists.**

**Inline Work Limit:** <50 lines
- Small fixes, clarifications → stay inline (haiku)
- Feature implementation, testing, architecture → dispatch (sonnet/opus)

**Main Session Role:** Orchestrator (haiku)
- Coordinate phases
- Review evidence
- Update roadmap + memory

**Sub-Agent Roles:** Specialists (sonnet/opus)
- Coder (sonnet): implementation, tests, recipes
- Planner (sonnet): architecture, design, proof-of-concept
- Auditor (opus): security, OAuth3 compliance, cryptography

**Dispatch Protocol:**
1. Declare rung_target before dispatch
2. Paste full skill content (prime-safety ALWAYS FIRST)
3. Load NORTHSTAR.md + ROADMAP.md into CNF capsule
4. Define stop rules (EXIT_PASS / EXIT_BLOCKED / EXIT_NEED_INFO)
5. Integration rung = MIN(all sub-agent rungs)

---

### 3. SKILLS (4 Core — Production Grade)

**All skills sourced from:** `/home/phuc/projects/stillwater/skills/`

#### 3.1 prime-safety v2.1.0 — ALWAYS LOAD FIRST
- Fail-closed security layer
- Prevents: prompt injection, scope bypass, token leakage, unauthorized API calls
- **Critical for OAuth3 implementation**
- **When to use:** Every agent, every phase

#### 3.2 prime-coder v2.1.0 — For Implementation
- Deterministic evidence gate: red test → green test → commit
- Rung ladder: code quality = rung achieved
- **When to use:** Coder agents, Phases 0-6

#### 3.3 phuc-orchestration v1.0.0 — For Context Governance
- Context governor: prevents > 100 lines inline
- 3-skill limit per session
- **When to use:** Main orchestrator session

#### 3.4 phuc-context v1.1.0 — For Anti-Rot
- Anti-rot substrate (memory doesn't decay)
- **When to use:** Memory updates, long-running projects

---

## PHASE STRUCTURE

### Phases 0-6 (14 Sessions Total)

| Phase | Name | Goal | Rung | Sessions | Status |
|-------|------|------|------|----------|--------|
| **0** | Foundation | Directory structure, docs, skeleton | 641 | 1 | 🎯 READY |
| **1** | OAuth3 Core | Token management, scope gates, evidence chain | 274177 | 2 | Awaiting Phase 0 |
| **2** | Browser Automation | Playwright integration, page interaction, screenshots | 641 | 2 | Awaiting Phase 1 |
| **3** | Recipe Engine | Prime Mermaid parser, deterministic execution | 641 | 2 | Awaiting Phase 2 |
| **4** | PM Triplets | User/Task/Context models, composition | 641 | 2 | Awaiting Phase 3 |
| **5** | Store Integration | Stillwater Store (read recipes, submit recipes) | 641 | 2 | Awaiting Phase 4 + solaceagi Phase 3 |
| **6** | Multi-Platform | Gmail, LinkedIn, Slack, GitHub, Notion recipes | 641 | 3 | Awaiting Phase 5 |

**Total:** 14 sessions to rung 65537

**See:** `/home/phuc/projects/solace-browser/ROADMAP.md` (full spec)

---

## ARCHITECTURE DECISIONS (7 Locked Patterns)

### Decision 1: Playwright (Not Selenium)
- Chromium + Firefox + WebKit support
- Better debugging (network interception)
- Modern async/await
- **Why:** Faster, easier to audit, better for evidence capture

### Decision 2: OAuth3 Scope Gates on Every Action
- Every click/fill/submit wrapped in scope check
- Revocation halts execution immediately
- **Why:** Proves OAuth3 is feasible; builds trust with users

### Decision 3: Recipe = Deterministic, Cached, Shareable
- Prime Mermaid DAG format
- Same seed → same output (forever)
- Community can submit recipes to Stillwater Store
- **Why:** Composable, auditable, high-margin (caching)

### Decision 4: PM Triplets (User + Task + Context)
- User model (identity, preferences)
- Task model (goal, inputs, success criteria)
- Context model (state, decisions, remaining steps)
- **Why:** Enables composition (A's output = B's input)

### Decision 5: Evidence by Default
- OAuth3 audit trail (JSONL, hash-chained)
- Browser evidence (screenshots, DOM snapshots, network log)
- Per-step artifacts
- **Why:** Part 11 compliance + audit-ready

### Decision 6: PM Triplets Enable Composition
- Output of email summarizer = Input to LinkedIn poster
- No glue code needed
- Community recipes can be chained
- **Why:** Flywheel effect (recipes compound)

### Decision 7: Never-Worse Law
- Recipe hit rate only goes up, never down
- If new recipe < baseline, use baseline
- No silent degradation
- **Why:** Builds trust; predictable outcomes

---

## DIRECTORY STRUCTURE

```
solace-browser/
  ├── .claude/
  │   ├── CLAUDE.md                     ← this file
  │   ├── commands/                     ← synced from solace-cli
  │   └── memory/
  │
  ├── NORTHSTAR.md                      ← vision + metrics
  ├── ROADMAP.md                        ← full build plan
  ├── CLAUDE.md                         ← this file
  ├── README.md                         ← developer quickstart
  │
  ├── src/
  │   ├── oauth3/                       ← OAuth3 implementation
  │   │   ├── __init__.py
  │   │   ├── vault.py                  ← token storage (AES-256-GCM)
  │   │   ├── scopes.py                 ← scope enforcement
  │   │   └── evidence.py               ← audit trail (JSONL)
  │   │
  │   ├── browser/                      ← Playwright wrapper
  │   │   ├── __init__.py
  │   │   ├── context.py                ← browser context + OAuth3 gates
  │   │   ├── page.py                   ← page navigation + evidence
  │   │   └── evidence.py               ← screenshot + DOM capture
  │   │
  │   ├── recipes/                      ← Recipe engine
  │   │   ├── __init__.py
  │   │   ├── parser.py                 ← Prime Mermaid parser
  │   │   ├── executor.py               ← deterministic execution
  │   │   ├── cache.py                  ← recipe caching
  │   │   └── registry.py               ← recipe catalog
  │   │
  │   ├── triplets/                     ← PM Triplet models
  │   │   ├── __init__.py
  │   │   ├── user.py                   ← User model
  │   │   ├── task.py                   ← Task model
  │   │   └── context.py                ← Context model
  │   │
  │   └── util/
  │       ├── crypto.py                 ← AES-256-GCM
  │       └── evidence.py               ← evidence bundle generation
  │
  ├── recipes/
  │   ├── gmail/
  │   │   ├── triage-inbox.mmd
  │   │   ├── compose-draft.mmd
  │   │   └── send-email.mmd
  │   ├── linkedin/
  │   │   ├── post-update.mmd
  │   │   ├── send-message.mmd
  │   │   └── comment-post.mmd
  │   └── ... (per-platform)
  │
  ├── tests/
  │   ├── unit/
  │   │   ├── test_oauth3_vault.py
  │   │   ├── test_scope_gates.py
  │   │   ├── test_recipe_parser.py
  │   │   └── test_triplets.py
  │   ├── integration/
  │   │   └── test_end_to_end.py
  │   └── conftest.py
  │
  ├── docs/
  │   ├── oauth3-spec.md                ← OAuth3 reference
  │   ├── recipe-format.md              ← Prime Mermaid format
  │   ├── api.md                        ← HTTP API
  │   └── examples/                     ← example recipes + usage
  │
  ├── dragon/                           ← Dragon Rider memory
  │   ├── evolution/                    ← session logs
  │   ├── learning/                     ← architectural patterns
  │   ├── questions/                    ← Q&A database
  │   └── journal/
  │
  ├── scratch/                          ← gitignored working files
  │   └── todo/                         ← phase checklists
  │
  └── .github/
      └── workflows/
          ├── test.yml                  ← pytest on PR
          └── audit.yml                 ← bandit + semgrep on auth changes
```

---

## FORBIDDEN STATES (Software 5.0 Invariants)

| State | Example | Why Forbidden | Fix |
|-------|---------|---------------|----|
| `SKILL_LESS_DISPATCH` | Dispatch without skills | No safety checks | Always paste full skill content |
| `SCOPE_BYPASS` | Skip scope check | Security breach | Every action requires scope check |
| `TOKEN_PLAINTEXT` | Store token as plain text | Lane A violation | Use AES-256-GCM always |
| `REVOCATION_IGNORED` | Revoked token still works | Security breach | Check revocation status at every action |
| `SILENT_FAILURE` | Network error? Return empty | Fallback ban | Raise error, fail loud |
| `RECIPE_NONDETERMINISM` | Same input, different output | Breaks caching | Use deterministic primitives only |
| `TRIPLET_MISSING` | Execute without user/task/context | Composition breaks | Load all 3 models before execution |
| `EVIDENCE_OPTIONAL` | Skip audit trail | Audit trail broken | Evidence is mandatory, not optional |

---

## HOW TO RUN A PHASE

### Phase 0 (Foundation)
```bash
cd /home/phuc/projects/solace-browser
cat scratch/todo/PHASE_0_Foundation.md
# Read checklist
# Codex builds: directory structure + docs + skeleton
```

### Phase 1-6 (Implementation)
```bash
cat scratch/todo/PHASE_N_[Name].md
# Codex builds: features, tests, recipes
```

### Review Evidence
```bash
# After each phase:
cat evidence/tests.json                 # All tests pass?
cat evidence/repro_red.log              # Red test before fix
cat evidence/repro_green.log            # Green test after fix
```

### Update Case Study
```bash
/update-case-study Phase_N [rung-achieved]
```

---

## EVIDENCE REQUIREMENTS (Rung 641 Minimum)

Every phase must produce:

1. **tests.json** — All tests, pass/fail status
2. **repro_red.log** — Failures BEFORE code
3. **repro_green.log** — Passing AFTER code
4. **plan.json** — Implementation plan + acceptance criteria

---

## RUNG SYSTEM (Quality Tiers)

| Rung | Meaning | Example |
|------|---------|---------|
| **641** | "Runs without error" | Unit tests pass locally |
| **274177** | "Replays consistently" | Issue token → revoke → actions blocked |
| **65537** | "Survives adversarial" | Revoke mid-action → immediate halt |

---

## BELT PROGRESSION

| Belt | Milestone |
|------|-----------|
| White | First recipe runs (fork + modify) |
| Yellow | 5 recipes submitted to Stillwater Store |
| Orange | Recipe hit rate > 30% (real adoption) |
| Green | Rung 65537 achieved (all tests pass) |
| Blue | 1,000+ GitHub stars |
| Black | OAuth3 external adopters |

---

## SYNCHRONIZATION WITH SOLACEAGI

**Cross-Project Dependencies:**

```
solace-browser Phase 0-4 (OAuth3 + recipe engine + PM triplets)
  ↓ (independent, can run in parallel)

solaceagi Phase 0-2 (foundation + OAuth3 vault + LLM router)
  ↓

solace-browser Phase 5 (Store Integration)
  DEPENDS ON: solaceagi Phase 3 (Stillwater Store integration)
  ↓

solaceagi Phase 4 (Twin Browser)
  DEPENDS ON: solace-browser Phases 1-5 (fully functional browser + recipes)
  ↓

solace-browser Phase 6 (Multi-Platform)
  Can run in parallel with solaceagi Phases 4-6
```

**See:** Both ROADMAP.md files for dependency markers `[BLOCKS: ...]` and `[BLOCKED_BY: ...]`

---

## QUICK REFERENCE

| Item | Location |
|------|----------|
| Vision + metrics | NORTHSTAR.md |
| Build plan | ROADMAP.md |
| Phase checklists | scratch/todo/ |
| Architectural patterns | dragon/learning/ |
| Q&A database | dragon/questions/stillwater.jsonl |
| Developer guide | README.md |
| OAuth3 spec | docs/oauth3-spec.md |
| Recipe format | docs/recipe-format.md |

---

## STATUS: 🎯 Ready for Phase 0

**Next Step:**
```bash
/build Phase_0_Foundation
```

---

**Signature:** Software 5.0 Edition
**Rung Target:** 65537
**Northstar:** Phuc_Forecast
**Visibility:** OSS (GitHub public)
**Last Updated:** 2026-02-25
