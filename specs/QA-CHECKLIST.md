# QA Checklist — Solace Browser MVP UI + LinkedIn Recipes

**QA Auditor:** Claude Sonnet 4.6 (main session, separate from builder session)
**Builder session:** haiku + sonnet swarms
**Rung Target:** 641 (local correctness)
**Build Spec:** `specs/BUILD-SPEC.md`

> This checklist is the source of truth for QA verification. Items must be checked by
> running the actual server and verifying observable behavior — not by code inspection alone.

---

## How QA Works

1. Builder session implements features per `BUILD-SPEC.md`
2. Builder runs `python ui_server.py` (or whatever they named it)
3. Builder pastes screenshot or curl output as evidence
4. QA session (this session) verifies against checklist items below
5. Any FAIL → builder session opens a bugfix task with exact repro steps
6. QA signs off when all P0 items pass

---

## Pre-flight Checks (must pass before testing features)

- [ ] `python persistent_browser_server.py` starts without errors on port 9222
- [ ] `curl http://localhost:9222/` returns a response (not connection refused)
- [ ] `python ui_server.py` (or equivalent) starts without errors on port 9223
- [ ] No import errors in any new Python files
- [ ] `ls recipes/linkedin-*.recipe.json` returns 6+ files
- [ ] All 6 recipe JSON files are valid JSON (`python -c "import json; json.load(open('recipes/linkedin-X.recipe.json'))"`)

---

## Feature 1: Home Page

**Route:** `http://localhost:9223/`

### Structure
- [ ] Page loads without 500 error
- [ ] Page title is "Solace Browser" or similar (not "localhost" default)
- [ ] Shows exactly 6 site cards: LinkedIn, Gmail, Reddit, Hacker News, GitHub, Google
- [ ] No broken layout (all cards visible, no overflow clipping)

### Session Status
- [ ] If `artifacts/linkedin_session.json` EXISTS: LinkedIn card shows Active (green)
- [ ] If `artifacts/linkedin_session.json` MISSING: LinkedIn card shows "No session" (gray)
- [ ] Session age logic: create a session file with mtime > 6 days ago → should show "Expiring"

### Buttons
- [ ] "Activity" button visible on card with active session
- [ ] "Connect" button visible on card with no session
- [ ] "Run Recipe" button visible on card with active session
- [ ] Clicking "Activity" navigates to `/activity?site=linkedin` (correct site ID)
- [ ] Clicking "Run Recipe" opens a recipe selector (modal or dropdown)

### Recent Activity
- [ ] If `logs/activity.jsonl` is empty or absent: shows "No activity yet" (no crash)
- [ ] If log has entries: shows last 3 entries with site + recipe + summary

---

## Feature 2: Activity View

**Route:** `http://localhost:9223/activity?site=linkedin`

### Structure
- [ ] Page loads without error
- [ ] Shows site name in header ("LinkedIn Activity" or similar)
- [ ] Shows 4 tabs: Activity Feed, PrimeWiki, State Diagram, HTML Viewer
- [ ] Default tab is "Activity Feed"
- [ ] Clicking each tab switches content without full page reload

### Activity Feed Tab
- [ ] If `logs/activity.jsonl` has linkedin entries: shows them in reverse chronological order
- [ ] Each entry shows: timestamp (human-readable), recipe name, status icon (✓/✗), summary
- [ ] If no linkedin entries: shows "No activity yet for LinkedIn"
- [ ] "View artifacts" link present on done tasks (even if it just opens the JSON)
- [ ] No JavaScript console errors

### PrimeWiki Tab
- [ ] If `primewiki/linkedin/` has `.md` files: renders as HTML (not raw markdown)
- [ ] If directory empty/absent: shows "No knowledge graph yet — run a discovery recipe to build it"
- [ ] No crash/404

### State Diagram Tab
- [ ] If any `.mmd` file exists in `artifacts/` or `checkpoints/`: renders as Mermaid diagram
- [ ] Mermaid.js loads from CDN (check network tab)
- [ ] If no `.mmd` files: shows "No state diagrams yet"
- [ ] Diagram is readable (not blank white box)

### HTML Viewer Tab
- [ ] URL input field is present
- [ ] "Fetch & Display" button is present
- [ ] Clicking button calls `http://localhost:9222/html-clean?url={url}` (verify in network tab)
- [ ] Returned HTML renders in iframe or content area
- [ ] If browser server is down: shows error message (not blank/crash)
- [ ] "View Raw" button shows cleaned HTML source

---

## Feature 3: Kanban UI

**Route:** `http://localhost:9223/kanban`

### Structure
- [ ] Page loads without error
- [ ] Shows 4 columns: Queue, Running, Done, Failed (with task counts in header)
- [ ] Columns are horizontal layout (not vertical)
- [ ] "Add Task" button visible

### Empty State
- [ ] If `artifacts/task_queue.jsonl` is absent: all columns show "No tasks" (no crash)

### Add Task
- [ ] Clicking "+ Add Task" opens recipe selector
- [ ] Recipe selector shows recipes grouped by site
- [ ] All 6 LinkedIn recipes appear in LinkedIn group
- [ ] Selecting a recipe and confirming adds card to Queue column
- [ ] New task appears in `artifacts/task_queue.jsonl` as a new JSON line

### Task Cards
- [ ] Each card shows: site icon/name, recipe name, status
- [ ] Done cards show: summary text (from artifact or log)
- [ ] Failed cards show: error message snippet
- [ ] Running cards show: progress indicator (even if it's just a spinner)

### Auto-refresh
- [ ] Page updates task statuses without full reload every ~5 seconds
- [ ] Moving a task from Queue → Done updates the UI automatically

### Actions
- [ ] "Cancel" on queued task removes it from queue (or marks cancelled)
- [ ] "Retry" on failed task moves it back to queue
- [ ] "Detail" link opens artifact JSON in modal or new tab

---

## Feature 4: LinkedIn MVP Recipes

**Directory:** `recipes/linkedin-*.recipe.json`

### Schema Validation (all 6 files)

For each recipe, verify:
- [ ] `recipe_id` matches filename (e.g. `linkedin-discover-posts` matches filename)
- [ ] `version` field present (string)
- [ ] `description` field present (string, non-empty)
- [ ] `reasoning` object with at least one key explaining the approach
- [ ] `portals` object with at least one selector entry
- [ ] Each selector has `strength` (float 0-1) and `type` fields
- [ ] `output_schema` object defined (what the recipe returns)
- [ ] JSON is valid (no trailing commas, no syntax errors)

### Recipe-specific Checks

**linkedin-discover-posts:**
- [ ] `output_schema` includes `posts` array with `author`, `text_snippet`, `likes` fields
- [ ] `reasoning` mentions the feed selectors used
- [ ] Steps include scroll action (human-like scroll to see more posts)

**linkedin-create-post:**
- [ ] `input_params` schema includes `text` field
- [ ] `reasoning` mentions `fill_slowly` with delay for text input
- [ ] Steps include opening the "Start a post" modal

**linkedin-edit-post:**
- [ ] `input_params` includes `post_url` and `new_text`
- [ ] Steps include clicking `...` menu to find Edit option
- [ ] Steps include clearing existing text before typing new text

**linkedin-delete-post:**
- [ ] `input_params` includes `post_url`
- [ ] Steps include confirmation dialog handling
- [ ] `reasoning` includes safety note about irreversibility
- [ ] Recipe logs post text before deleting (evidence requirement)

**linkedin-react-post:**
- [ ] Idempotent: if already liked, recipe should NOT double-like
- [ ] `input_params` includes `reaction` field

**linkedin-comment-post:**
- [ ] `input_params` includes `comment_text`
- [ ] Uses `fill_slowly` with delay=15ms (consistent with existing LinkedIn patterns)
- [ ] Steps include finding the comment input field specifically (not the post input)

---

## End-to-End Integration Test

Pick ONE recipe and run it manually:

```bash
# Verify server is running
curl http://localhost:9222/

# Run the discover posts recipe (most safe — read-only)
curl -X POST http://localhost:9222/run-recipe \
  -H "Content-Type: application/json" \
  -d '{"recipe_id": "linkedin-discover-posts"}'
```

- [ ] Recipe runs without Python errors
- [ ] Returns JSON matching `output_schema`
- [ ] Result logged to `logs/activity.jsonl`
- [ ] Result visible in Kanban "Done" column
- [ ] Result visible in Activity View "Activity Feed" tab

---

## Red Flags (auto-FAIL)

Any of these = immediate fail, builder must fix before re-review:

- JavaScript `Uncaught TypeError` in browser console
- Python `Traceback` on server startup
- Feature route returns 500 error
- Recipe JSON fails `json.loads()` validation
- Kanban "Add Task" crashes server
- HTML Viewer tab crashes when browser server is down (must show error gracefully)
- `linkedin-delete-post` recipe missing safety log (irreversible action without evidence)

---

## Sign-off

QA passes when:
- [ ] All P0 acceptance criteria from BUILD-SPEC.md checked
- [ ] All 6 recipe JSON files validated
- [ ] End-to-end test passes with at least one recipe
- [ ] No Red Flags outstanding

**QA Sign-off:** `[ ] PASS at Rung 641 — {date} — QA: Claude Sonnet 4.6`
