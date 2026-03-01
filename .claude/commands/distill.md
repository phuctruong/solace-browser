# /distill - Documentation Knowledge Extraction

Apply the DISTILL recipe to compress documentation into Stillwater generators.

## Usage

```
/distill [directory]          # Distill a specific directory
/distill papers               # Distill papers/ in current project
/distill diagrams             # Distill src/diagrams/ or data/default/diagrams/
/distill all                  # Distill papers/ + diagrams/ together (full project pass)
```

## What It Does

1. **Inventory** - Scan all *.md files in target directory (excluding README.md, CLAUDE.md)
2. **Measure** - Calculate source sizes, file counts, concept counts
3. **Extract** - Create/update README.md (interface layer — structural skeleton)
4. **Compress** - Create/update CLAUDE.md (generator layer — axioms only)
5. **Verify** - Check RTC (all concepts traceable from source → README → CLAUDE.md)
6. **Report** - Show compression ratios and MDL status
7. **Learn** - Extract cross-project patterns and update memory

## Standard Project Scope

Every project has two distill targets:

| Target | Path (typical) | Content type |
|--------|---------------|--------------|
| Papers | `papers/` | Long-form architecture papers (prose + tables) |
| Diagrams | `src/diagrams/` or `data/default/diagrams/` | Mermaid state machines + architecture maps |

Run `/distill all` to process both in one pass.

## Target Ratios

| Layer | Compression | Role |
|-------|-------------|------|
| Sources → README | 5-15x | Remove pedagogy, keep structure + all tables |
| README → CLAUDE.md | 1.5-3x | Remove visuals, keep axioms + invariants |
| Total | 10-30x | Maximum lossless compression |

## Output Structure

```
[directory]/
├── CLAUDE.md     # Stillwater generator — axioms, invariants, forbidden states (smallest)
├── README.md     # Interface layer — diagrams, tables, concept index (medium)
└── *.md          # Source ripples — full content (largest)
```

## Instructions for Claude

### For papers/ directory:

1. List all *.md files (excluding README.md, CLAUDE.md, 00-index.md if it exists)
2. Calculate total size
3. Create/update README.md from sources:
   - Extract all ## headers → concept index
   - Keep all tables (verbatim)
   - Keep mermaid diagrams that show structure (not examples)
   - Remove: prose explanations, examples, rationale paragraphs
   - Keep: thesis sentences, axioms, forbidden states, invariant tables
4. Create/update CLAUDE.md from README:
   - DNA-23: Core equations (4-6 lines, one per major concept)
   - STORY-47: Axioms table (5-9 rows: concept | rule | why-it-exists)
   - GENOME-79: Operational rules (G1-G7, one per major forbidden state or invariant)
   - Laws: Full invariant table (what-never / what-always)
   - NO diagrams, NO prose, NO examples

### For src/diagrams/ or data/default/diagrams/ directory:

**Diagrams are different — Mermaid IS the content, not an example.**

1. List all *.md files (excluding README.md, CLAUDE.md)
2. Read the README.md index if it exists (use as starting skeleton)
3. Create/update README.md:
   - Keep the full diagram index (file → what it shows)
   - Keep ONE representative Mermaid block per major architectural concept
   - Remove: duplicate diagrams showing same concept differently
   - Keep: color coding legend (it's a specification, not decoration)
4. Create/update CLAUDE.md:
   - List all diagram files with one-line purpose
   - Extract: node types (CPU=green, LLM=blue, Cloud=purple, Gate=black)
   - Extract: forbidden paths (what the diagrams show CANNOT happen)
   - Extract: invariants (what the diagrams show MUST always be true)
   - One canonical Mermaid per subsystem (the most complete one)

### RTC Verification:

After writing README.md and CLAUDE.md:
- Confirm every paper title appears in README.md concept index
- Confirm every invariant in sources appears in CLAUDE.md Laws table
- Confirm every diagram file is named in CLAUDE.md
- Report: ✅ RTC passed | ❌ [missing concepts]

### Cross-Project Learning:

When distilling, note patterns that appear across multiple papers:
- Same concept in solace-cli AND stillwater AND solaceagi → elevate to UNIVERSAL LAW
- Patterns appearing only in one project → flag as project-specific
- Contradictions between projects → flag as UNRESOLVED (needs Phuc decision)

## Example Output

```
=== DISTILL: solaceagi/papers/ ===

Sources: 22 files, 168KB
README:  18KB (9.3x compression)
CLAUDE:  4.2KB (4.3x from README, 40x total)

=== DISTILL: solaceagi/src/diagrams/ ===

Sources: 17 files, 51KB
README:  existing (updated)
CLAUDE:  2.8KB (18x total)

RTC:     ✅ 22/22 papers indexed | 17/17 diagrams named
MDL:     ✅ Plateau reached
Cross:   3 universal laws identified (Prime Safety, Fallback Ban, Evidence-First)

Files updated:
- papers/README.md
- papers/CLAUDE.md
- src/diagrams/README.md
- src/diagrams/CLAUDE.md
```

## Ecosystem Projects (run /distill all in each)

| Project | Papers | Diagrams |
|---------|--------|----------|
| solaceagi | papers/ (22 files) | src/diagrams/ (17 files) |
| solace-cli | papers/ (14 files) | src/diagrams/ (12 files) |
| stillwater | papers/ (60 files) | data/default/diagrams/ |
| solace-browser | — | src/diagrams/ (8 files) |
| paudio | papers/ if any | src/diagrams/ if any |
| pvideo | papers/ if any | src/diagrams/ if any |

## Publishing to Network

After distilling, publish to the PM Network:

```
/distill-publish <path>       # Publish CLAUDE.md to network
/distill-verify <id>          # Verify artifact in network
/distill-list                 # List all network artifacts
```

## Related Commands

- `/compress` - Apply Stillwater compression to data files
- `/verify` - Run RTC verification on existing CLAUDE.md
- `/expand` - Generate README from CLAUDE.md
- `/distill all` - Full project pass (papers + diagrams)
