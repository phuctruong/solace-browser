# SolaceBrowser — Platform Roadmap

**Authority**: 65537 | **Northstar**: 70% recipe hit rate → $5.75 COGS → economic moat
**Last Updated**: 2026-02-21
**Status**: Phase 1.5 (OAuth3 Foundation) COMPLETE (1,466 tests) → Phase 2 (Platform Recipes) IN PROGRESS

> *"Delegate only with consent. Never weaken. Be water."* — Software 5.0 + OAuth3

---

## Strategic Reframe: OAuth3 Changes Everything

Before OAuth3: SolaceBrowser = "browser automation with recipe system"
After OAuth3: SolaceBrowser = **"the reference implementation of consent-bound AI delegation"**

This distinction is enormous:

| Without OAuth3 | With OAuth3 |
|---------------|------------|
| Tool | Protocol standard |
| Single product | Platform others build on |
| Beats competitors | Sets the standard competitors must follow |
| Sells subscriptions | Licenses the spec + hosts reference impl |

**The win condition (from OAUTH3-WHITEPAPER.md § 15)**:
> "Rung-gated" becomes industry standard.
> Enterprises require lane typing.
> Delegated AI requires scoped agency tokens.
> Skill libraries are treated as capital assets.
> Model providers compete on price, not lock-in.

---

## Why This Roadmap Matters

**Recipe moat + OAuth3 governance = structurally uncopyable position.**

At 70% recipe hit rate:
- COGS: $5.75/user/month (70% gross margin)
- Without recipes: $12.75 COGS (33% margin — not fundable)

OAuth3 makes the recipe system **legally and architecturally defensible**:
- Every recipe execution is bounded by a scoped, revocable agency token
- Evidence bundles prove what the agent did (non-repudiation)
- Platform Respect Mode prevents abuse → platforms tolerate us → longevity

**Our 6 moats** (no competitor has all 6):
1. Recipe system (70% cache hit → 3x cheaper COGS)
2. PrimeWiki PM knowledge layer (domain-aware navigation)
3. Twin architecture (local + cloud)
4. Anti-detection (Bezier mouse, fingerprint sync)
5. Stillwater verification (evidence-per-task, not just screenshots)
6. **OAuth3 protocol** (scoped consent, revocation, audit trail — unique to us)

**Competitive landscape**:
| Competitor | Approach | OAuth3 gap |
|-----------|---------|-----------|
| OpenClaw | General browser agent | No consent model, no revocation, black box |
| Browser-Use | Playwright + LLM | No scoped delegation, no evidence |
| Bardeen | Chrome extension | No cloud, no agency tokens |
| Vercel agent-browser | DOM reduction | No consent, no revocation, no recipe reuse |
| **All of them** | — | None implement OAuth3 — we publish the spec |

---

## Current Status: Phase 1 (LinkedIn MVP)

**Target**: Rung 641 | **Recipes**: 6 LinkedIn MVP | **PM**: `primewiki/linkedin/`

**QA prompt** (paste into QA session):
```
Load specs/QA-CHECKLIST.md. Start ui_server.py (port 9223) and solace_browser_server.py (port 9222).
Verify: Home page, Activity View (/activity?site=linkedin), Kanban (/kanban), all 6 LinkedIn recipes.
Run: curl -X POST http://localhost:9222/run-recipe -d '{"recipe_id":"linkedin-discover-posts"}'
Sign off Rung 641 when all 6 recipes return {status, duration, evidence}.
```

---

## Phase 1.5 — OAuth3 Foundation — COMPLETE

**Status**: All 8 builds DONE. 1,466 total tests passing. OAuth3 foundation is the architecture all future recipes run on.

| Build | Description | Status | Tests |
|-------|-------------|--------|-------|
| BUILD 1 | OAuth3 Core Module | DONE | 154+61 tests |
| BUILD 2 | Consent UI | DONE | 58 tests |
| BUILD 3 | Step-Up Auth | DONE | 29 tests |
| BUILD 4 | HTML Snapshots (PZip) | DONE | 18 tests |
| BUILD 5 | Gmail Recipes | DONE | 308 tests |
| BUILD 6 | Substack Recipes | DONE | 334 tests |
| BUILD 7 | Twitter Recipes | DONE | 287 tests |
| BUILD 8 | Machine Access + Tunnel | DONE | 145 tests |
| Bonus | Audit Trail | DONE | 72 tests |
| **Total** | | | **1,466 tests** |

**Target**: Rung 641 (local correctness) — ACHIEVED

---

### BUILD PROMPT 1: OAuth3 Core Module

```
TASK: Build OAuth3 agency token system for solace-browser

Context: See OAUTH3-WHITEPAPER.md for full spec. OAuth3 extends OAuth to action delegation.
Every recipe execution must be bounded by a scoped, time-bound, revocable agency token.

Create module: src/oauth3/ (or wherever solace_browser_server.py imports from)

Files to create:
  oauth3/token.py — AgencyToken dataclass + validation
  oauth3/scopes.py — Scope registry (all supported action scopes)
  oauth3/enforcement.py — Middleware: check scope before recipe execution
  oauth3/revocation.py — Token revocation + session kill

AgencyToken schema (store as JSON in ~/.solace/tokens/):
{
  "token_id": "uuid4",
  "user_id": "string",
  "issued_at": "ISO8601",
  "expires_at": "ISO8601 (default: 30 days)",
  "scopes": ["linkedin.read_messages", "gmail.send_email"],
  "revoked": false,
  "revoked_at": null,
  "step_up_required_for": ["linkedin.delete_post", "gmail.delete_email"]
}

Scope registry (oauth3/scopes.py):
SCOPES = {
  "linkedin.read_messages": "Read your LinkedIn messages",
  "linkedin.create_post": "Create posts on your behalf",
  "linkedin.edit_post": "Edit your existing posts",
  "linkedin.delete_post": "Delete your posts (STEP-UP REQUIRED)",
  "linkedin.react": "React to posts on your behalf",
  "linkedin.comment": "Comment on posts on your behalf",
  "gmail.read_inbox": "Read your Gmail inbox",
  "gmail.send_email": "Send email on your behalf",
  "gmail.search": "Search your email",
  "gmail.label": "Apply labels to email",
  "hackernews.submit": "Submit stories to HackerNews",
  "hackernews.comment": "Comment on HackerNews",
  "reddit.create_post": "Post to subreddits on your behalf",
  "notion.read_page": "Read your Notion pages",
  "notion.write_page": "Write to your Notion pages",
}

API endpoints to add to solace_browser_server.py:
  POST /oauth3/token — issue token with requested scopes (returns token_id + token JSON)
  GET  /oauth3/token/{token_id} — get token status
  DELETE /oauth3/token/{token_id} — revoke token (immediate)
  GET  /oauth3/scopes — list all available scopes with descriptions

Enforcement in POST /run-recipe:
  1. Extract agency_token from request body or X-Agency-Token header
  2. Validate token: not expired, not revoked, has required scope for this recipe
  3. If scope missing: return HTTP 403 {error: "insufficient_scope", required: "linkedin.create_post", consent_url: "/consent?scopes=linkedin.create_post"}
  4. If step_up required: return HTTP 402 {error: "step_up_required", action: "linkedin.delete_post"}
  5. On success: add token_id to Stillwater evidence bundle

Evidence bundle addition:
  Every recipe run adds to evidence:
    "agency_token": {
      "token_id": "...",
      "scope_used": "linkedin.create_post",
      "step_up_performed": false,
      "token_expires_at": "..."
    }

Acceptance tests (Rung 641):
  - POST /oauth3/token with scopes=["linkedin.create_post"] → returns valid token JSON
  - POST /run-recipe without token → 403 with consent_url
  - POST /run-recipe with wrong scope → 403 with required scope
  - POST /run-recipe with valid token → runs recipe, evidence includes token_id
  - DELETE /oauth3/token/{id} → token marked revoked; subsequent recipe run → 401

Files to read first: solace_browser_server.py (understand existing run-recipe endpoint)
NORTHSTAR: OAUTH3-WHITEPAPER.md
Rung: 641
```

---

### BUILD PROMPT 2: OAuth3 Consent UI

```
TASK: Build OAuth3 consent page in ui_server.py (port 9223)

Context: When a recipe requires scopes the user hasn't granted, redirect to /consent.
The consent page is the trust anchor — it's where users grant explicit, auditable permission.

New route: GET /consent?scopes=linkedin.create_post,linkedin.comment&redirect=/kanban

Page layout (vanilla HTML/CSS, no build step, match existing ui_server.py style):
  Header: "SolaceBrowser is requesting permission"
  App name + icon: "SolaceBrowser (local)"
  Scope list: For each scope in query param:
    - Icon (read=eye, write=pencil, delete=trash with red)
    - Human-readable scope description from SCOPES dict
    - Risk level indicator (low/medium/high)
  Step-up warning: If any scope in step_up_required_for → show yellow banner "Some actions will require re-confirmation"
  Two buttons:
    - [Allow — Grant Permission] → POST /oauth3/token with scopes → redirect to redirect param
    - [Deny — Cancel] → redirect to / with error=access_denied

Route: POST /oauth3/consent
  Body: {scopes: [...], redirect: "/kanban"}
  Action: call POST http://localhost:9222/oauth3/token → get token_id
          Set cookie: solace_agency_token={token_id}; HttpOnly; SameSite=Strict
          Redirect to redirect param

Token display page: GET /settings/tokens
  List all tokens: token_id (truncated), scopes, issued_at, expires_at, revoke button
  [Revoke] button → DELETE http://localhost:9222/oauth3/token/{token_id}

Home page update (ui_server.py):
  Each platform tile (LinkedIn, Gmail, etc.) shows badge: "6 scopes granted" or "No permissions — click to grant"
  Click on tile with no token → redirect to /consent?scopes={platform_default_scopes}

Acceptance tests (Rung 641):
  - GET /consent?scopes=linkedin.create_post → page renders with scope description
  - POST /oauth3/consent with valid scopes → cookie set → redirect works
  - GET /settings/tokens → shows issued tokens with revoke button
  - Home page → LinkedIn tile shows scope badge

Rung: 641
```

---

### BUILD PROMPT 3: Step-Up Authorization

```
TASK: Implement OAuth3 step-up authorization for high-risk recipe actions

Context: OAUTH3-WHITEPAPER.md §5.2: "High-risk actions require re-consent: destructive, financial, identity-changing"
Step-up means: even if user has a valid token, destructive recipes require explicit re-confirmation.

High-risk recipe scopes (require step_up in token + UI confirmation):
  linkedin.delete_post — permanently removes your post
  gmail.delete_email — permanently deletes email
  reddit.delete_post — permanently removes post

Implementation in solace_browser_server.py POST /run-recipe:
  1. If recipe.scope is in step_up_required_for list:
     a. Return HTTP 402 {
          "error": "step_up_required",
          "action": "linkedin.delete_post",
          "description": "This action is permanent and cannot be undone.",
          "confirm_url": "/step-up?token_id={id}&action=linkedin.delete_post&recipe_id={id}"
        }
  2. POST /oauth3/step-up — user confirms in UI
     a. Records step_up_performed=true in evidence bundle
     b. Returns one-time step_up_nonce
  3. Retry POST /run-recipe with step_up_nonce → executes

UI route: GET /step-up?token_id=...&action=...&recipe_id=...
  Red warning banner: "Permanent Action — This cannot be undone"
  Description of what will be deleted
  [Confirm Delete] → POST /oauth3/step-up → POST /run-recipe
  [Cancel] → redirect back

Evidence bundle addition:
  "step_up": {
    "required": true,
    "performed": true,
    "performed_at": "ISO8601",
    "action": "linkedin.delete_post"
  }

Acceptance tests:
  - POST /run-recipe for delete recipe without step_up → 402 with confirm_url
  - GET /step-up page renders with warning
  - POST /oauth3/step-up → nonce issued
  - POST /run-recipe with nonce → executes, evidence shows step_up_performed=true
  - POST /run-recipe with expired nonce → 401

Rung: 641
```

---

### BUILD PROMPT 4: OAuth3 Spec Publication (stillwater)

```
TASK: Add OAuth3 to stillwater as a publishable spec document

Context: OAUTH3-WHITEPAPER.md is the whitepaper. We need a machine-readable spec + implementation guide.
This makes OAuth3 an open standard others can implement — not just our product feature.

In stillwater repo, create:

papers/oauth3-spec-v0.1.md — The formal spec (openapi-style but for agency delegation)
  Sections:
  1. Agency Token schema (JSON Schema)
  2. Scope naming convention ({platform}.{action_class})
  3. Token lifecycle: ISSUED → ACTIVE → EXPIRED | REVOKED
  4. Evidence-carrying execution requirements (what every compliant impl must produce)
  5. Step-up authorization protocol
  6. Revocation requirements (must be immediate; max 5s propagation)
  7. Platform Respect Mode requirements
  8. Compliance checklist (10 items from whitepaper §14)

skills/oauth3-enforcer.md — Skill for agents that execute under OAuth3
  Purpose: enforce OAuth3 compliance in any browser automation agent
  Core contract: No execution without valid agency token. No step-up bypass.
  FSM: INIT → TOKEN_CHECK → SCOPE_CHECK → STEP_UP_CHECK → EXECUTE → EVIDENCE_EMIT → DONE
  Forbidden states: EXECUTE_WITHOUT_TOKEN, SCOPE_BYPASS, STEP_UP_BYPASS, EVIDENCE_MISSING

Update stillwater/README.md:
  Add "OAuth3 Compliance" section explaining Stillwater verifies OAuth3-bound executions
  Every Stillwater evidence bundle certifies OAuth3 compliance (or flags violations)

Acceptance:
  - papers/oauth3-spec-v0.1.md exists and is spec-complete
  - skills/oauth3-enforcer.md exists with full FSM
  - README references OAuth3 as governance standard
  - Rung: 641 (complete spec, not yet implemented in external system)
```

---

## Phase 2 — Platform Recipes (on top of OAuth3 foundation) — IN PROGRESS

All Phase 2 recipes are automatically OAuth3-bounded. Phase 1.5 complete.

**IN PROGRESS**: Reddit recipes, Notion recipes, HackerNews recipes

### BUILD PROMPT 5 (PREREQUISITE): HTML Snapshot Capture with PZip

```
TASK: Add HTML snapshot capture to solace-browser recipe execution

Context:
- After each recipe step that navigates or modifies a page, capture a full page snapshot.
- PZip compression makes this economically viable: HTML pages from same domain share
  80%+ content (CSS, JS, layout). Cross-file compression: 100 LinkedIn pages → ~5 pages worth.
- This is the secret sauce no competitor offers: full pages, not screenshots. Actual HTML,
  not a raster image. Inspectable, searchable, replayable.
- PZip Python API at /home/phuc/projects/pzip/pzip/:
    pzip.pzip_compress(data: bytes) -> bytes
    pzip.pzip_decompress(data: bytes) -> bytes
    pzip.compress_collection(dir: str) -> bytes  ← cross-file magic

Files to create:
  src/snapshot.py — HTML snapshot capture module
  src/history.py  — Browsing session history (list of snapshots, in-order)

After each recipe step that calls navigate() or any action that modifies the page:
1. Capture full page HTML: document.documentElement.outerHTML (via Playwright page.content())
2. Capture computed CSS for visible elements (page.evaluate() → getComputedStyle on visible elements)
3. Capture form state: all input values, selected options, checked states
   (page.evaluate() → query all inputs/selects/checkboxes → {selector: value} dict)
4. Capture form changes: compare form_state before and after each recipe step
   (diff: before_state vs after_state → emit form_changes list)
5. Capture network requests: browser network log (XHR/fetch URLs + response sizes)
   (via page.on("response") listener registered before step execution)
6. Generate snapshot_id = sha256(url + timestamp + html_hash) — content-addressed
7. Package as snapshot JSON:
   {
     "snapshot_id": "sha256hex",
     "url": "https://...",
     "title": "Page Title",
     "timestamp": "ISO8601",
     "html": "<!DOCTYPE html>...",
     "form_state": {"input#email": "user@example.com"},
     "form_changes": [{"selector": "input#email", "before": "", "after": "user@example.com"}],
     "network_requests": [{"url": "...", "method": "GET", "response_size_bytes": 1234}],
     "viewport": {"width": 1920, "height": 1080},
     "scroll_position": {"x": 0, "y": 450},
     "recipe_step": {"step_index": 2, "action": "fill", "selector": "input#email"}
   }
8. Compress with PZip: compressed_blob = pzip.pzip_compress(json.dumps(snapshot).encode())
9. Store compressed blob: ~/.solace/history/{session_id}/{snapshot_id}.pzip
10. Add entry to session index: ~/.solace/history/{session_id}/index.jsonl
    (one JSON line per snapshot: {snapshot_id, url, title, timestamp, compressed_size_bytes})

Integration point in solace_browser_server.py:
- After each call to executor.execute_step() → call snapshot.capture(page, step_info) → append to session history
- POST /run-recipe response: include {session_id, snapshots_captured: N} in evidence bundle

History API endpoints (add to solace_browser_server.py):
  GET /history — list all sessions (from ~/.solace/history/ dirs)
    Response: [{session_id, task_id, recipe_id, started_at, snapshot_count}]
  GET /history/{session_id} — list snapshots in session
    Response: {session_id, snapshots: [{snapshot_id, url, title, timestamp, compressed_size_bytes}]}
  GET /history/{session_id}/{snapshot_id} — get full snapshot (decompress → return JSON)
    Response: full snapshot JSON with html field
  GET /history/{session_id}/{snapshot_id}/render — return raw HTML only (for iframe)
    Content-Type: text/html
    Content-Security-Policy: sandbox allow-same-origin (no script execution)

History UI (add to ui_server.py):
  GET /activity-history — browsing history Kanban view
    Columns: one per session (date + task name header)
    Cards: one per page visit (favicon, title, URL truncated, timestamp)
    Yellow badge: if form_changes is non-empty for this snapshot
    Click card → modal: sandboxed iframe showing rendered page + form diff panel
    Filter bar: by date / by site domain / by recipe / by action type
    Search: POST /history/search?q=... → full-text search in snapshot HTML + form values

Acceptance tests (Rung 641):
- Capture snapshot for a test page: HTML is non-empty, form_state captured correctly
- Form fill: before_state and after_state differ correctly → form_changes correct
- PZip compression ratio > 2:1 on captured HTML (use LinkedIn page or equivalent HTML file)
- PZip decompress → original HTML recovered byte-for-byte (round-trip test)
- snapshot_id is deterministic: same inputs → same sha256 (byte-identical test)
- GET /history/{session_id} returns correct snapshot list after 3 captures
- GET /history/{session_id}/{snapshot_id}/render returns valid HTML in < 200ms

Files to read first:
  - solace_browser_server.py (understand existing run-recipe + evidence bundle structure)
  - /home/phuc/projects/pzip/pzip/__init__.py or pzip.py (understand Python API)
  - recipes/linkedin-discover-posts.recipe.json (reference recipe format)

Rung: 641
Evidence: compression ratio measurement in evidence/tests.json
```

---

### BUILD PROMPT 7: Gmail Recipes (first platform after LinkedIn)

```
TASK: Build 4 Gmail recipes for solace-browser

Context:
- PM triplet: primewiki/gmail/gmail-page-flow.* and gmail-oauth2.*
- Bot detection: char-by-char typing (80-200ms/char) — see primewiki/gmail/gmail-bot-detection-bypass.primemermaid.md
- OAuth3 scopes required: gmail.read_inbox, gmail.send_email, gmail.search, gmail.label
- Each recipe must present agency_token to solace_browser_server.py

Recipes to build (in recipes/ as gmail-*.recipe.json):
  gmail-read-inbox.recipe.json
    Scope: gmail.read_inbox
    Steps: navigate mail.google.com → wait for div[role=main] → extract 10 most recent subjects+senders
    Output: {emails: [{subject, sender, date, is_read}]}

  gmail-send-email.recipe.json
    Scope: gmail.send_email
    Input: {to, subject, body}
    Steps: click compose → fill to (char-by-char) → fill subject → fill body → Ctrl+Enter
    Output: {sent: true, timestamp}

  gmail-search-email.recipe.json
    Scope: gmail.read_inbox
    Input: {query: "from:someone@example.com"}
    Steps: click search bar → type query (char-by-char) → press Enter → extract results
    Output: {results: [{subject, sender, date}]}

  gmail-label-email.recipe.json
    Scope: gmail.label
    Input: {email_id, label}
    Steps: open email → click label icon → select/create label
    Output: {labeled: true, label}

For each recipe, Stillwater evidence bundle must include:
  - agency_token.token_id
  - agency_token.scope_used
  - screenshots[] (before + after key actions)
  - selector_matches[] (which PM portals were used)

Files to read first:
  - primewiki/gmail/gmail-page-flow.prime-mermaid.md (selector map)
  - primewiki/gmail/gmail-oauth2.prime-mermaid.md (auth flow)
  - primewiki/gmail/gmail-bot-detection-bypass.primemermaid.md (CRITICAL)
  - recipes/linkedin-discover-posts.recipe.json (reference format)
  - solace_browser_server.py (run-recipe endpoint)

Acceptance (Rung 641):
  - All 4 recipes run via POST /run-recipe with valid gmail.* token
  - gmail-read-inbox returns ≥1 email object
  - gmail-send-email sends email (verify in Gmail UI)
  - Each run produces Stillwater evidence bundle with token_id
```

---

### BUILD PROMPT 8: Substack Recipes (first-mover opportunity)

```
TASK: Build Substack PM triplet + 3 recipes — FIRST MOVER IN THIS SPACE

Context:
- Market research confirms: "one of the most annoying things about Substack is the lack of automation available"
- No competitor has working Substack automation. We ship first = we own this vertical.
- OAuth3 scopes: substack.publish_post, substack.get_stats, substack.schedule_post

Phase 1: Scout Substack UI → create PM triplet
  Navigate substack.com/publish → explore editor, stats page, subscriber management
  Create: primewiki/substack/substack-page-flow.mmd (state machine)
  sha256sum → substack-page-flow.sha256
  Write: primewiki/substack/substack-page-flow.prime-mermaid.md (selector map)
  Add: oauth3/scopes.py entries for substack.*
  Add: primewiki/PRIMEWIKI_INDEX.md entry for Substack

Phase 2: Build recipes
  substack-publish-post.recipe.json
    Scope: substack.publish_post
    Input: {title, body_html, subtitle?}
    Steps: navigate /publish/posts/new → fill title → fill body → click Publish
    Output: {published: true, post_url}

  substack-get-stats.recipe.json
    Scope: substack.get_stats
    Steps: navigate /publish/stats → extract subscriber count, open rate, top posts
    Output: {subscribers, open_rate, top_posts[]}

  substack-schedule-post.recipe.json
    Scope: substack.schedule_post
    Input: {title, body_html, publish_at: ISO8601}
    Steps: create post → click Schedule → set date/time → confirm
    Output: {scheduled: true, publish_at}

Add scope to oauth3/scopes.py:
  "substack.publish_post": "Publish posts to your Substack newsletter",
  "substack.get_stats": "Read your Substack subscriber and engagement stats",
  "substack.schedule_post": "Schedule future posts on your Substack",

Acceptance (Rung 641):
  - PM triplet exists with valid SHA256
  - substack-publish-post runs and publishes a test post (can delete after)
  - substack-get-stats returns subscriber count
  - OAuth3 enforcement: recipe rejects call without valid substack.* token
```

---

### BUILD PROMPT 9: Twitter/X Recipes

```
TASK: Build Twitter/X PM triplet + 3 recipes

Context:
- OAuth3 scopes: twitter.post_tweet, twitter.read_timeline, twitter.check_notifications
- Anti-detection critical: Twitter has aggressive bot detection
  Use: Bezier mouse movement + inertia scroll + randomized typing delays (same as Gmail)
- Do NOT use Twitter API (requires paid access) — pure browser automation

Phase 1: Scout Twitter/X UI → create PM triplet
  Navigate twitter.com → identify: tweet composer, timeline, notification bell
  Create: primewiki/twitter/twitter-page-flow.mmd
  sha256sum → twitter-page-flow.sha256
  Write: primewiki/twitter/twitter-page-flow.prime-mermaid.md (selector map)
  Note: Twitter/X changes DOM frequently — document selector stability score

Phase 2: Build recipes
  twitter-post-tweet.recipe.json
    Scope: twitter.post_tweet
    Input: {text, media_url?}
    Steps: click tweet button → wait for composer → type text (char-by-char) → click Tweet
    Output: {posted: true, tweet_url}
    Anti-detection: Bezier mouse to tweet button, 50-150ms typing delay

  twitter-read-timeline.recipe.json
    Scope: twitter.read_timeline
    Steps: navigate home → scroll → extract top 20 tweets
    Output: {tweets: [{author, text, likes, retweets, timestamp}]}

  twitter-check-notifications.recipe.json
    Scope: twitter.check_notifications
    Steps: navigate /notifications → extract unread count + recent notifications
    Output: {unread_count, notifications: [{type, from, text}]}

Acceptance (Rung 641):
  - PM triplet with SHA256
  - All 3 recipes run with valid twitter.* token
  - twitter-post-tweet posts successfully (no CAPTCHA, no shadowban indicator)
  - Evidence bundle shows anti-detection measures applied (Bezier path logged)
```

---

## Phase 3 — Universal Portal (Month 2) — NEXT

**Goal**: Machine access dashboard + built-in tunnel server (ngrok-like, no external tools) + download page on solaceagi.com.

**5 Control Surfaces after this phase**: AI Agent API, CLI (`solace-cli browser run`), OAuth3 Web Dashboard, Native Tunnel, Download Installer.

**Strategic reframe**: Solace Browser is not just a web browser. It is the universal portal through which AI agents interact with ALL of a user's digital resources — web accounts, local files, terminal, system — all governed by OAuth3 consent + Part 11 audit trails.

**Why this deepens the moat**: No competitor has OAuth3-gated machine access. Browser-Use is Chrome only. Bardeen is extension only. OpenClaw has no machine layer. Solace Browser is the first AI agent portal with web + machine + cloud in a single, consent-governed application.

**5 Control Surfaces (after this phase):**
1. AI Agent (Claude Code + stillwater skills → local API)
2. CLI (`solace-cli browser run "task"`)
3. OAuth3 Web (solaceagi.com dashboard → remote control)
4. Native Tunnel (built-in reverse proxy, connect from anywhere)
5. Download (solaceagi.com/browser, cross-platform installers)

---

### BUILD PROMPT 11: Machine Access Layer

```
TASK: Build OAuth3-gated machine access layer for solace-browser

Context: Solace Browser transforms from web-only browser to universal AI agent portal.
The machine layer gives AI agents access to local files, terminal, and system — all gated
by the same OAuth3 consent + Part 11 evidence system as the web layer.

RISK LEVEL: HIGH — machine access is irreversible (files can be deleted, commands executed)
Rung target: 274177 (irreversible — not just local correctness)

Files to create:
  src/machine/scopes.py — 13 machine-specific OAuth3 scopes:
    MACHINE_SCOPES = {
      "machine.file.read":        "Read files and directories on your machine",
      "machine.file.write":       "Write and create files on your machine",
      "machine.file.delete":      "Delete files from your machine (STEP-UP REQUIRED)",
      "machine.file.list":        "List directory contents on your machine",
      "machine.terminal.read":    "View terminal output and command history",
      "machine.terminal.execute": "Execute terminal commands on your machine (STEP-UP REQUIRED)",
      "machine.terminal.allowlist": "Execute commands matching the configured allowlist",
      "machine.system.info":      "Read system information (CPU, memory, disk, OS)",
      "machine.system.env":       "Read environment variables (non-secret)",
      "machine.process.list":     "List running processes",
      "machine.process.kill":     "Kill processes by PID (STEP-UP REQUIRED)",
      "machine.tunnel":           "Open reverse tunnel to solaceagi.com (STEP-UP REQUIRED)",
      "machine.clipboard":        "Read and write clipboard contents",
    }
    MACHINE_STEP_UP_REQUIRED = [
      "machine.file.delete", "machine.terminal.execute",
      "machine.process.kill", "machine.tunnel"
    ]

  src/machine/file_browser.py — OAuth3-gated file system access:
    - list_directory(path, token): requires machine.file.list scope
    - read_file(path, token): requires machine.file.read scope
    - write_file(path, content, token): requires machine.file.write scope
    - delete_file(path, token): requires machine.file.delete + step-up confirmation
    - Security: path traversal prevention (deny paths outside allowed_roots)
    - allowed_roots configurable in ~/.solace/machine-config.json
    - Default allowed_roots: ["~/Documents", "~/Desktop", "~/Downloads", "~/.solace"]

  src/machine/terminal.py — OAuth3-gated command execution:
    - execute_command(cmd, token): requires machine.terminal.execute + step-up
    - execute_allowlisted(cmd, token): requires machine.terminal.allowlist
    - Allowlist stored in ~/.solace/terminal-allowlist.json (user-managed)
    - Blocklist (hard-coded, never overridable):
        BLOCKED_COMMANDS = ["rm -rf /", "mkfs", "dd if=", "fork bomb", "> /dev/"]
    - Output capture: stdout + stderr + exit_code + duration_ms
    - Timeout: 30 seconds max per command
    - Evidence: every execution emits OAuth3-bound evidence bundle

  src/machine/api.py — FastAPI router for machine endpoints:
    POST /machine/file/list    — list directory (machine.file.list scope)
    POST /machine/file/read    — read file contents (machine.file.read scope)
    POST /machine/file/write   — write file (machine.file.write scope)
    DELETE /machine/file       — delete file (machine.file.delete + step-up)
    GET  /machine/system/info  — system info (machine.system.info scope)
    POST /machine/terminal/run — execute command (machine.terminal.execute + step-up)
    GET  /machine/scopes       — list all machine scopes

Security requirements (non-negotiable):
  - ALL machine operations require valid OAuth3 agency token
  - Path traversal: ANY request containing ".." or absolute path → 403 immediately
  - Step-up for destructive: file.delete + terminal.execute → require confirmed step-up nonce
  - Blocklist: checked BEFORE any token validation (fail-closed)
  - Evidence bundle: every machine operation logs to ~/.solace/evidence/{task_id}/

Acceptance tests (Rung 274177):
  - 100+ tests covering scope enforcement, path traversal attack vectors, command blocklist
  - Path traversal: ../../../etc/passwd → 403 for all read/write/delete endpoints
  - Blocklist: "rm -rf /" blocked with no token check
  - Valid token + correct scope → operation succeeds, evidence bundle emitted
  - Step-up required for delete + execute (without nonce → 402)
  - Step-up confirmed + nonce → operation executes, evidence shows step_up_performed=true
  - Null/missing scope → 403 with scope name in error body
  - allowed_roots enforced: path outside roots → 403 even with valid token

Rung: 274177
```

---

### BUILD PROMPT 12: Tunnel Engine

```
TASK: Build reverse tunnel engine for solace-browser → tunnel.solaceagi.com

Context: The tunnel enables remote control of the local Solace Browser from anywhere.
This is the "built-in ngrok" — no external tools, no configuration, one click to connect.

RISK LEVEL: CRITICAL — tunnel opens local machine to internet
Rung target: 65537 (security-critical — this is the highest risk surface in the system)

Files to create:
  src/machine/tunnel.py — Reverse tunnel implementation:
    - WebSocket-based persistent connection to tunnel.solaceagi.com
    - OAuth3 scope: machine.tunnel (step-up required before tunnel opens)
    - Tunnel lifecycle:
        INIT → STEP_UP_CHECK → OAUTH3_GATE → CONNECT → ACTIVE → HEARTBEAT_LOOP → DISCONNECT
    - TunnelSession dataclass:
        {tunnel_id, user_id, token_id, started_at, bytes_in, bytes_out,
         connected: bool, last_heartbeat: ISO8601}
    - Auto-reconnect: exponential backoff (1s, 2s, 4s, 8s, max 60s)
    - Heartbeat: ping every 30s, disconnect if no pong within 10s
    - Bandwidth tracking: bytes_in + bytes_out per session, logged to evidence bundle
    - Hard limits: max 100MB/session (free tier), configurable per belt tier
    - Graceful shutdown: close WebSocket cleanly, emit disconnect evidence bundle

  Tunnel endpoint mapping:
    - tunnel.solaceagi.com assigns unique subdomain: {user_id}.tunnel.solaceagi.com
    - All HTTP requests to subdomain → WebSocket relay → local Solace Browser API
    - OAuth3 token required on every proxied request (server-side validation)

  Evidence per tunnel session:
    {
      "tunnel_id": "uuid4",
      "user_id": "...",
      "token_id": "...",
      "scope": "machine.tunnel",
      "step_up_performed": true,
      "started_at": "ISO8601",
      "ended_at": "ISO8601",
      "bytes_in": 1234,
      "bytes_out": 5678,
      "requests_proxied": 42,
      "disconnect_reason": "user_initiated | timeout | server_closed | error"
    }

Security requirements (non-negotiable):
  - ZERO tunnel traffic without valid OAuth3 token on every proxied request
  - TLS required on WebSocket connection (wss:// only, reject ws://)
  - Tunnel token pinned to user_id — cross-user relay impossible
  - Bandwidth limits enforced in real-time (not post-hoc)
  - Tunnel closes immediately on token revocation (revocation propagation < 5s)
  - Security scan required before merge: semgrep + bandit on tunnel.py

Acceptance tests (Rung 65537):
  - WebSocket handshake with valid OAuth3 machine.tunnel token → connected
  - WebSocket handshake without token → connection refused
  - Token revoked mid-session → tunnel closes within 5s
  - Bandwidth limit exceeded → graceful disconnect, no further relay
  - Auto-reconnect after simulated disconnect → reconnects within 2s
  - Heartbeat timeout simulation → disconnect after 10s no-pong
  - Evidence bundle emitted on clean disconnect AND on error disconnect

Rung: 65537
```

---

### BUILD PROMPT 13: Browser Home Page + Machine Dashboard

```
TASK: Build browser home page and machine control dashboard for solace-browser

Context: The home page becomes a command center for the universal portal.
Users see: web automation status + machine access + tunnel connection + quick actions.

Files to create:
  web/home.html — Universal portal start page (replaces current home page):
    Sections:
      1. Quick Actions panel: [Run Recipe] [Browse Files] [Open Terminal] [Connect Tunnel]
         Each action checks OAuth3 token before proceeding (redirect to /consent if missing)
      2. Recipe Library grid: most-used recipes with last-run status + hit rate badge
      3. Machine Status panel: disk usage, running processes count, tunnel status
      4. Activity Feed: last 10 recipe runs + machine access logs (real-time, SSE)
    Tech: vanilla HTML/CSS/JS, no build step, served by existing ui_server.py

  web/machine-dashboard.html — Machine control center:
    Three panels:
      File Browser panel:
        - Left: directory tree (allowed_roots from machine-config.json)
        - Right: file listing with actions (read, write, download, delete with step-up confirm)
        - Breadcrumb navigation
        - File content viewer (code highlighting for .py, .json, .md, .yaml)
        - Upload: drag-and-drop to write files (requires machine.file.write token)
        - All operations call /machine/file/* endpoints with OAuth3 token in header

      Terminal panel:
        - Command input with allowlist indicator (shows if command matches allowlist)
        - Output display: stdout (white) + stderr (red) + exit code badge
        - Step-up confirmation modal for execute (non-allowlisted) commands
        - Command history (last 50 commands, sessionStorage)
        - System info sidebar: CPU %, memory %, disk %, uptime

      Active Sessions panel:
        - List of current OAuth3 machine tokens (scope, issued_at, expires_at)
        - Revoke button per token
        - Tunnel status: connected/disconnected, bytes_in/out, [Disconnect] button

  web/tunnel-connect.html — Tunnel connection management:
    - Current status: DISCONNECTED / CONNECTING / ACTIVE + tunnel URL
    - [Connect Tunnel] button → requests machine.tunnel step-up → opens WebSocket
    - Connected state shows: tunnel URL, bytes transferred, duration, request count
    - [Copy Tunnel URL] button (copies {user_id}.tunnel.solaceagi.com to clipboard)
    - [Disconnect] button → graceful tunnel shutdown
    - Connection log: last 10 tunnel events (ISO8601 + event type)

Acceptance tests (Rung 641):
  - web/home.html renders all 4 sections without JS errors
  - Quick Actions: each button triggers OAuth3 token check before action
  - Machine dashboard: File Browser lists allowed_roots directories
  - Terminal panel: allowlisted command executes without step-up; other commands show modal
  - Tunnel connect: [Connect Tunnel] triggers step-up flow, then WebSocket connection
  - All endpoints called with OAuth3 token in Authorization header

Rung: 641
```

---

### BUILD PROMPT 14: Cross-Platform Distribution

```
TASK: Package Solace Browser as cross-platform desktop application

Context: Solace Browser must ship as a native desktop app — not a Python script users must
configure themselves. One download, one install, runs everywhere. This is the distribution
layer that puts the universal portal in users' hands.

Architecture:
  Option A (Tauri): Rust shell + webview, smaller binary, better perf
  Option B (Electron): Node + Chromium, larger but more battle-tested
  Decision: Tauri (smaller install footprint, no bundled Chromium overhead)

  Bundled components:
    - Tauri shell (Rust) wraps existing web UI (web/home.html + machine-dashboard.html)
    - Embedded Python runtime (pyinstaller bundled) for solace_browser_server.py + machine API
    - Playwright browsers installed to ~/Library/Application Support/SolaceBrowser/
    - Configuration wizard on first launch (allowed_roots, allowlist setup)

Files to create:
  src-tauri/
  ├── tauri.conf.json      — Tauri app configuration (name, version, icons, bundle ids)
  ├── src/main.rs          — Rust entry point + Python subprocess manager
  └── icons/               — App icons (DMG, DEB, MSI)

  scripts/
  ├── build-mac.sh         — Build DMG for macOS (arm64 + x86_64 universal)
  ├── build-linux.sh       — Build .deb + .rpm for Debian/Ubuntu + RHEL/Fedora
  └── build-windows.sh     — Build .msi installer for Windows 10/11

  installer/
  └── welcome.html         — First-launch wizard: allowed_roots + allowlist config

Download page (solaceagi.com/browser):
  - Platform auto-detection (macOS/Linux/Windows)
  - Primary download button + secondary platform links
  - Changelog, SHA256 checksums
  - Installation instructions per platform

Auto-update mechanism:
  - Check https://solaceagi.com/api/browser/latest on startup
  - Compare version strings, show banner if update available
  - [Update Now] → download + verify SHA256 → replace binary → restart

Acceptance tests (Rung 641):
  - macOS: app launches, all API servers start, home.html renders
  - Linux: .deb installs, app runs headless on Ubuntu 22.04
  - Windows: .msi installs, app runs on Windows 11
  - Auto-update: version check returns new version → banner shown
  - SHA256 of distributed binary matches solaceagi.com/api/browser/latest checksum

Rung: 641
```

---

## Phase 4 — solaceagi.com (Cloud Layer)

**When**: After Phase 3 (Universal Portal validated, machine layer stable)
**What**: Hosted Stillwater + cloud browser execution, OAuth3-governed

```
BUILD PROMPT 10: solaceagi.com MVP API (renumbered from original Phase 3)

TASK: Build FastAPI service for solaceagi.com — cloud recipe execution

Architecture:
  Belt-gated access:
    White Belt ($0): BYOK — user provides own API key, zero LLM cost to us
    Yellow Belt ($8/mo): Managed LLM (Together.ai/OpenRouter, 20% margin, ~8K tasks/mo)
    Orange Belt ($48/mo): Cloud twin (24/7) + managed LLM included + OAuth3 vault
  Cloud executes recipes using user's own API key or managed LLM (by tier)
  Stillwater evidence bundle returned per task

Endpoints:
  POST /tasks — submit recipe task
    Body: {recipe_id, input_params, agency_token, anthropic_api_key_encrypted}
    Returns: {task_id, status: "queued"}

  GET /tasks/{task_id} — poll task status
    Returns: {task_id, status: "running|done|failed", started_at, completed_at}

  GET /tasks/{task_id}/evidence — get Stillwater bundle
    Returns: Stillwater evidence bundle (same schema as local execution)

  POST /oauth3/cloud-token — issue cloud-scoped agency token
    Body: {scopes, expires_hours: 720}
    Returns: {token_id, ...AgencyToken}

  DELETE /oauth3/cloud-token/{token_id} — revoke cloud token (kills running tasks)

Session vault (AES-256-GCM, zero-knowledge):
  POST /vault/session — store encrypted browser session
    Body: {site, encrypted_session_blob}
    Encryption: AES-256-GCM with user's master password (never stored server-side)

  GET /vault/session/{site} — retrieve encrypted session for cloud execution
    Returns: {encrypted_session_blob} — agent decrypts with master password

Infrastructure: FastAPI + Playwright in Docker + Redis task queue + Postgres (task log)

Acceptance (Rung 641):
  - POST /tasks → task queued → GET /tasks/{id} shows running → done
  - GET /tasks/{id}/evidence returns valid Stillwater bundle
  - POST /oauth3/cloud-token → DELETE → subsequent POST /tasks with that token → 401
  - Session vault: store → retrieve → decrypt round trip works
```

---

## The Win Condition (from OAUTH3-WHITEPAPER.md §15)

We ship this sequence:
1. DONE — Phase 1: LinkedIn recipes (6 recipes, rung 641)
2. DONE — Phase 1.5: OAuth3 foundation (1,466 tests: OAuth3 core, consent UI, step-up auth, HTML snapshots, Gmail, Substack, Twitter, machine access, audit trail)
3. IN PROGRESS — Phase 2: Reddit + Notion + HackerNews (additional platform recipes)
4. NEXT — Phase 3: Universal Portal (machine access dashboard + tunnel server + download page on solaceagi.com)
5. PLANNED — Phase 4: solaceagi.com (cloud execution + tunnel server)

We publish:
- OAuth3 spec on solaceagi.com/spec (open standard — others implement it)
- Cost model paper (tokens saved = capital accumulated)
- One-command demo: `curl -X POST solaceagi.com/demo/linkedin-read-messages`

We win when:
- OpenClaw, Browser-Use are forced to implement OAuth3 (we set the standard)
- Enterprises adopt rung-gated execution as compliance requirement
- Skill libraries are treated as capital assets (not just code)

---

## Belt System

> "Don't get set into one form, adapt it and build your own." — Bruce Lee

| Belt | Tier | Price | XP | Milestone |
|------|------|-------|-----|-----------|
| White | Free | $0 | 0 | LinkedIn Phase 1 — **DONE** |
| Yellow | Student | $8/mo | 100 | OAuth3 foundation ships — **DONE** (1,466 tests) |
| Orange | Warrior | $48/mo | 300 | 70% recipe hit rate + OAuth3 spec published + cloud twin live |
| Green | Master | $88/mo | 750 | 10 platforms, all OAuth3-bounded + team tokens |
| Black | Grandmaster | $188+/mo | 10,000 | OAuth3 is the standard. Models are commodities. Skills are capital. |

**XP sources (community flywheel):**
- Recipe submitted to Stillwater Store: +50 XP
- Recipe accepted at rung 641: +100 XP
- Recipe accepted at rung 65537: +300 XP
- PrimeWiki PM triplet submitted: +75 XP
- Swarm agent definition contributed: +100 XP
- Security audit contribution: +200 XP

"This isn't SaaS — it's a dojo. Every skill you contribute makes the platform better for everyone."

**Auth**: 65537 | **OAUTH3-WHITEPAPER.md is the constitution**
