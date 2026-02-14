# /remember - External Memory (DISTILL-Compressed)

Storage: `.claude/memory/context.md` | Auth: 65537
**Project:** Solace Browser | **Status:** Phase 7 Complete, Phase 8 Ready
**Key Memory:** 7 phases, 442+ tests, 100% determinism, 10x cost efficiency

## Usage
```
/remember                 # Display all memory
/remember [key]           # Get value
/remember [key] [value]   # Store (auto-distilled)
/remember --list          # List by section
/remember --clear [key]   # Delete
```

## AUTO-DISTILL RULE (MANDATORY)

When saving ANY information, apply DISTILL compression:
```
INPUT:  "My kids are Mylee, Tyson and Emilee"
OUTPUT: kids: Mylee, Tyson, Emilee

INPUT:  "I decided to use prime channels for indexing because..."
OUTPUT: rule_indexing: prime channels (2,3,5,7,11...)

INPUT:  "OOLONG benchmark is at 99.3% accuracy"
OUTPUT: oolong_accuracy: 99.3%
```

**Rules:**
- Key=value format (no prose)
- One line per fact
- Equations in terse form
- Lists as comma-separated
- No "I decided to...", just the decision
- No mermaid diagrams (visual cruft)

## Channel Assignment

| Pattern | Channel | Stability |
|---------|---------|-----------|
| user_*, kids, location, favorite_* | [2] Identity | Stillwater |
| project_*, goal_*, mission | [3] Goals | Stillwater |
| decision_*, insight_*, *_rule | [5] Decisions | LOCKED |
| current_*, phase_*, subsystem_* | [7] Context | Ripple |
| blocker_*, issue_* | [11] Blockers | Ripple |

## Format

```markdown
# MEMORY | Auth:65537 | Updated:DATE

## IDENTITY [2]
user: Boston, blue
kids: Mylee, Tyson, Emilee

## DECISIONS [5] LOCKED
rule_name: terse_value
equation: formula

## CONTEXT [7] RIPPLE
current_phase: value
```

## Auto-Save Triggers

Claude saves automatically when:
- User shares personal info -> [2]
- Design decision made -> [5] LOCKED
- Milestone completed -> [7]
- Blocker encountered -> [11]

## Integration

- Subsystem projects (pzip, pvideo) share IDENTITY section
- `/distill` reads context for compression decisions
- `/mine-primes` updates discovery counts
- All saves are DISTILL-compressed

## OOLONG Insight

```
LLM memory: Probabilistic -> Drift -> 85% recall
External:   Deterministic -> Exact -> 100% recall
Compression: 4.4x (prose -> key=value)
```

*"To compress is to understand."*
