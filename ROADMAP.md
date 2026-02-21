# SolaceBrowser — Platform Roadmap

**Authority**: 65537 | **Northstar**: 70% recipe hit rate → $5.75 COGS → economic moat
**Last Updated**: 2026-02-21
**Status**: Phase 1 (LinkedIn MVP) complete → Phase 1.5 (OAuth3 Foundation) next

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

## Phase 1.5 — OAuth3 Foundation (BUILD THIS NEXT)

**Why first**: OAuth3 is the architecture all future recipes run on. Build it once, correctly, before adding more platforms. Every new recipe added after this is automatically consent-bound.

**Target**: Rung 641 (local correctness) → ship before any new platform recipes

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

## Phase 2 — Platform Recipes (on top of OAuth3 foundation)

All Phase 2 recipes are automatically OAuth3-bounded once Phase 1.5 ships.

### BUILD PROMPT 5: Gmail Recipes (first platform after LinkedIn)

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

### BUILD PROMPT 6: Substack Recipes (first-mover opportunity)

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

### BUILD PROMPT 7: Twitter/X Recipes

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

## Phase 3 — solaceagi.com (Cloud Layer)

**When**: After Phase 2 (Gmail + Substack + Twitter validated)
**What**: Hosted Stillwater + cloud browser execution, OAuth3-governed

```
BUILD PROMPT 8: solaceagi.com MVP API

TASK: Build FastAPI service for solaceagi.com — cloud recipe execution

Architecture:
  User enters Anthropic API key + grants OAuth3 agency tokens (cloud scope)
  Cloud executes recipes using user's own API key (zero LLM costs to us)
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
1. ✅ Phase 1: LinkedIn recipes (DONE)
2. 🔨 Phase 1.5: OAuth3 foundation (BUILD NEXT)
3. 🔨 Phase 2: Gmail + Substack + Twitter (first-mover platforms)
4. 🔨 Phase 3: solaceagi.com (cloud execution)

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

| Belt | XP | Milestone |
|------|----|-----------|
| ⬜ White | 0 | LinkedIn Phase 1 — **DONE** |
| 🟡 Yellow | 100 | OAuth3 foundation ships — **BUILD NEXT** |
| 🟠 Orange | 300 | 70% recipe hit rate + OAuth3 spec published |
| 🟢 Green | 750 | 10 platforms, all OAuth3-bounded |
| 🔵 Blue | 1,500 | solaceagi.com live — cloud execution under OAuth3 |
| 🟤 Brown | 3,000 | 80% hit rate + "rung-gated" entering industry lexicon |
| ⬛ Black | 10,000 | OAuth3 is the standard. Models are commodities. Skills are capital. |

**Auth**: 65537 | **OAUTH3-WHITEPAPER.md is the constitution**
