# Solace Browser — Build Spec (MVP UI + LinkedIn Recipes)

**Version:** 1.0.0
**Status:** READY TO BUILD
**Rung Target:** 641 (local correctness)
**Authored by:** Phuc Truong + Claude Sonnet 4.6
**QA/Auditor:** Claude Sonnet 4.6 (separate session)

> Absorb what is useful, discard what is useless, add what is essentially your own. — Bruce Lee

---

## Overview

Four features to build for the Solace Browser MVP:

| # | Feature | Route | Priority |
|---|---|---|---|
| 1 | Custom Home Page | `GET /` | P0 |
| 2 | Activity View (twin orchestrator) | `GET /activity?site=linkedin` | P0 |
| 3 | Kanban Recipe UI | `GET /kanban` | P0 |
| 4 | LinkedIn MVP Recipes (6 recipes) | `recipes/linkedin-*.recipe.json` | P0 |

**Tech stack:**
- UI: single HTML files, vanilla JS, no build step
- Server: extend `solace_browser_server.py` (new routes) OR create `ui_server.py` on port 9223
- API: existing `persistent_browser_server.py` at port 9222 (do NOT modify)
- Styling: simple CSS, no framework required (Tailwind CDN acceptable)

---

## Feature 1: Custom Home Page

### What
Landing page showing all supported sites with session status and quick actions.

### Route
`GET /` on the UI server (port 9223)

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🌊 Solace Browser        [Status: ● Server Running]        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Supported Sites                              [+ Add Site]  │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ 🔵 LinkedIn  │  │ 📧 Gmail    │  │ 🔴 Reddit   │        │
│  │ ● Active     │  │ ○ No session│  │ ● Expiring  │        │
│  │ 3h ago       │  │             │  │ 2d ago       │        │
│  │ [Activity]   │  │ [Connect]   │  │ [Activity]   │        │
│  │ [Run Recipe] │  │             │  │ [Run Recipe] │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ 🟠 HN       │  │ ⚫ GitHub   │  │ 🔵 Google   │        │
│  │ ○ No session│  │ ● Active    │  │ ● Active    │        │
│  │             │  │ 1d ago       │  │ 5h ago      │        │
│  │ [Connect]   │  │ [Activity]   │  │ [Activity]  │        │
│  │             │  │ [Run Recipe] │  │ [Run Recipe]│        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  Recent Activity                                            │
│  ─────────────────────────────────────────────────────────  │
│  2h ago  LinkedIn: Discovered 12 trending posts             │
│  3h ago  LinkedIn: Posted "AI tools for productivity"       │
│  1d ago  GitHub: Created issue #42                          │
└─────────────────────────────────────────────────────────────┘
```

### Site Cards

Each site card shows:
- Site icon (emoji or favicon) + name
- Session status badge:
  - `● Active` (green) — session file exists, age < 7 days
  - `● Expiring` (yellow) — session file age 5-7 days
  - `○ No session` (gray) — no session file for this site
- Last activity timestamp (from logs or artifact timestamps)
- Buttons:
  - `[Activity]` → navigate to `/activity?site={site}` (only if session active)
  - `[Connect]` → shown instead of Activity when no session; opens instructions for capturing session
  - `[Run Recipe]` → opens recipe selector modal (only if session active)

### Supported Sites (v1)

```json
[
  { "id": "linkedin", "name": "LinkedIn", "icon": "🔵", "domain": "linkedin.com", "session_file": "artifacts/linkedin_session.json" },
  { "id": "gmail", "name": "Gmail", "icon": "📧", "domain": "gmail.com", "session_file": "artifacts/gmail_session.json" },
  { "id": "reddit", "name": "Reddit", "icon": "🔴", "domain": "reddit.com", "session_file": "artifacts/reddit_session.json" },
  { "id": "hackernews", "name": "Hacker News", "icon": "🟠", "domain": "news.ycombinator.com", "session_file": "artifacts/hackernews_session.json" },
  { "id": "github", "name": "GitHub", "icon": "⚫", "domain": "github.com", "session_file": "artifacts/github_session.json" },
  { "id": "google", "name": "Google", "icon": "🔵", "domain": "google.com", "session_file": "artifacts/google_session.json" }
]
```

### Session Status Logic

```javascript
// Call existing API to check session files
async function getSiteStatus(site) {
  // Check if session artifact file exists and get its age
  const resp = await fetch(`http://localhost:9222/check-registry?site=${site.id}`);
  if (!resp.ok) return { status: 'none' };
  const data = await resp.json();
  const ageHours = (Date.now() - data.last_modified_ms) / 3600000;
  if (ageHours < 120) return { status: 'active', ageHours };
  if (ageHours < 168) return { status: 'expiring', ageHours };
  return { status: 'expired', ageHours };
}
```

### Recent Activity

Parse the last 10 entries from `logs/activity.jsonl` (create if absent):
```json
{"ts": "2026-02-21T10:00:00Z", "site": "linkedin", "recipe": "linkedin-discover-posts", "summary": "Discovered 12 trending posts"}
```

---

## Feature 2: Activity View (Twin Orchestrator)

### What
After session is active, show what the cloud twin has been doing and tools to inspect it.

### Route
`GET /activity?site=linkedin` on UI server

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back    🔵 LinkedIn Activity        [Run Recipe] [Sync]  │
├──────────────┬──────────────────────────────────────────────┤
│              │  [Activity Feed] [PrimeWiki] [State Diagram] [HTML Viewer]
│  SIDEBAR     │                                               │
│  ─────────── │  ── Activity Feed ─────────────────────────  │
│  Site info   │                                               │
│  Session:    │  ● 2h ago  linkedin-discover-posts           │
│    Active    │    ✓ Discovered 12 posts                     │
│  Last sync:  │    → View artifacts | View evidence          │
│    3h ago    │                                               │
│              │  ● 3h ago  linkedin-create-post              │
│  Recipes     │    ✓ Posted "AI tools for productivity"      │
│  ─────────── │    → View artifacts | View evidence          │
│  Run:        │                                               │
│  Discover    │  ○ 1d ago  linkedin-profile-update           │
│  Post        │    ✗ Failed: selector timeout                │
│  Comment     │    → Retry | View error log                  │
│  Edit        │                                               │
│  Delete      │                                               │
└──────────────┴─────────────────────────────────────────────-┘
```

### Tabs

**Tab 1: Activity Feed**
- Timeline of recipe runs for this site
- Source: `logs/activity.jsonl` filtered by site
- Each entry: timestamp, recipe name, status (✓ success / ✗ failed), summary
- Links: "View artifacts" → opens artifact JSON in modal; "View evidence" → opens evidence bundle

**Tab 2: PrimeWiki**
- Load and render markdown from `primewiki/{site}/` directory
- Show as formatted HTML (use marked.js CDN or simple regex renderer)
- If no PrimeWiki content: show "No knowledge graph yet — run a discovery recipe to build it"

**Tab 3: State Diagram**
- Load `.mmd` files from `checkpoints/` or `artifacts/` for this site
- Render using Mermaid.js CDN (add `<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js">`)
- Selector to switch between multiple diagrams if multiple `.mmd` files exist
- If no diagrams: show "No state diagrams yet"

**Tab 4: HTML Viewer**
- Input field for URL
- Button: "Fetch & Display"
- Calls `GET http://localhost:9222/html-clean?url={encoded_url}`
- Renders returned HTML in sandboxed iframe (sandbox="allow-scripts allow-same-origin")
- Also shows "View Raw" button to see the cleaned HTML source

---

## Feature 3: Kanban Recipe UI

### What
Visual task queue showing all recipe runs — queued, running, done, failed.

### Route
`GET /kanban` on UI server

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back    Recipe Queue                    [+ Add Task]     │
├─────────────┬───────────┬────────────┬───────────────────────┤
│  QUEUE (2)  │  RUNNING  │  DONE (5)  │  FAILED (1)          │
│             │   (1)     │            │                       │
│  ┌────────┐ │ ┌───────┐ │ ┌────────┐ │ ┌─────────────────┐  │
│  │LinkedIn│ │ │LinkedIn│ │ │LinkedIn│ │ │LinkedIn         │  │
│  │Discover│ │ │Create  │ │ │Discover│ │ │Profile Update   │  │
│  │Posts   │ │ │Post    │ │ │Posts   │ │ │                 │  │
│  │        │ │ │        │ │ │12 posts│ │ │selector timeout │  │
│  │[Cancel]│ │ │██░░ 40%│ │ │2h ago  │ │ │                 │  │
│  │        │ │ │[Cancel]│ │ │[Detail]│ │ │[Retry] [Detail] │  │
│  └────────┘ │ └───────┘ │ └────────┘ │ └─────────────────┘  │
│             │           │            │                       │
│  ┌────────┐ │           │ ... more   │                       │
│  │Reddit  │ │           │            │                       │
│  │Upvote  │ │           │            │                       │
│  │Workflow│ │           │            │                       │
│  │[Cancel]│ │           │            │                       │
│  └────────┘ │           │            │                       │
└─────────────┴───────────┴────────────┴───────────────────────┘
```

### Card Schema

```json
{
  "task_id": "uuid",
  "site": "linkedin",
  "recipe_id": "linkedin-discover-posts",
  "recipe_name": "Discover Posts",
  "status": "queued|running|done|failed",
  "progress_pct": 40,
  "created_at": "ISO8601",
  "started_at": "ISO8601|null",
  "completed_at": "ISO8601|null",
  "summary": "12 trending posts found",
  "error": "selector timeout on .feed-shared-update-v2",
  "artifact_path": "artifacts/runs/uuid/result.json"
}
```

### Task Queue Storage

Store queue in `artifacts/task_queue.jsonl` (append-only log). UI polls `GET /tasks` every 5s.

### Add Task Modal

```
[ Select Site ▼ ] [ Select Recipe ▼ ] [ Optional: Input params ]
                                                      [ Add to Queue ]
```

Recipe selector grouped by site:
- LinkedIn: Discover Posts, Create Post, Edit Post, Delete Post, React, Comment
- Gmail: Send Email, OAuth Login
- Reddit: Upvote, Comment, Create Post
- HackerNews: Upvote, Comment, Hide
- GitHub: Create Issue

### API Endpoints to Add

```
GET  /tasks              → return task_queue.jsonl as JSON array
POST /tasks              → add task { site, recipe_id, params }
POST /tasks/{id}/cancel  → mark task as cancelled
POST /tasks/{id}/retry   → re-queue failed task
GET  /tasks/{id}/result  → return artifact JSON for completed task
```

---

## Feature 4: LinkedIn MVP Recipes (6 recipes)

### Format Reference

Use existing `add-linkedin-project-optimized.recipe.json` as the format template.
All recipes must have: `recipe_id`, `version`, `created`, `description`, `reasoning`, `portals`, `steps`, `output_schema`.

---

### Recipe 1: linkedin-discover-posts

**File:** `recipes/linkedin-discover-posts.recipe.json`

**What it does:** Scroll the LinkedIn feed, collect top posts by engagement (likes + comments + shares), return structured list.

**Steps:**
1. Navigate to `https://www.linkedin.com/feed/`
2. Scroll down 3-5 times with human-like delays
3. Extract all feed posts visible on page: author, text snippet, likes, comments, shares, post URL
4. Filter: posts with > 50 total engagement
5. Sort by engagement descending
6. Return top 20 as JSON array

**Output schema:**
```json
{
  "posts": [
    {
      "author": "John Doe",
      "author_url": "https://linkedin.com/in/johndoe",
      "text_snippet": "First 200 chars of post...",
      "likes": 142,
      "comments": 38,
      "shares": 12,
      "post_url": "https://linkedin.com/feed/update/urn:li:...",
      "discovered_at": "ISO8601"
    }
  ],
  "total_found": 12,
  "page_scrolls": 4
}
```

**Selectors (from existing LinkedIn knowledge):**
- Feed posts: `role=article` or `.feed-shared-update-v2`
- Author: `.update-components-actor__title`
- Engagement counts: `.social-details-social-counts__reactions-count`

---

### Recipe 2: linkedin-create-post

**File:** `recipes/linkedin-create-post.recipe.json`

**What it does:** Create a new LinkedIn text post.

**Input params:**
```json
{ "text": "Post content here. Max 3000 chars." }
```

**Steps:**
1. Navigate to `https://www.linkedin.com/feed/`
2. Click "Start a post" button (`role=button[name='Start a post']`)
3. Click into the modal text area (`.ql-editor` or role=textbox)
4. Type text using `fill_slowly` with delay=15ms
5. Click "Post" button
6. Wait for success confirmation
7. Capture post URL from confirmation

**Output schema:**
```json
{
  "posted": true,
  "post_url": "https://linkedin.com/feed/update/urn:li:...",
  "timestamp": "ISO8601"
}
```

---

### Recipe 3: linkedin-edit-post

**File:** `recipes/linkedin-edit-post.recipe.json`

**What it does:** Edit an existing LinkedIn post by URL.

**Input params:**
```json
{ "post_url": "https://linkedin.com/feed/update/urn:li:...", "new_text": "Updated content" }
```

**Steps:**
1. Navigate to `post_url`
2. Click the `...` (more options) button on the post
3. Click "Edit post" from the menu
4. Clear existing text (Ctrl+A → Delete)
5. Type `new_text` using `fill_slowly`
6. Click "Save" button
7. Wait for success

**Output schema:**
```json
{ "edited": true, "post_url": "...", "timestamp": "ISO8601" }
```

---

### Recipe 4: linkedin-delete-post

**File:** `recipes/linkedin-delete-post.recipe.json`

**What it does:** Delete a LinkedIn post by URL.

**Input params:**
```json
{ "post_url": "https://linkedin.com/feed/update/urn:li:..." }
```

**Steps:**
1. Navigate to `post_url`
2. Click `...` (more options) button
3. Click "Delete post"
4. Click "Delete" in confirmation dialog
5. Verify post is gone (check for error or redirect)

**Output schema:**
```json
{ "deleted": true, "timestamp": "ISO8601" }
```

**Safety note:** This is irreversible. Recipe should log the post text before deleting.

---

### Recipe 5: linkedin-react-post

**File:** `recipes/linkedin-react-post.recipe.json`

**What it does:** React (like) to a LinkedIn post.

**Input params:**
```json
{ "post_url": "https://linkedin.com/feed/update/urn:li:...", "reaction": "like" }
```

**Steps:**
1. Navigate to `post_url` (or scroll feed to find it)
2. Find the Like button: `role=button[name='Like']` or `.reactions-react-button`
3. If already liked, skip (idempotent)
4. Click Like button
5. Verify reaction registered

**Output schema:**
```json
{ "reacted": true, "reaction": "like", "post_url": "...", "timestamp": "ISO8601" }
```

---

### Recipe 6: linkedin-comment-post

**File:** `recipes/linkedin-comment-post.recipe.json`

**What it does:** Leave a comment on a LinkedIn post.

**Input params:**
```json
{ "post_url": "https://linkedin.com/feed/update/urn:li:...", "comment_text": "Great post!" }
```

**Steps:**
1. Navigate to `post_url`
2. Click "Comment" button: `role=button[name='Comment']`
3. Click into comment text field (`.ql-editor` or role=textbox in comment panel)
4. Type `comment_text` using `fill_slowly` delay=15ms
5. Press Enter or click "Post" button in comment area
6. Verify comment appears

**Output schema:**
```json
{ "commented": true, "comment_text": "...", "post_url": "...", "timestamp": "ISO8601" }
```

---

## Differentiation: Free vs Paid

| Feature | Free (OSS) | Paid (solaceagi.com) |
|---|---|---|
| Home page | ✅ All sites | ✅ Same |
| Activity view | ✅ Local only | ✅ Cloud twin logs too |
| Kanban UI | ✅ Local execution | ✅ Cloud execution (24/7) |
| LinkedIn basic recipes | ✅ All 6 MVP recipes | ✅ Same |
| Recipe quality | Basic selectors | AI-enhanced (better fallbacks, retry logic, context-aware) |
| Post scheduling | ❌ Manual trigger | ✅ Cron-style scheduler |
| Discovery quality | Basic engagement sort | ✅ AI-scored (relevance + quality + sentiment) |
| Session persistence | Manual sync | ✅ Auto-sync (cloud mirror) |
| PrimeWiki content | Community-built | ✅ Curated + AI-enhanced |
| Task history | 7 days local | ✅ 90 days cloud |

**Key insight:** Same recipes, same open client — solaceagi.com adds intelligence and automation on top.
The recipe FORMAT is open; the recipe LIBRARY quality and cloud execution are the paid moat.

---

## Architecture Notes

### UI Server

Extend `solace_browser_server.py` with new routes, OR create `ui_server.py`:

```python
# Minimal server (no dependencies beyond stdlib)
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, os, pathlib

class SolaceUIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        routes = {
            '/': self.home_page,
            '/activity': self.activity_view,
            '/kanban': self.kanban_view,
            '/tasks': self.get_tasks,
            '/api/sites': self.api_sites,
        }
        handler = routes.get(self.path.split('?')[0])
        if handler: handler()
        else: self.send_error(404)
```

### Log Format

All recipes should append to `logs/activity.jsonl`:
```json
{"ts": "ISO8601", "site": "linkedin", "recipe_id": "linkedin-discover-posts", "task_id": "uuid", "status": "done", "summary": "12 posts found", "artifact_path": "artifacts/runs/uuid/result.json"}
```

### API Server Calls (from UI to port 9222)

UI makes fetch() calls to existing API:
- `GET http://localhost:9222/check-registry` — check session status
- `GET http://localhost:9222/html-clean?url={url}` — fetch cleaned HTML
- `GET http://localhost:9222/snapshot` — current page state
- `GET http://localhost:9222/screenshot` — screenshot

---

## Acceptance Criteria (Rung 641)

### Feature 1 — Home Page
- [ ] Loads at `http://localhost:9223/` without errors
- [ ] Shows all 6 supported sites as cards
- [ ] LinkedIn shows correct session status (Active/None) based on artifact file existence
- [ ] "Activity" button navigates to activity view
- [ ] "Connect" button shown when no session (with clear instructions)
- [ ] "Run Recipe" button opens recipe selector modal
- [ ] Recent Activity section shows last 3 log entries (or "No activity yet")

### Feature 2 — Activity View
- [ ] Loads at `/activity?site=linkedin` without errors
- [ ] Activity Feed tab shows log entries from `logs/activity.jsonl`
- [ ] PrimeWiki tab renders markdown from `primewiki/linkedin/` (or shows empty state)
- [ ] State Diagram tab renders Mermaid from any `.mmd` file in `artifacts/` (or empty state)
- [ ] HTML Viewer tab: input URL, click Fetch, shows cleaned HTML in iframe
- [ ] All 4 tabs switchable without page reload

### Feature 3 — Kanban UI
- [ ] Loads at `/kanban` without errors
- [ ] Shows 4 columns: Queue, Running, Done, Failed
- [ ] "Add Task" button opens recipe selector modal
- [ ] Adding a task creates entry in `artifacts/task_queue.jsonl`
- [ ] Task cards show site, recipe name, status
- [ ] "Retry" works on failed tasks
- [ ] Page auto-refreshes task status every 5 seconds

### Feature 4 — LinkedIn Recipes
- [ ] All 6 recipe JSON files exist in `recipes/`
- [ ] Each JSON is valid and matches the recipe format schema
- [ ] `reasoning` section explains selectors used
- [ ] `portals` section has selectors with `strength` scores
- [ ] `output_schema` is defined
- [ ] At least one recipe manually tested end-to-end (note which one and result)
