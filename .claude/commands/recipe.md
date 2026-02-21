# /recipe — Create or Update a Recipe

Dispatch a Coder agent to build a new recipe for a platform, or update an existing one.
All recipes are automatically OAuth3-bounded once Phase 1.5 ships.

## Usage

```
/recipe [platform] [action]
/recipe gmail read-inbox          # Build gmail-read-inbox.recipe.json
/recipe gmail send-email          # Build gmail-send-email.recipe.json
/recipe substack publish-post     # Build substack-publish-post.recipe.json
/recipe twitter post-tweet        # Build twitter-post-tweet.recipe.json
/recipe linkedin create-post      # Update/improve existing recipe
/recipe --list                    # List all recipes with coverage status
```

ARGUMENTS: $ARGUMENTS

## OAuth3 Requirement

Every recipe built after Phase 1.5 ships MUST include:
- `scope_required` field in recipe JSON
- Agency token enforcement (POST /run-recipe checks token)
- Evidence bundle with `agency_token` field

## Instructions for Claude

When user runs `/recipe [platform] [action]`:

### Step 1 — NORTHSTAR Check

Read `/home/phuc/projects/solace-browser/NORTHSTAR.md`
State: "This recipe advances: recipe hit rate → 70% → $5.75 COGS → economic moat"

### Step 2 — Scout First

Run Scout on the area to understand:
- Does the PM triplet (primewiki/[platform]/) exist?
- Does a reference recipe already exist?
- What scopes are needed?

If PM triplet missing: suggest `/primewiki [platform]` first, then build the recipe.

### Step 3 — Check OAuth3 Status

Read `oauth3/` directory (if it exists after Phase 1.5 ships).

If OAuth3 not yet implemented:
```
WARNING: OAuth3 module not yet built.
Recipe will be created without enforcement (stub mode).
After /build oauth3-core completes, re-run /recipe to add enforcement.
Continue? [y/n]
```

### Step 4 — Build Coder Dispatch

```
=== CODER DISPATCH: Recipe Builder ===
Role:        coder
Model:       sonnet
Skill pack:  prime-safety + prime-coder (full content from skills/)
Rung target: 641

NORTHSTAR (load first — MANDATORY):
[paste full NORTHSTAR.md content]

Task (CNF Capsule):
  You are a Coder agent building a recipe for solace-browser.
  Before starting: "This recipe advances recipe hit rate → 70% → economic moat"

  Platform: [platform]
  Action: [action]
  Recipe ID: [platform]-[action] (e.g., gmail-read-inbox)
  Recipe file: recipes/[platform]-[action].recipe.json

  Reference format: recipes/linkedin-discover-posts.recipe.json
  PM triplet: primewiki/[platform]/[platform]-page-flow.prime-mermaid.md
  OAuth3 scope: [scope from scopes.py — e.g., gmail.read_inbox]

  Read first:
    - recipes/linkedin-discover-posts.recipe.json (reference format)
    - primewiki/[platform]/ (selector map + bot detection notes)
    - oauth3/scopes.py (available scopes — if it exists)
    - solace_browser_server.py (how /run-recipe uses recipe JSON)

  Build the recipe:
  {
    "id": "[platform]-[action]",
    "version": "1.0.0",
    "scope_required": "[platform].[action_scope]",
    "description": "...",
    "steps": [
      {
        "action": "navigate|click|type|wait|extract",
        "selector": "...",
        "value": "...",
        "anti_detection": "bezier_mouse|char_by_char|inertia_scroll",
        "evidence": "screenshot|dom_snapshot"
      }
    ],
    "evidence_schema": {
      "output_fields": [...],
      "agency_token": {"token_id": "...", "scope_used": "...", "step_up_performed": false}
    },
    "acceptance_test": {
      "command": "curl -X POST http://localhost:9222/run-recipe ...",
      "expected": {"status": "pass", "evidence": {...}}
    }
  }

  MANDATORY:
  - Anti-detection rules from PM triplet (char-by-char typing, Bezier mouse)
  - Scope field must match a scope in oauth3/scopes.py
  - Evidence bundle must include agency_token stub
  - Write failing acceptance test FIRST (red gate)
  - Run test after recipe creation (green gate)

  All draft work to: scratch/recipes/[platform]-[action]/
  Final recipe moves to: recipes/[platform]-[action].recipe.json

  Stop rules:
  - EXIT_PASS: recipe passes acceptance test, evidence bundle correct, rung 641 met
  - EXIT_BLOCKED: PM triplet missing, OR scope not defined in scopes.py
  - EXIT_NEED_INFO: selector map ambiguous
```

### Step 5 — Display Results

After coder returns:

```
=== RECIPE BUILT: [platform]-[action] ===

Recipe: recipes/[platform]-[action].recipe.json
Scope: [scope_required]
Steps: [count]
Anti-detection: [measures applied]
Evidence: [fields in evidence schema]
Acceptance test: [PASS | FAIL]

OAuth3 status: [enforced | stub — run /build oauth3-core to activate enforcement]

Next: /update-case-study solace-browser [platform]-recipes 641
```

## When user runs `/recipe --list`

```
=== RECIPE COVERAGE ===

LinkedIn (Phase 1 — DONE):
  linkedin-discover-posts    ✅ rung 641
  linkedin-create-post       ✅ rung 641
  linkedin-react             ✅ rung 641
  linkedin-comment           ✅ rung 641
  linkedin-read-messages     ✅ rung 641
  linkedin-check-profile     ✅ rung 641

Gmail (Phase 2 — TODO):
  gmail-read-inbox           [ ] build with /recipe gmail read-inbox
  gmail-send-email           [ ] build with /recipe gmail send-email
  gmail-search-email         [ ] build with /recipe gmail search-email
  gmail-label-email          [ ] build with /recipe gmail label-email

Substack (Phase 2 — FIRST MOVER):
  substack-publish-post      [ ] build with /recipe substack publish-post
  substack-get-stats         [ ] build with /recipe substack get-stats
  substack-schedule-post     [ ] build with /recipe substack schedule-post

Twitter (Phase 2 — TODO):
  twitter-post-tweet         [ ] build with /recipe twitter post-tweet
  twitter-read-timeline      [ ] build with /recipe twitter read-timeline
  twitter-check-notifications [ ] build with /recipe twitter check-notifications

Prerequisite: /build oauth3-core must complete before any Phase 2 recipe
```

## Scratch Dir Policy

All draft work → `scratch/recipes/[platform]-[action]/` (gitignored)
Final recipe → `recipes/[platform]-[action].recipe.json` (only after PASS)

## Related Commands

- `/primewiki [site]` — Create PM triplet before building a recipe
- `/build oauth3-core` — Build OAuth3 enforcement (prerequisite for Phase 2 recipes)
- `/scout recipes` — Inventory all existing recipes and gaps
