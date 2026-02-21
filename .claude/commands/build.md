# /build — Launch Phuc Swarm Build Session (solace-browser)

Start a phuc swarm build session for a solace-browser phase. Reads NORTHSTAR + ROADMAP, assembles the correct agent team, and produces the full session prompt.

## Usage

```
/build [phase]
/build oauth3-core        # Phase 1.5 — OAuth3 Core Module
/build oauth3-consent     # Phase 1.5 — OAuth3 Consent UI
/build oauth3-stepup      # Phase 1.5 — Step-Up Authorization
/build oauth3-spec        # Phase 1.5 — OAuth3 Spec Publication (cross-posts to stillwater)
/build gmail-recipes      # Phase 2 — Gmail Recipes (4 recipes)
/build substack-recipes   # Phase 2 — Substack Recipes (FIRST MOVER)
/build twitter-recipes    # Phase 2 — Twitter/X Recipes
/build cloud-api          # Phase 3 — solaceagi.com Cloud Layer
/build --list             # Show all phases + current status
```

ARGUMENTS: $ARGUMENTS

## Phase Registry

| Phase | ID | Target | Status |
|-------|----|--------|--------|
| OAuth3 Core Module | oauth3-core | Rung 641 | BUILD NEXT |
| OAuth3 Consent UI | oauth3-consent | Rung 641 | Blocked by oauth3-core |
| Step-Up Authorization | oauth3-stepup | Rung 641 | Blocked by oauth3-consent |
| OAuth3 Spec Publication | oauth3-spec | Rung 641 | Parallel with oauth3-core |
| Gmail Recipes | gmail-recipes | Rung 641 | Blocked by oauth3-core |
| Substack Recipes | substack-recipes | Rung 641 | Blocked by oauth3-core |
| Twitter/X Recipes | twitter-recipes | Rung 641 | Blocked by oauth3-core |
| Cloud API | cloud-api | Rung 641 | Blocked by Phase 2 |

## Swarm Team for Every Build

| Agent | Model | Skill Pack | When |
|-------|-------|-----------|------|
| Scout | haiku | prime-safety | Always first — map codebase, identify gaps |
| Forecaster | sonnet | prime-safety + phuc-forecast | Always — failure modes, stop rules |
| Coder | sonnet | prime-safety + prime-coder | Implementation |
| Skeptic | sonnet | prime-safety + prime-coder + phuc-forecast | Verification (rung 274177+) |

## Instructions for Claude

When user runs `/build [phase]`:

### Step 1 — NORTHSTAR Alignment Check

1. Read `/home/phuc/projects/solace-browser/NORTHSTAR.md`
2. Display: Mission (1 line) + Northstar Metric (CRS target) + Current Belt/Rung
3. Confirm: does the requested phase serve the northstar?
4. Key alignment check: Does this phase advance the 70% recipe hit rate or OAuth3 moat?
5. Output ALIGNED or DRIFT.

### Step 2 — ROADMAP Phase Extraction

1. Read `/home/phuc/projects/solace-browser/ROADMAP.md`
2. Find the section matching `[phase]` argument (fuzzy match on phase name/keyword)
3. Extract: Goal, Task list, Build Prompt, Rung target, Evidence required, Acceptance tests
4. If phase not found: list all available phases (from table above) and stop.

### Step 3 — Case Study Status

1. Read `/home/phuc/projects/stillwater/case-studies/solace-browser.md`
2. Show: current belt, current rung, what's done, what's blocked
3. Confirm this phase is the correct next step (or warn if a blocker exists).

### Step 4 — Scout Dispatch (haiku)

Dispatch a Scout agent to map the codebase before coding begins.

```
=== SCOUT DISPATCH ===
Role:        scout
Model:       haiku
Skill pack:  prime-safety (full content from /home/phuc/projects/stillwater/skills/prime-safety.md)
Rung target: 641

NORTHSTAR (load first — MANDATORY):
[paste full NORTHSTAR.md content]

Task (CNF Capsule):
  You are a Scout agent for solace-browser (OAuth3 reference implementation).
  Before stating which NORTHSTAR metric this work advances, answer:
    "Which NORTHSTAR metric does this work advance?"
    (Answer: OAuth3 recipe hit rate → economic moat)

  Project path: /home/phuc/projects/solace-browser/
  Phase goal: [extracted from ROADMAP]

  Read these files to understand current state:
    - solace_browser_server.py (existing /run-recipe endpoint)
    - ui_server.py (existing UI routes)
    - recipes/ directory (existing recipe format)
    - primewiki/ directory (PM triplets that exist)

  Output gap_report.json:
  {
    "phase": "[phase]",
    "files_relevant": [...],
    "files_exist": [...],
    "files_missing": [...],
    "blockers": [...],
    "existing_endpoint_schema": {...},
    "northstar_metric_advanced": "recipe_hit_rate + OAuth3_moat"
  }

  Stop rules:
  - EXIT_PASS: gap_report.json complete, northstar metric stated
  - EXIT_BLOCKED: fatal blocker found (list it, do not proceed)
  - EXIT_NEED_INFO: required file unreadable
```

### Step 5 — Forecaster Dispatch (sonnet)

After scout returns, dispatch Forecaster.

```
=== FORECASTER DISPATCH ===
Role:        forecaster
Model:       sonnet
Skill pack:  prime-safety + phuc-forecast (full content from skills/)
Rung target: [from ROADMAP phase]

NORTHSTAR (load first — MANDATORY):
[paste full NORTHSTAR.md content]

Task (CNF Capsule):
  You are a Forecaster agent applying phuc-forecast to solace-browser build session.
  Before starting, state: "Which NORTHSTAR metric does this work advance?"

  Project: solace-browser (OAuth3 reference implementation)
  Phase: [phase]
  Goal: [goal from ROADMAP]
  Scout gap report: [paste gap_report.json]
  NORTHSTAR metric: OAuth3 moat + recipe hit rate → 70%

  Required output (DREAM → FORECAST → DECIDE → ACT → VERIFY):

  DREAM:
    - Goal + success metrics (concrete: acceptance tests from ROADMAP)
    - Constraints: no breaking changes to existing /run-recipe endpoint
    - Non-goals: no new platforms until OAuth3 foundation is solid

  FORECAST:
    - Top 5 failure modes (ranked by P × Impact)
    - Risk: browser compatibility, scope validation edge cases, token expiry race conditions
    - Risk level: MED

  DECIDE:
    - Chosen approach (incremental over existing server code)
    - Alternatives considered
    - Stop rules: EXIT_PASS conditions, EXIT_BLOCKED conditions

  ACT:
    - Step plan with checkpoints
    - Artifacts: new files to create, endpoints to add, tests to write
    - Rung target: [from ROADMAP]

  VERIFY:
    - Tests: run acceptance tests from ROADMAP Build Prompt verbatim
    - Evidence required: repro_red.log, repro_green.log, tests.json
    - Falsifiers: what would prove this FAILED

  Stop rules:
  - EXIT_PASS: All 5 sections complete, no FACT_INVENTION, no SKIP_VERIFY
  - EXIT_NEED_INFO: Missing required inputs
  - EXIT_BLOCKED: Risk HIGH with no mitigation
```

### Step 6 — Build Prompt Output

After Forecaster completes, output the full build prompt the user can paste into a new session:

```
========================================
PHUC SWARM BUILD SESSION — solace-browser
========================================
Project:     solace-browser
Phase:       [phase]
Rung target: [rung]
Date:        2026-02-21
NORTHSTAR:   OAuth3 moat + 70% recipe hit rate → $5.75 COGS → economic moat
Status:      ALIGNED

NORTHSTAR (loaded):
[paste key lines from NORTHSTAR.md]

SCOUT FINDINGS:
[gap_report.json summary]

FORECAST:
[paste DREAM + FORECAST + DECIDE sections]

BUILD TASK (paste into new session):
---
[paste the Build Prompt from ROADMAP verbatim — the full text under "Build Prompt"]
---

SKILL PACK (paste into every sub-agent):
  1. skills/prime-safety.md (ALWAYS FIRST)
     Source: /home/phuc/projects/stillwater/skills/prime-safety.md
  2. skills/prime-coder.md (for coder/skeptic agents)
     Source: /home/phuc/projects/stillwater/skills/prime-coder.md
  3. skills/phuc-forecast.md (for planner/skeptic agents)
     Source: /home/phuc/projects/stillwater/skills/phuc-forecast.md

SCRATCH DIR MANDATE:
  All intermediate work → /home/phuc/projects/solace-browser/scratch/
  Only FINAL verified artifacts move to project proper.
  scratch/ is gitignored.

RUNG TARGET: [rung]
EVIDENCE REQUIRED: PATCH_DIFF, repro_red.log, repro_green.log, tests.json
NEXT COMMAND AFTER BUILD: /update-case-study solace-browser [phase] [rung-achieved]
========================================
```

### Step 7 — Dispatch Coder (sonnet)

If user confirms "go", dispatch Coder with full CNF capsule:

```
=== CODER DISPATCH ===
Role:        coder
Model:       sonnet
Skill pack:  prime-safety + prime-coder (full content from skills/)
Rung target: [from ROADMAP]

NORTHSTAR (load first — MANDATORY):
[paste full NORTHSTAR.md content]

Task (CNF Capsule):
  You are a Coder agent for solace-browser.
  Before starting, state: "Which NORTHSTAR metric does this work advance?"
  (Answer: OAuth3 moat + recipe hit rate. If output does not advance either → NEED_INFO, stop.)

  Project: solace-browser at /home/phuc/projects/solace-browser/
  Phase: [phase]
  Goal: [goal]

  Forecaster plan: [paste ACT section from forecaster]
  Scout gap report: [paste gap_report.json]

  Build steps (from ROADMAP — paste verbatim):
  [paste Build Prompt steps from ROADMAP exactly as written]

  Rung target: [rung]
  Evidence required: PATCH_DIFF, repro_red.log, repro_green.log, tests.json

  MANDATORY:
  - Write failing test FIRST (red gate)
  - Implement minimum code to pass (green gate)
  - Run full test suite: pytest tests/ -v
  - Zero regressions on existing endpoints
  - Produce: evidence/plan.json, evidence/tests.json
  - Commit with feat: or fix: prefix
  - All working files go to scratch/ first

  Stop rules:
  - EXIT_PASS: all acceptance tests pass AND evidence artifacts exist AND rung met
  - EXIT_BLOCKED: blocker found — list it and stop, do not guess
  - EXIT_NEED_INFO: endpoint schema ambiguous
```

After coder returns, dispatch Skeptic at rung 274177+ to verify.

## Scratch Dir Policy (MANDATORY)

All intermediate work MUST go to scratch/ (gitignored):
- Working files, drafts, experiments → scratch/
- Test artifacts during development → scratch/
- Only FINAL, VERIFIED artifacts move to project proper
- This keeps the project clean and minimal

```
/home/phuc/projects/solace-browser/scratch/   ← all working files go here
```

## When user runs `/build --list`

Read ROADMAP.md and display:

```
=== SOLACE-BROWSER BUILD STATUS ===

Phase 1:   LinkedIn MVP            ✅ DONE (Rung 641)
Phase 1.5: OAuth3 Foundation       🔨 BUILD NEXT
  └─ oauth3-core    → Rung 641  [START HERE]
  └─ oauth3-consent → Rung 641  [blocked by oauth3-core]
  └─ oauth3-stepup  → Rung 641  [blocked by oauth3-consent]
  └─ oauth3-spec    → Rung 641  [parallel, publishes to stillwater]
Phase 2:   Platform Recipes        ⏳ Blocked by Phase 1.5
  └─ gmail-recipes      → Rung 641  [FIRST MOVER opportunity]
  └─ substack-recipes   → Rung 641  [FIRST MOVER in this space]
  └─ twitter-recipes    → Rung 641
Phase 3:   Cloud Layer (solaceagi) ⏳ Blocked by Phase 2

Run: /build oauth3-core to start (this is the highest-leverage next step)
```

## Forbidden States

- `SKILL_LESS_DISPATCH` — never dispatch without full skill content pasted inline
- `FORGOTTEN_CAPSULE` — never say "as discussed" or "as before" in any sub-agent prompt
- `NORTHSTAR_DRIFT_UNCHECKED` — never start without NORTHSTAR alignment check
- `RUNG_UNDECLARED` — always declare rung_target before any dispatch
- `SCOUT_SKIPPED` — always run scout before coder
- `NORTHSTAR_MISSING_FROM_CNF` — every dispatch must include full NORTHSTAR.md content
- `SCRATCH_SKIPPED` — all working files must go to scratch/ first

## Skills Location

Skills are in the stillwater repo (shared across all projects):
```
/home/phuc/projects/stillwater/skills/prime-safety.md
/home/phuc/projects/stillwater/skills/prime-coder.md
/home/phuc/projects/stillwater/skills/phuc-forecast.md
/home/phuc/projects/stillwater/skills/phuc-orchestration.md
```

## Related Commands

- `/scout [area]` — Dispatch scout to map a codebase area
- `/recipe [name]` — Create or update a recipe
- `/primewiki [site]` — Create PrimeWiki PM triplet for a site
- `/northstar` — Load solace-browser NORTHSTAR
- `/status` — Check project rung + belt + next phase
- `/update-case-study [phase] [rung]` — Record build results
