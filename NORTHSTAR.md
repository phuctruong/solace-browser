# NORTHSTAR: Phuc_Forecast — SolaceBrowser

> "A browser agent that captures recipes from what it does — so it gets better every session."

## Mission

SolaceBrowser is the **self-improving browser agent** — it automates web tasks and
captures every successful workflow as a sealed wish/recipe pair. Each session teaches
the next session.

## North Star Metric

**Recipe Capture Rate**: % of successful browser sessions that produce a reusable,
sealed wish+recipe pair in the wishes/ backlog.

Secondary metrics:
- Wish acceptance rate (BACKLOG → SEALED → DONE progression)
- Screenshot accuracy (visual diff from expected)
- Zero EXECUTE_WITHOUT_SEALED_WISH violations

## Model Strategy

| Model | Role | When |
|-------|------|------|
| **haiku** | Main session coordinator, wish tracker | Always-on |
| **sonnet** | Browser planner, skeptic reviewer | Complex automation |
| **opus** | Security audit (when accessing sensitive sites) | Rare |

## Rung Target: 641

SolaceBrowser focuses on workflow automation — rung 641 (local correctness, tests
pass, recipes sealed). Upgrade to 274177 only when promoting recipes to Stillwater Store.

## What Aligns with This Northstar

- Every task starts as a sealed wish contract (prime-wishes.md)
- Successful sessions end with a recipe file
- Screenshots captured as evidence
- `phuc-cleanup.md` runs after each session (archive-before-delete)

## What Does NOT Align

- Running browser automation without a sealed wish (EXECUTE_WITHOUT_SEALED_WISH)
- Claiming DONE without acceptance test artifacts
- Recipes that are not reproducible (must replay identically)

## See Also

- `CLAUDE.md` — prime-wishes + phuc-cleanup loaded
- `ripples/project.md` — project constraints
- `skills/prime-wishes.md` — wish contract system
- `skills/phuc-cleanup.md` — archive-first hygiene
