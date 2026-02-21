# /primewiki — Create PrimeWiki PM Triplet for a Site

Dispatch a haiku scout + sonnet coder to create a PrimeWiki Platform Model (PM) triplet for a new website. PM triplets are the domain knowledge layer that makes recipes reliable.

## Usage

```
/primewiki [site]
/primewiki gmail         # Create Gmail PM triplet
/primewiki substack      # Create Substack PM triplet (FIRST MOVER)
/primewiki twitter       # Create Twitter/X PM triplet
/primewiki hackernews    # Create HackerNews PM triplet
/primewiki reddit        # Create Reddit PM triplet
/primewiki notion        # Create Notion PM triplet
/primewiki --list        # List all PM triplets + coverage status
```

ARGUMENTS: $ARGUMENTS

## What is a PM Triplet?

A PM triplet consists of 3 files:

```
primewiki/[site]/
  [site]-page-flow.mmd                  ← Mermaid state machine of site navigation
  [site]-page-flow.sha256               ← SHA256 fingerprint of the diagram
  [site]-page-flow.prime-mermaid.md     ← Annotated selector map (what agents use)
```

The `.prime-mermaid.md` file is the critical artifact — it maps:
- Site navigation states
- CSS/ARIA selectors for key elements
- Bot detection bypass notes
- OAuth2 auth flow (if applicable)
- Stability scores for selectors

## Instructions for Claude

When user runs `/primewiki [site]`:

### Step 1 — NORTHSTAR Check

Read `/home/phuc/projects/solace-browser/NORTHSTAR.md`
State: "This PM triplet advances: recipe hit rate → 70% → economic moat (better selectors → fewer failures)"

### Step 2 — Check Existing Triplet

Check if `primewiki/[site]/` already exists.
If yes: show what exists and ask "Update existing triplet or create new version?"

### Step 3 — Scout Dispatch (haiku)

```
=== SCOUT DISPATCH: PrimeWiki ===
Role:        scout (haiku)
Model:       haiku
Skill pack:  prime-safety (full content pasted inline)
Rung target: 641

NORTHSTAR (load first — MANDATORY):
[paste full NORTHSTAR.md]

Task (CNF Capsule):
  You are a Scout agent creating a PrimeWiki PM triplet for [site].
  Before starting: "This work advances recipe hit rate → economic moat."

  Reference format: primewiki/linkedin/linkedin-page-flow.prime-mermaid.md

  Navigate to [site] (if browser available) OR use knowledge of [site] UI:

  1. Map the key pages and navigation flows:
     - Login/auth page → main page → key action pages
     - For each page: list 3-5 critical UI elements with selectors

  2. Identify bot detection patterns:
     - Login: CAPTCHA? email 2FA? SMS? IP rate limiting?
     - Posting/action: typing speed detection? mouse movement detection?
     - Scrolling: pattern detection? JS injection detection?

  3. Extract key selectors (CSS + ARIA + data-*):
     - Primary selector (most stable)
     - Fallback selector (structural)
     - XPath (last resort)

  4. Map OAuth2 flow (if site uses OAuth2 for third-party):
     - Authorization URL pattern
     - Redirect URI handling
     - Token storage location

  Output files to: scratch/primewiki/[site]/
    - [site]-page-flow-draft.mmd (Mermaid state machine)
    - [site]-selectors.json (all selectors with stability scores)
    - [site]-bot-detection.md (bypass strategies)

  Stop rules:
  - EXIT_PASS: all files created with reasonable completeness
  - EXIT_BLOCKED: site structure cannot be determined
  - EXIT_NEED_INFO: need to navigate live site (cannot determine from static knowledge)
```

### Step 4 — Graph Designer Dispatch (haiku)

After Scout returns selectors, dispatch Graph Designer to formalize the Mermaid diagram:

```
=== GRAPH DESIGNER DISPATCH ===
Role:        graph-designer
Model:       haiku
Skill pack:  prime-safety + prime-mermaid (full content from skills/)
Rung target: 641

Task (CNF Capsule):
  You are a Graph Designer creating a PrimeWiki Mermaid state machine for [site].

  Scout output: [paste [site]-selectors.json and [site]-page-flow-draft.mmd]

  Create a Mermaid state diagram:
  - States = key pages (Login, Home, Compose, Post, Profile, Settings)
  - Transitions = user actions (click, navigate, submit)
  - Annotations = selectors for key elements at each state
  - Include: bot_detection_note at relevant states

  Format: match primewiki/linkedin/linkedin-page-flow.mmd exactly

  Output to: scratch/primewiki/[site]/[site]-page-flow.mmd

  Stop rules:
  - EXIT_PASS: valid Mermaid syntax, all key states covered, selectors annotated
  - EXIT_BLOCKED: too many unknown states to create a coherent diagram
```

### Step 5 — Compile Final Triplet

After Graph Designer returns:

1. Create the SHA256 of the .mmd file:
   - Note for agent: run `sha256sum [site]-page-flow.mmd` to get hash
   - Store as `[site]-page-flow.sha256`

2. Create the `.prime-mermaid.md` file combining:
   - The Mermaid diagram
   - Annotated selector map (from selectors.json)
   - Bot detection bypass notes
   - OAuth2 flow (if applicable)

3. Move all files from `scratch/primewiki/[site]/` to `primewiki/[site]/`

4. Update `primewiki/PRIMEWIKI_INDEX.md` with new entry

### Step 6 — Display Results

```
=== PRIMEWIKI TRIPLET CREATED: [site] ===

Files:
  primewiki/[site]/[site]-page-flow.mmd          ✅
  primewiki/[site]/[site]-page-flow.sha256        ✅
  primewiki/[site]/[site]-page-flow.prime-mermaid.md ✅

States mapped: [count]
Selectors extracted: [count]
Bot detection: [strategies documented]
OAuth2 flow: [yes | no | n/a]

PRIMEWIKI_INDEX.md: updated

Next: /recipe [site] [first-action] to build the first recipe
```

## When user runs `/primewiki --list`

```
=== PRIMEWIKI COVERAGE ===

Platform         | PM Triplet | SHA256 | Recipes | Status
-----------------|------------|--------|---------|-------
LinkedIn         | ✅         | ✅     | 6       | COMPLETE
Gmail            | [ ]        | [ ]    | 0       | → /primewiki gmail
Substack         | [ ]        | [ ]    | 0       | → /primewiki substack (FIRST MOVER)
Twitter/X        | [ ]        | [ ]    | 0       | → /primewiki twitter
HackerNews       | [ ]        | [ ]    | 0       | → /primewiki hackernews
Reddit           | [ ]        | [ ]    | 0       | → /primewiki reddit
Notion           | [ ]        | [ ]    | 0       | → /primewiki notion

Prerequisite for Phase 2 recipes: PM triplet must exist before recipe build.
```

## Scratch Dir Policy

All draft files → `scratch/primewiki/[site]/` (gitignored)
Final triplet → `primewiki/[site]/` (only after PASS)
SHA256 verified before move.

## Related Commands

- `/recipe [site] [action]` — Build a recipe using this PM triplet
- `/scout primewiki` — Inventory all existing PM triplets
- `/build substack-recipes` — Full Substack recipe build (includes PM triplet creation)
