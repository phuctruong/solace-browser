# AGENT.md - Default Skill Boot Contract

Scope: `/home/phuc/projects/solace-browser`
Audience: Codex sessions working in this repository.

## 1) Default Loads (Always)

Load these by default at session start.

1. Stillwater core skills (requested path first):
   - Primary glob: `/home/phuc/projects/stillwater/data/default/skills/core/*.md`
   - Fallback glob: `/home/phuc/projects/stillwater/data/default/swarms/core/*.md`
2. Software5 command contract:
   - Primary path: `/home/phuc/projects/solace-cli/.claude/commands/software5`
   - Fallback path: `/home/phuc/projects/solace-cli/.claude/commands/software5.md`

Rules:
- Use every readable markdown file matched by the selected core-skills glob.
- Process core skill files in stable alphabetical order.
- If primary path does not exist, use fallback path and state that in the load receipt.
- If both primary and fallback are missing, fail closed and report exactly what is missing.

## 2) Boot Sequence

Run this sequence before implementation work.

1. Load Software5 command contract.
2. Load all core skills markdown files.
3. Emit a load receipt with:
   - Resolved paths used
   - File count loaded
   - File list loaded
   - Missing paths (if any)

No silent fallback. Do not claim a file was loaded unless it was read.

## 3) Required Before/After Scoring

For each session, report scoring before and after loading the contracts.

Scoring dimensions (0-100 each):
1. `math`
2. `coding`
3. `skills` (orchestration, safety gates, and workflow discipline)

Composite formula:
`composite = round(0.4 * coding + 0.4 * math + 0.2 * skills)`

Output format (required):

| Dimension | Before | After | Delta |
|---|---:|---:|---:|
| math | Bm | Am | Am-Bm |
| coding | Bc | Ac | Ac-Bc |
| skills | Bs | As | As-Bs |
| composite | Bx | Ax | Ax-Bx |

Constraints:
- `before` is baseline prior to loading these files.
- `after` is post-load expected operational quality under loaded contracts.
- Do not present benchmark claims as measured facts unless verified by tests.

## 4) Evidence and Integrity

When reporting scores, include a short basis line:
- Which files were loaded
- Whether fallbacks were used
- What checks were run (if any)

If loading fails, do not provide an `after` score. Report blocker details first.
