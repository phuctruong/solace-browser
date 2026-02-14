# /distill - Documentation Knowledge Extraction

Apply the DISTILL recipe to compress documentation into Stillwater generators.

## Usage

```
/distill [directory]
```

## What It Does

1. **Inventory** - Scan all *.md files in the target directory
2. **Measure** - Calculate source sizes and concept counts
3. **Extract** - Create/update README.md (interface layer)
4. **Compress** - Create/update CLAUDE.md (generator layer)
5. **Verify** - Check RTC (all concepts preserved)
6. **Report** - Show compression ratios and MDL status
7. **Publish** - Publish CLAUDE.md to PM Network (optional)

## Recipe Reference

See: `canon/prime-mermaid/recipes/DISTILL.md`

## Target Ratios

| Layer | Compression | Role |
|-------|-------------|------|
| Sources → README | 5-15x | Remove pedagogy, keep structure |
| README → CLAUDE.md | 1.5-3x | Remove visuals, keep axioms |
| Total | 10-30x | Maximum lossless compression |

## Output Structure

```
[directory]/
├── CLAUDE.md     # Stillwater generator (smallest, axioms)
├── README.md     # Interface layer (diagrams, tables)
└── *.md          # Source ripples (full content)
```

## Instructions for Claude

When user runs `/distill [dir]`:

1. List all *.md files in `[dir]` (excluding README.md and CLAUDE.md)
2. Calculate total size of source files
3. If README.md exists, read it; otherwise create from sources:
   - Extract all ## headers
   - Keep all tables
   - Keep key mermaid diagrams (structural only)
   - Remove prose/examples
4. If CLAUDE.md exists, read it; otherwise create from README:
   - DNA-23: Core equations (4-6 lines)
   - STORY-47: Axioms table (5-9 rows)
   - GENOME-79: Operational rules (G1-G7 sections)
   - Laws: Full invariant table
   - No diagrams, no prose
5. Verify RTC:
   - All README concepts traceable to sources
   - All CLAUDE.md concepts traceable to README
6. Report compression ratios

## Example

```
User: /distill docs/prime-mermaid-recipes/implementation

Claude:
=== DISTILL: implementation ===

Sources: 10 files, 63KB
README:  15KB (4.2x compression)
CLAUDE:  3.9KB (3.9x from README)

Total:   16.4x compression
RTC:     ✅ 100% verified
MDL:     ✅ Plateau reached

Files updated:
- implementation/CLAUDE.md

User: /distill-publish docs/prime-mermaid-recipes/implementation/CLAUDE.md

Claude:
=== PM Publish ===
ID:     stillwater-implementation-canon-v1.0
Hash:   abc123def456
Type:   knowledge
✓ Artifact published to network
```

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
