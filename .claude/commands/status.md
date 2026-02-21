# /status — solace-browser Project Status

Read case study + NORTHSTAR metrics and display the current state: belt, rung, phase, and next recommended action.

## Usage

```
/status                # Full project status
/status --rungs        # Rung ladder view only
/status --next         # Next recommended build action only
/status --phases       # All phases: done / in-progress / todo
```

ARGUMENTS: $ARGUMENTS

## Instructions for Claude

When user runs `/status`:

### Step 1 — Read Case Study

Read: `/home/phuc/projects/stillwater/case-studies/solace-browser.md`

Extract:
- Current belt
- Current rung
- Completed phases
- Active blockers
- Last build date

### Step 2 — Read NORTHSTAR Metrics

Read: `/home/phuc/projects/solace-browser/NORTHSTAR.md`

Extract:
- Community Resonance Score target
- Recipe hit rate target (70% → $5.75 COGS)
- OAuth3 milestone progress

### Step 3 — Read Memory

Read: `/home/phuc/projects/solace-browser/.claude/memory/context.md` (if exists)

Extract: current_phase, rung_*, blocker_* keys

### Step 4 — Display Status

```
==================================================
SOLACE-BROWSER STATUS — 2026-02-21
==================================================

NORTHSTAR: OAuth3 moat + 70% recipe hit rate → $5.75 COGS → economic moat
CONSTITUTION: OAUTH3-WHITEPAPER.md

BELT: [current belt]
RUNG: [current rung]

PHASES:
  Phase 1:   LinkedIn MVP     ✅ DONE (Rung 641, 6 recipes)
  Phase 1.5: OAuth3 Foundation → CURRENT
    oauth3-core    [ ] Rung 641  ← START HERE
    oauth3-consent [ ] Rung 641  (blocked by oauth3-core)
    oauth3-stepup  [ ] Rung 641  (blocked by oauth3-consent)
    oauth3-spec    [ ] Rung 641  (publish to stillwater — parallel)
  Phase 2:   Platform Recipes  ⏳ Blocked by Phase 1.5
    gmail-recipes      [ ] Rung 641  (4 recipes)
    substack-recipes   [ ] Rung 641  (FIRST MOVER — no competitors)
    twitter-recipes    [ ] Rung 641  (3 recipes)
  Phase 3:   Cloud Layer       ⏳ Blocked by Phase 2

BLOCKERS: [list any active blockers]
LAST BUILD: [date from case study]

NORTHSTAR METRICS:
  Recipe hit rate: [now] → target 70%
  Platforms covered: 1 (LinkedIn) → target 10 (Q2 2026)
  OAuth3 compliance: 0% → target 100% (all recipes OAuth3-bounded)
  CRS: — → target 0.5

BELT PROGRESSION:
  White  [✅] LinkedIn Phase 1 done
  Yellow [ ] OAuth3 foundation ships ← NEXT MILESTONE
  Orange [ ] 70% recipe hit rate + OAuth3 spec published
  Green  [ ] 10 platforms, all OAuth3-bounded
  Blue   [ ] solaceagi.com live — cloud execution
  Black  [ ] OAuth3 is the standard. Models are commodities. Skills are capital.

NEXT ACTION:
  /build oauth3-core   (Phase 1.5 — highest leverage: all future recipes depend on this)

==================================================
```

### When user runs `/status --rungs`

```
RUNG LADDER — solace-browser:

Rung 641 (local correctness):
  Phase 1 LinkedIn MVP: ✅ achieved
  Phase 1.5 OAuth3:     [ ] not yet
  Phase 2 Recipes:      [ ] not yet

Rung 274177 (stability + replay):
  [ ] not yet (requires Phase 2 completion)

Rung 65537 (production + security gate):
  [ ] not yet (requires cloud deployment + security audit)

Next rung target: 641 (for oauth3-core)
Command: /build oauth3-core
```

### When user runs `/status --next`

```
NEXT ACTION (highest leverage):

1. /build oauth3-core
   Why: All future recipes depend on OAuth3 foundation.
        Without it, every new recipe is ungoverned and ungovernable.
        This is the Yellow Belt milestone.

2. /build oauth3-spec (parallel)
   Why: Publishing the spec to stillwater establishes the open standard.
        Do this alongside oauth3-core — it's pure writing, no code risk.

3. /build gmail-recipes (after oauth3-core ships)
   Why: Gmail is first-mover advantage. No competitor has OAuth3-bounded Gmail automation.
```

## Related Commands

- `/build [phase]` — Launch build session for a phase
- `/northstar` — Load NORTHSTAR for solace-browser
- `/update-case-study [phase] [rung]` — Record completed build
- `/scout [area]` — Map a codebase area before building
