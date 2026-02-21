# /scout — Dispatch Scout Agent to Map Codebase Area

Dispatch a haiku scout agent to inventory a codebase area before building. Fast, cheap, no coding — just mapping.

## Usage

```
/scout [area]
/scout oauth3          # Map OAuth3-related files + existing server endpoints
/scout recipes         # Map all recipes: format, structure, coverage gaps
/scout primewiki       # Map PrimeWiki triplets: what exists, what's missing
/scout ui              # Map UI server routes + template structure
/scout server          # Map solace_browser_server.py endpoints + schemas
/scout tests           # Map test coverage: what's tested, what's missing
/scout --full          # Full codebase inventory
```

ARGUMENTS: $ARGUMENTS

## What Scout Does

Scout (haiku) is cheap, fast, and reads-only. It never writes code. It produces:
- `gap_report.json` — what exists vs. what's needed
- `file_inventory.json` — all files in the area with sizes + last-modified
- `blocker_list.json` — any dependencies that would block work

All scout output goes to `scratch/scout/[area]/` (gitignored).

## Instructions for Claude

When user runs `/scout [area]`:

### Step 1 — Load NORTHSTAR

Read `/home/phuc/projects/solace-browser/NORTHSTAR.md`

Display: "Scouting [area] to advance: OAuth3 moat + recipe hit rate → 70%"

### Step 2 — Build Scout Prompt

Load skill content from `/home/phuc/projects/stillwater/skills/prime-safety.md`

```
=== SCOUT DISPATCH ===
Role:        scout
Model:       haiku
Skill pack:  prime-safety (full content pasted inline)
Rung target: 641

NORTHSTAR (load first — MANDATORY):
[paste full NORTHSTAR.md content]

Before starting, state: "Which NORTHSTAR metric does this scout advance?"

Task (CNF Capsule):
  You are a Scout agent for solace-browser.
  Project path: /home/phuc/projects/solace-browser/
  Scout area: [area]

  Mapping instructions for [area]:

  IF area = "oauth3":
    Read: solace_browser_server.py (find /run-recipe endpoint, extract request/response schema)
    Read: oauth3/ directory (if exists — list all files)
    Read: recipes/*.recipe.json (pick 2 examples — show schema)
    Output: {
      "run_recipe_endpoint": {method, path, request_schema, response_schema},
      "oauth3_module_exists": true|false,
      "oauth3_files": [...],
      "token_storage_location": "...",
      "enforcement_points": [...]
    }

  IF area = "recipes":
    Read: recipes/ directory (all .recipe.json files)
    For each: extract {id, name, scope_required, steps_count, evidence_schema}
    Output: {
      "recipes": [...],
      "platforms_covered": [...],
      "missing_platforms": ["gmail", "substack", "twitter"],
      "oauth3_bounded": [which recipes already have scope requirements],
      "format_reference": "recipes/linkedin-discover-posts.recipe.json"
    }

  IF area = "primewiki":
    Read: primewiki/ directory (all subdirs and files)
    For each platform: list {platform, files_exist, sha256_exists, page_flow_exists}
    Output: {
      "platforms_mapped": [...],
      "platforms_missing": ["gmail", "substack", "twitter"],
      "format_reference": "primewiki/linkedin/linkedin-page-flow.prime-mermaid.md"
    }

  IF area = "server":
    Read: solace_browser_server.py (all endpoints)
    Extract: all routes, request schemas, response schemas
    Output: {
      "endpoints": [{method, path, request_schema, response_schema}],
      "missing_endpoints": [required by ROADMAP but not yet implemented]
    }

  IF area = "ui":
    Read: ui_server.py (all routes + templates)
    Output: {
      "routes": [...],
      "templates": [...],
      "missing_routes": [required by ROADMAP]
    }

  IF area = "tests":
    Read: tests/ directory (all test files)
    Output: {
      "test_files": [...],
      "coverage_summary": "what's tested",
      "untested_areas": [...]
    }

  IF area = "--full":
    Run all of the above. Combine into single full_inventory.json.

  Write output to: scratch/scout/[area]/[timestamp].json
  If scratch/ dir doesn't exist, note that it should be created (gitignored).

  Null handling: if file not found → emit NEED_INFO, not a guess.

  Stop rules:
  - EXIT_PASS: output JSON complete, northstar metric stated
  - EXIT_BLOCKED: fatal read error (list file path)
  - EXIT_NEED_INFO: directory structure unclear
```

### Step 3 — Display Scout Results

Show the JSON output in readable format:

```
=== SCOUT REPORT: [area] ===
Date: 2026-02-21
Area: [area]
NORTHSTAR metric: OAuth3 moat + recipe hit rate

[formatted key findings from gap_report.json]

Blockers found: [none | list]
Recommendation: [what to build first based on findings]

Saved to: scratch/scout/[area]/
Next: /build [recommended-phase]
```

## Scratch Dir Policy

All scout output goes to `scratch/` (gitignored). Never writes to project proper.

```
/home/phuc/projects/solace-browser/scratch/scout/
  oauth3/       ← oauth3 area scout outputs
  recipes/      ← recipe inventory
  primewiki/    ← PM triplet inventory
  server/       ← endpoint mapping
  ui/           ← UI route mapping
  tests/        ← test coverage map
```

## Forbidden States

- `SCOUT_WRITES_CODE` — scout never writes code, only reads and maps
- `NORTHSTAR_MISSING` — always state northstar metric before scouting
- `GUESSING_FILE_CONTENT` — if file not found, emit NEED_INFO not a guess

## Related Commands

- `/build [phase]` — Build using scout findings as input
- `/recipe [name]` — Create a recipe (after scouting recipes area)
- `/primewiki [site]` — Create PM triplet (after scouting primewiki area)
- `/northstar` — Load NORTHSTAR before scouting
