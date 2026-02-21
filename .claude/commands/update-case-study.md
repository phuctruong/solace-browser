# /update-case-study — Record solace-browser Build Results

After a build session completes, update the case study file with what was built, the rung achieved, and belt progression.

## Usage

```
/update-case-study [phase] [rung-achieved]
/update-case-study oauth3-core 641
/update-case-study gmail-recipes 641
/update-case-study substack-recipes 274177
```

ARGUMENTS: $ARGUMENTS

## Case Study File

`/home/phuc/projects/stillwater/case-studies/solace-browser.md`

## Belt Progression Criteria

| Belt | Automatic when... |
|------|------------------|
| White | Phase 1 done (LinkedIn MVP, rung 641) — ALREADY ACHIEVED |
| Yellow | OAuth3 foundation ships (oauth3-core + consent UI at rung 641) |
| Orange | 70% recipe hit rate + OAuth3 spec published to stillwater |
| Green | 10 platforms, all OAuth3-bounded, rung 65537 on at least 3 |
| Blue | solaceagi.com cloud execution live 24/7 |
| Black | OAuth3 is the standard. Models are commodities. Skills are capital. |

## Instructions for Claude

When user runs `/update-case-study [phase] [rung-achieved]`:

### Step 1 — Validate Arguments

1. `phase` must match a known phase (see Phase Registry in /build command)
2. `rung-achieved` must be one of: 641, 274177, 65537

If any argument is missing: list valid values and stop. Do NOT guess.

### Step 2 — Read Current Case Study

Read `/home/phuc/projects/stillwater/case-studies/solace-browser.md`

Extract:
- Current belt
- Current rung
- What is already listed as completed
- Current metrics (recipe hit rate, platform count, OAuth3 status)

### Step 3 — Ask for Build Artifacts

If user has not provided artifact details:

```
What artifacts were produced in this build session?
  1. Files created (list paths)
  2. Tests passing? (command used + pass/fail count)
  3. Evidence bundle exists? (evidence/plan.json, evidence/tests.json)
  4. Git commit SHA (if committed)
  5. API endpoints added (if any)
  6. Any blockers encountered?

You can paste the agent's output directly and I will extract these.
```

### Step 4 — Check Belt Progression

Apply belt criteria:

```
Current belt: [X]
Rung achieved: [rung]

Belt check:
  White:  ACHIEVED (Phase 1 done)
  Yellow: [ACHIEVED | not yet — need: oauth3-core + oauth3-consent at rung 641]
  Orange: [not yet — need: 70% recipe hit rate + spec published]
  Green:  [not yet — need: 10 platforms + rung 65537 on 3+]

Belt upgrade: [none | WHITE → YELLOW | etc.]
```

### Step 5 — Update Case Study File

Append this build record:

```markdown
## Build Record: [phase] — 2026-02-21

**Phase**: [phase]
**Rung achieved**: [rung]
**Belt after**: [belt]
**Date**: 2026-02-21

### What was built
[List files created, API endpoints added, OAuth3 modules implemented]

### Evidence bundle
- Files created: [list]
- Tests: [pass/fail + count + command]
- Git commit: [SHA or "not committed yet"]
- evidence/plan.json: [exists | missing]
- evidence/tests.json: [exists | missing]

### Metrics updated
[e.g., "OAuth3 implementation: 0% → 60%", "Platforms with OAuth3: 0 → 1"]

### Acceptance tests passed
[List which acceptance tests from ROADMAP.md passed]

### Next phase
[Extract from ROADMAP.md what comes next after this phase]
```

Also update the metrics table at the top of the case study (recipe hit rate, platform count, OAuth3 status).
If belt progressed: update the `**Belt**: X` line at the top.
If rung progressed: update the `**Rung**: X` line.

Write the updated file. Confirm: "Updated case-studies/solace-browser.md".

### Step 6 — Update Memory

Auto-save to `.claude/memory/context.md`:

```
current_phase_solace-browser: [phase] completed 2026-02-21
rung_solace-browser: [rung-achieved]
belt_solace-browser: [belt]
oauth3_status: [what was implemented]
```

### Step 7 — Suggest Next Action

Read ROADMAP.md and output:

```
=== CASE STUDY UPDATED ===

Project:     solace-browser
Phase done:  [phase]
Rung:        [rung-achieved]
Belt:        [belt] [upgrade note if applicable]
Date:        2026-02-21

Next phase from ROADMAP:
  [next phase name + 1 line goal]

Suggested next command:
  /build [next-phase]

Or check full ecosystem status:
  /status (solace-browser) | /build --list
```

## Related Commands

- `/build [phase]` — Launch the next build session
- `/status` — View project status after update
- `/northstar` — Load NORTHSTAR for alignment check
