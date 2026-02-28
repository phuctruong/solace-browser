# TODO — Solace Browser (Sprint 3)

**Project:** solace-browser (OAuth3 browser automation + React frontend)
**Stack:** Python (Playwright) + React/TypeScript (Vite) + Firebase Auth
**Rung Target:** 274177 (stability — replay verified)
**Methodology:** Read .claude/skills/ — diagram-first, webservice-first, unit-test-first, prime-safety

---

## Sprint 2 Status: PARTIAL (2026-02-28)

Sprint 2 completed 3 of 6 tasks:
- DONE: TASK-001 — Fixed 37 fallback ban violations (0 remain)
- DONE: TASK-002 — Fixed 27 test failures (3,834 pass, 0 fail, 15 skip)
- DONE: TASK-001 — Recipe engine hardening + determinism tests (3,852 pass, 0 fail, 15 skip)
- DONE: TASK-002 — Real frontend implementation (176 vitest pass, build passes, 2,186 implementation lines)
- NOT DONE: Recipe expansion (Slack/GitHub/Notion still 49 lines / 3 steps)
- NOT DONE: Replay sweep, nothing committed

**Current state:**
- Tests: 3,852 PASS, 0 FAIL, 15 SKIP
- Fallback violations: 0
- `src/recipes/`: 1,560 lines
- Frontend pages + support files: 2,186 lines across pages, approval modal, client, types, constants, and task styling
- Existing recipe tests: 13 files, 28 passing tests
- Total recipes: 70 JSON + 7 Mermaid/MD
- 80 files uncommitted in working tree

---

## TASK-001: Recipe Engine Hardening + Determinism Tests

**Status:** DONE (2026-02-28)
**Rung Achieved:** 641
**Evidence:** `pytest tests/test_recipe_cache_hit.py tests/test_recipe_cache_miss.py tests/test_recipe_compiler_ir_schema.py tests/test_recipe_executor_action_failure.py tests/test_recipe_executor_happy_path.py tests/test_recipe_executor_scope_denial.py tests/test_recipe_metrics.py tests/test_recipe_parser_invalid.py tests/test_recipe_parser_valid.py tests/test_recipe_determinism.py tests/test_recipe_replay.py tests/test_recipe_all_parse.py tests/test_recipe_error_paths.py -q` → `28 passed`; `pytest tests/ -q` → `3852 passed, 15 skipped`; diagram: `diagrams/08-task-001-recipe-hardening.md`
**Priority:** CRITICAL — claimed rung 274177 but never tested determinism

The recipe engine (`src/recipes/`, 962 lines) was NOT modified in Sprints 1 or 2. It needs actual hardening code AND determinism proof tests. 9 recipe tests exist already (405 lines) — do NOT delete them. ADD to them.

**Existing test files (DO NOT DELETE):**
- `tests/test_recipe_cache_hit.py` (25L)
- `tests/test_recipe_cache_miss.py` (34L)
- `tests/test_recipe_compiler_ir_schema.py` (39L)
- `tests/test_recipe_executor_action_failure.py` (61L)
- `tests/test_recipe_executor_happy_path.py` (67L)
- `tests/test_recipe_executor_scope_denial.py` (60L)
- `tests/test_recipe_metrics.py` (51L)
- `tests/test_recipe_parser_invalid.py` (37L)
- `tests/test_recipe_parser_valid.py` (31L)

**New code to add in `src/recipes/`:**

1. **Determinism layer in `recipe_parser.py`:**
   - Add `parse_deterministic(recipe_path) -> DAG` that sorts nodes/edges canonically
   - Hash the canonical DAG (SHA-256 of sorted JSON)
   - Return `(dag, dag_hash)` tuple
   - Verify: parse same recipe 3× → identical hash each time

2. **Replay layer in `recipe_executor.py`:**
   - Add `execute_replay(recipe, sealed_output) -> bool` that replays from sealed outbox
   - No LLM call on replay — uses sealed artifacts only
   - Returns True if replay produces identical output hash
   - Cost of replay should be ~0 (no LLM, no browser)

3. **Cache verification in `recipe_cache.py`:**
   - Add `cache_stats() -> CacheStats` returning hit_count, miss_count, hit_rate
   - First run for a recipe must be a miss (assert miss_count increments)
   - Second identical run must be a hit (assert hit_count increments)

**New test files to create:**

4. `tests/test_recipe_determinism.py` (at least 5 tests):
   - Parse same recipe 3× → identical DAG hash each time
   - Parse 10 different recipes → all produce valid DAGs (no crashes)
   - Parse recipe with complex Mermaid (branches, conditions) → deterministic
   - Two recipes with same content but different whitespace → same hash
   - Recipe with Unicode characters → parses correctly

5. `tests/test_recipe_replay.py` (at least 5 tests):
   - Execute recipe → seal output → replay → identical hash
   - Replay with tampered sealed output → detected (hash mismatch)
   - Replay cost is near-zero (no LLM call counter increment)
   - Replay 3× → all 3 produce identical output
   - Replay missing recipe → specific error (not crash)

6. `tests/test_recipe_all_parse.py` (at least 3 tests):
   - Parse ALL 70 JSON recipes in `data/default/recipes/` → no errors
   - Every parsed recipe has required fields: steps, scopes
   - No recipe has empty steps list

7. `tests/test_recipe_error_paths.py` (at least 5 tests):
   - Missing required field → raises `RecipeValidationError` (not crash)
   - Invalid JSON → raises `RecipeParseError` (not silent empty)
   - Circular dependency in DAG → detected and rejected
   - Empty recipe file → specific error
   - Recipe with unknown action type → specific error

**Acceptance:**
- [x] `src/recipes/` has new code (line count 1,560 > 962)
- [x] `tests/test_recipe_determinism.py` exists with 5 tests, all pass
- [x] `tests/test_recipe_replay.py` exists with 5 tests, all pass
- [x] `tests/test_recipe_all_parse.py` — all 70 recipes parse
- [x] `tests/test_recipe_error_paths.py` — malformed input → specific errors
- [x] All 9 existing recipe tests still pass (no regressions)
- [x] Total recipe tests: 28 (was 9)
- [x] All 3,834 existing tests still pass

---

## TASK-002: Real Frontend Implementation (Pages Are 20-132 Line Stubs)

**Status:** DONE (2026-02-28)
**Rung Achieved:** 641
**Evidence:** `npm test -- --run src/__tests__/pages/Task002FrontendContract.test.tsx` → `6 passed`; `npm test` → `176 passed`; `npm run build` → success; `pytest tests/ -q` → `3852 passed, 15 skipped`; diagrams/contracts: `diagrams/09-task-002-frontend-state-machines.md`, `docs/task-002-frontend-api-contract.yaml`
**Priority:** HIGH — frontend pages are empty shells with no real logic

Current sizes: AppDetailPage(20L), RunDetailPage(32L), SetupMembershipPage(44L), SetupLLMPage(48L), LoginPage(56L), HomePage(132L), ApprovalModal(71L) = 403 lines total. These are stubs with placeholder text.

**Reference diagrams for frontend:**
- `diagrams/06-frontend-state-management.md` — page state machines
- `diagrams/10-approval-flow-architecture.md` — preview → approve → execute
- `diagrams/14-sealed-outbox-architecture.md` — outbox display in RunDetail

**Implement each page with real logic:**

1. **HomePage.tsx (target: 250+ lines):**
   - State: loading → loaded → error
   - Fetch installed apps list (mock API: `const apps = await fetch('/api/v1/store/apps?installed=true')`)
   - Render app cards in a grid (app name, status badge, last run time)
   - Credits remaining display (mock: `fetch('/api/v1/billing/credits')`)
   - Recent runs table with columns: app name, time, status, cost
   - Empty state when no apps installed: "Install your first app" card with link to store
   - Use `useEffect` + `useState` for data fetching (not just static JSX)

2. **LoginPage.tsx (target: 150+ lines):**
   - Firebase Auth SDK: `import { getAuth, signInWithPopup, GoogleAuthProvider } from 'firebase/auth'`
   - Google Sign-In button with proper onClick handler
   - Email + password form with `createUserWithEmailAndPassword`
   - Form validation: email format, password min 8 chars
   - Error states: wrong password, account exists, network error (display as red alert)
   - Loading spinner during auth
   - Redirect to `/` on success via `useNavigate`

3. **AppDetailPage.tsx (target: 200+ lines):**
   - URL param: `useParams<{ appId: string }>()`
   - Fetch app manifest: `fetch(\`/api/v1/store/apps/${appId}\`)`
   - Display sections: description, category badge, risk tier (color coded)
   - Scopes table: required (green bg), optional (yellow bg), step-up (red bg)
   - Budget display: max reads, sends, deletes per run
   - "Run Now" button → calls `setShowApproval(true)` → renders `<ApprovalModal>`
   - "Uninstall" button with confirmation dialog

4. **RunDetailPage.tsx (target: 200+ lines):**
   - URL param: `useParams<{ runId: string }>()`
   - Fetch run: `fetch(\`/api/v1/history/${runId}\`)`
   - Timeline component: vertical list of steps (step name, status icon, duration)
   - Evidence section: list of screenshots with thumbnails (lazy loaded with `loading="lazy"`)
   - Cost breakdown: level used, tokens consumed, cost, savings vs full LLM
   - Hash verification badge: "Verified" (green) or "Tampered" (red)
   - "Re-run" button

5. **SetupLLMPage.tsx (target: 120+ lines):**
   - Two cards: "Bring Your Own Key" vs "Managed LLM"
   - BYOK card: text input for API key + "Validate" button
   - Validation: POST to `/api/v1/oauth3/tokens` with key, show success/error
   - Managed card: explain Together.ai routing, show pricing ($3/mo)
   - Radio selection between the two options
   - Save button

6. **SetupMembershipPage.tsx (target: 120+ lines):**
   - Three plan cards side-by-side: Free ($0), Solace Pro ($8/mo), Enterprise (custom)
   - Feature comparison: checkmarks for what each tier includes
   - Current plan highlighted with "Current" badge
   - Upgrade button → POST `/api/v1/billing/checkout` → redirect to Stripe
   - Contact Sales button for Enterprise

7. **ApprovalModal.tsx (target: 120+ lines):**
   - Modal overlay with backdrop
   - Preview section: list of steps that will execute, scopes needed, cost estimate
   - Three buttons: Approve (green), Modify (yellow), Abort (red)
   - Approve → POST `/api/v1/tasks/{id}/approve`
   - Abort → POST `/api/v1/tasks/{id}/abort`
   - Override option: checkbox "Override safety check" + required reason textarea
   - Loading state during API call

**Frontend tests to add (in `frontend/src/__tests__/` or similar):**
- At least 6 component tests using vitest + @testing-library/react:
  - HomePage renders app grid (mock fetch)
  - LoginPage shows error on failed auth
  - AppDetailPage shows scope table
  - RunDetailPage renders timeline
  - ApprovalModal approve button calls API
  - SetupMembershipPage renders plan cards

**Acceptance:**
- [ ] Every page fetches data (has `fetch()` or equivalent API calls)
- [ ] Every page handles 3 states: loading (spinner), loaded (content), error (message)
- [ ] LoginPage has Firebase Auth `signInWithPopup` or equivalent
- [ ] ApprovalModal has approve/abort buttons that call API endpoints
- [ ] Total frontend lines: 1,200+ (was 403)
- [ ] 6+ component tests pass
- [ ] `npm run build` (or `npx vite build`) succeeds with no errors

---

## TASK-003: Expand Recipes to Full Workflows

**Status:** READY
**Priority:** MEDIUM — recipes are 49 lines / 3 steps each (too small for real use)

The 3 new recipes (Slack, GitHub, Notion reader) are all 49 lines with 3 steps. Real browser automation workflows need 8-15 steps with proper evidence capture, pagination, and error handling.

**Reference:** Existing full-size recipes for comparison:
- `data/default/recipes/notion/notion-create-page.json` (179L) — shows proper step structure
- `data/default/recipes/notion/notion-search.json` (187L) — shows pagination pattern

**Expand each recipe:**

1. **`data/default/recipes/slack/slack-channel-summary.json` (49L → 150+ lines, 10+ steps):**
   ```
   Step 1: Navigate to Slack workspace URL
   Step 2: Authenticate (OAuth3 scope: slack.read.channels)
   Step 3: Navigate to target channel
   Step 4: Scroll to load messages (handle pagination/infinite scroll)
   Step 5: Extract messages with timestamps + author names
   Step 6: Filter messages by date range (input parameter)
   Step 7: Categorize messages (questions, decisions, action items, FYI)
   Step 8: Generate summary via LLM (scope: llm.generate.text)
   Step 9: Format output as markdown
   Step 10: Save to outbox (scope: outbox.write)
   Step 11: Capture final evidence screenshot
   ```
   Each step needs: `action`, `selector` (CSS/XPath), `scope_required`, `evidence_capture: true/false`, `timeout_ms`, `on_error` (specific behavior)

2. **`data/default/recipes/github/github-issue-triage.json` (49L → 150+ lines, 10+ steps):**
   ```
   Step 1: Navigate to repo issues page
   Step 2: Authenticate (OAuth3 scope: github.read.issues)
   Step 3: Apply filters (open + unassigned)
   Step 4: Extract issue list (title, labels, age)
   Step 5: For each issue: extract body + comments
   Step 6: Classify priority (critical/high/medium/low) via LLM
   Step 7: Classify type (bug/feature/question/docs) via LLM
   Step 8: Suggest assignee based on label history
   Step 9: Draft triage report (markdown table)
   Step 10: Save to outbox
   Step 11: Capture evidence
   ```

3. **`data/default/recipes/notion/notion-page-reader.json` (49L → 120+ lines, 8+ steps):**
   ```
   Step 1: Navigate to Notion page URL
   Step 2: Authenticate (OAuth3 scope: notion.read.pages)
   Step 3: Wait for page load (handle Notion's dynamic rendering)
   Step 4: Extract page title + properties
   Step 5: Extract content blocks (headings, paragraphs, lists, tables, code)
   Step 6: Parse nested/indented blocks preserving hierarchy
   Step 7: Generate structured summary via LLM
   Step 8: Save to outbox
   Step 9: Capture evidence
   ```

**Each step in every recipe MUST have these fields:**
```json
{
  "step_id": "step_01_navigate",
  "action": "navigate",
  "url": "https://...",
  "selector": null,
  "scope_required": "platform.action.resource",
  "evidence_capture": true,
  "timeout_ms": 10000,
  "on_error": "fail_with_screenshot",
  "description": "Navigate to workspace"
}
```

**Budget constraints (add to each recipe):**
```json
"budget": {
  "max_reads": 100,
  "max_sends": 0,
  "max_deletes": 0,
  "max_llm_calls": 3,
  "max_duration_seconds": 300
}
```

**Tests:**
- `tests/test_expanded_recipes.py` (at least 3 tests):
  - Parse slack-channel-summary.json → valid, 10+ steps
  - Parse github-issue-triage.json → valid, 10+ steps
  - Parse notion-page-reader.json → valid, 8+ steps
  - Every step has required fields (action, scope_required, evidence_capture)

**Acceptance:**
- [ ] slack-channel-summary.json: 10+ steps, 120+ lines (was 49L / 3 steps)
- [ ] github-issue-triage.json: 10+ steps, 120+ lines (was 49L / 3 steps)
- [ ] notion-page-reader.json: 8+ steps, 100+ lines (was 49L / 3 steps)
- [ ] Every step has: action, scope_required, evidence_capture, timeout_ms, on_error
- [ ] Budget constraints present in each recipe
- [ ] All 3 expanded recipes parse without error (tested)
- [ ] All existing 70 recipes still parse (no regressions)

---

## TASK-004: Rung 274177 Replay Sweep

**Status:** READY (unblocked by TASK-001 on 2026-02-28)
**Priority:** Required for promotion

After TASK-001 adds determinism tests, run the FULL test suite 3 times. All 3 must match.

1. `pytest tests/ -v --tb=short 2>&1 | tee /tmp/solace-browser-replay-run1.txt`
2. `pytest tests/ -v --tb=short 2>&1 | tee /tmp/solace-browser-replay-run2.txt`
3. `pytest tests/ -v --tb=short 2>&1 | tee /tmp/solace-browser-replay-run3.txt`
4. Normalize outputs (strip timing): `grep -E "PASSED|FAILED|ERROR" /tmp/solace-browser-replay-run1.txt | sort > /tmp/run1-normalized.txt` (same for run2, run3)
5. Compare: `sha256sum /tmp/run*-normalized.txt` — all 3 must match

**Acceptance:**
- [ ] 3 runs produce identical normalized results (same SHA-256)
- [ ] Zero flaky tests (no test passes in one run but fails in another)
- [ ] Zero failures across all 3 runs
- [ ] 3,850+ tests pass in each run (was 3,834 + new recipe tests)
- [ ] Evidence: SHA-256 hashes printed for all 3 runs

---

## TASK-005: Commit All Work

**Status:** BLOCKED by TASK-004
**Priority:** CRITICAL — 48 files uncommitted in working tree

After all tasks pass, commit everything:

1. `git add -A` (all Sprint 2+3 changes)
2. Commit: `git commit -m "feat: Sprint 2+3 — fallback ban clean, recipe determinism, frontend implementation, expanded recipes, rung 274177"`
3. Verify: `git status` shows clean working tree
4. Do NOT push (manual deployment only)

**Acceptance:**
- [ ] All changes committed
- [ ] `git status` clean after commit
- [ ] Tests pass after commit: `pytest tests/ -q`
- [ ] Commit message describes what was built

---

## Execution Order

```
DO IN ORDER (each depends on previous):
  TASK-001: Recipe engine hardening + 25+ tests    ← DONE
  TASK-002: Real frontend implementation            ← DONE
  TASK-003: Expand recipes to full workflows        ← READY
  TASK-004: Rung 274177 replay sweep                ← READY
  TASK-005: Commit all work                         ← BLOCKED by TASK-004
```

TASK-003 and TASK-004 are now the active queue. TASK-005 remains blocked by TASK-004.

---

**Total:** 5 tasks. Recipe hardening and frontend are complete; recipe expansion and replay sweep remain before commit.
**Current state:** 3,852 Python tests pass, 15 skip; 176 frontend tests pass; frontend build passes; 0 fallback violations
**Target:** 25+ recipe tests, real frontend (1,200+ lines), full recipes (10+ steps each), rung 274177, committed.
