# /northstar — Load solace-browser NORTHSTAR

Display the NORTHSTAR for solace-browser — the guiding vision, OAuth3 positioning, and CRS metrics.

## Usage

```
/northstar                    # Display solace-browser NORTHSTAR
/northstar --check            # Verify NORTHSTAR.md is complete
/northstar --align [task]     # Check if task aligns with northstar (ALIGNED | DRIFT)
```

ARGUMENTS: $ARGUMENTS

## Instructions for Claude

When user runs `/northstar`:

1. Read `/home/phuc/projects/solace-browser/NORTHSTAR.md`
2. Read ecosystem northstar (first 30 lines): `/home/phuc/projects/stillwater/NORTHSTAR.md`
3. Also check `.claude/memory/context.md` if it exists.
4. Display:

```
=== SOLACE-BROWSER NORTHSTAR ===

MISSION: The reference implementation of consent-bound AI delegation (OAuth3)

STRATEGIC REFRAME:
  Before OAuth3: solace-browser = "browser automation with recipe system"
  After OAuth3:  solace-browser = "the reference implementation of OAuth3 —
                                   the consent standard for AI agents"

CONSTITUTION: OAUTH3-WHITEPAPER.md

NORTHSTAR METRIC: OAuth3 moat + 70% recipe hit rate → $5.75 COGS → economic moat
  Recipe hit rate: [now] → target 70%
  Platforms covered: [now] → target 10 (Q2 2026)
  OAuth3 compliance: [now] → 100% (all recipes OAuth3-bounded)

CURRENT PHASE: [from case study or memory]
BELT: [current belt]
RUNG: [current rung]

NEXT ACTION: /build oauth3-core (Phase 1.5 — all future recipes depend on this)

ECOSYSTEM NORTHSTAR:
[paste first 30 lines of stillwater/NORTHSTAR.md]

WHY OAUTH3 IS UNCOPYABLE:
  Token-revenue vendors (OpenAI, Anthropic) cannot implement OAuth3.
  OAuth3 reduces token usage to near-zero via recipe reuse.
  They would cannibalize their own revenue if they built this.
  We can. That is the moat.

6 MOATS (no competitor has all 6):
  1. Recipe system (70% cache hit → 3x cheaper COGS)
  2. PrimeWiki PM knowledge layer (domain-aware navigation)
  3. Twin architecture (local + cloud)
  4. Anti-detection (Bezier mouse, fingerprint sync)
  5. Stillwater verification (evidence-per-task, not screenshots)
  6. OAuth3 protocol (scoped consent, revocation, audit trail — unique to us)
```

When user runs `/northstar --align [task]`:
1. Read NORTHSTAR.md
2. Does `[task]` advance: OAuth3 moat OR recipe hit rate?
3. Output: ALIGNED | DRIFT (with brief reason)
4. If DRIFT: suggest how to reframe to align

## Related Commands

- `/build [phase]` — Start a build session (northstar loaded automatically)
- `/status` — Check phase, rung, belt
- `/scout [area]` — Map codebase area
- `/recipe [platform] [action]` — Build a recipe
- `/primewiki [site]` — Create PM triplet
