# Paper 57: Solace Browser Coding App
# DNA: `coding_app(task) = inbox(northstar + skills + constraints + task) → yinyang(execute + evidence) → outbox(diff + screenshot + hash) → human(approve/reject)`
# Auth: 65537 | Version: 1.0.0 | Status: DRAFT
# Forbidden: SELF_REVIEW, DIRECT_FILE_WRITE, UNSCOPED_TASK, UNWITNESSED_PASS, DRIFT_FROM_TASK, GIT_WRITE, FALLBACK_SILENCE

---

## 1. Purpose

A Solace Browser app that writes code for Solace Browser itself. The app uses Yinyang as a chained proxy to Claude Code CLI. Every action goes through the consent/evidence pipeline. The coding agent cannot self-review, cannot commit, cannot drift.

**Constraint:** This app can ONLY modify Solace Browser source code. Nothing else. This constraint makes it 10x better because the agent has deep context about one codebase instead of shallow context about everything.

## 2. Architecture

```
USER (in Yinyang sidebar)
  │
  ├─── "Add native sidebar to Chromium"
  │
  ▼
INBOX (prepared by Yinyang before each task)
  │
  ├── northstar.md          — AI Worker Platform, Local-First, Evidence-Driven
  ├── skills/               — Compressed skills injected per task
  ├── constraints.md        — What the agent CAN'T do
  ├── task.md               — Single atomic task with acceptance criteria
  ├── context/              — Relevant source files (read-only reference)
  ├── conventions/config.yaml
  ├── conventions/defaults.yaml
  └── policies/safety.yaml
  │
  ▼
YINYANG (sidebar orchestrator)
  │
  ├── Reads inbox
  ├── Composes prompt: northstar + skills + constraints + task + context
  ├── Spawns Claude Code CLI as subprocess
  ├── Receives proposed diffs
  ├── Displays diffs in sidebar for user approval
  │
  ▼
USER (approve/reject each diff)
  │
  ▼
YINYANG (if approved)
  │
  ├── Writes approved files
  ├── Runs build (autoninja)
  ├── Takes screenshot (browser captures, not agent)
  ├── Hashes evidence (SHA-256 chain)
  │
  ▼
OUTBOX (sealed results)
  │
  ├── diffs/                — Approved file changes
  ├── evidence/             — Screenshots, build logs, hashes
  ├── report.md             — What was done (written by Yinyang, not agent)
  └── runs/evidence.json    — Hash-chained evidence bundle
```

## 3. App Manifest

```yaml
id: solace-browser-coder
name: Solace Browser Coder
description: Writes code for Solace Browser. Chained through Yinyang consent pipeline.
category: development
status: installed
safety: B
tier: free
tier_reason: "Core development tool — free for all contributors"
site: "localhost:*"
type: standard
scopes:
  - local.filesystem.read
  - local.filesystem.write
  - local.process.spawn
  - local.evidence
partners:
  produces_for: []
  consumes_from: []
required_inbox:
  prompts:
    - system-prompt.md
  policies:
    - safety.yaml
    - allowed-paths.yaml
  conventions:
    config: config.yaml
    defaults: defaults.yaml
```

## 4. Budget

```json
{
  "max_llm_calls_per_task": 20,
  "max_cost_per_task_usd": 0.50,
  "max_files_per_task": 5,
  "max_lines_changed_per_task": 200,
  "cooldown_seconds": 5,
  "remaining_runs": 999,
  "reads_per_run": 50,
  "writes_per_run": 5,
  "drafts_per_run": 3,
  "daily_max_tasks": 20,
  "daily_max_cost_usd": 5.00,
  "current_usage": {
    "tasks_today": 0,
    "cost_today_usd": 0.0,
    "files_changed_today": 0
  }
}
```

## 5. Constraints (What Makes It 10x Better)

The coding app is CONSTRAINED to Solace Browser only. These constraints are load-bearing — removing any one degrades quality.

### C1: Single Codebase Lock
- Can ONLY read/write files under `/home/phuc/projects/solace-browser/`
- Cannot touch solace-cli, solaceagi, or any other project
- **Why better:** Deep context > shallow breadth. The agent knows every file.

### C2: Single Task Per Session
- Receives exactly ONE task with explicit acceptance criteria
- Cannot decide what to work on next
- Cannot expand scope mid-task
- **Why better:** No drift. The task is done or it isn't.

### C3: No Self-Review
- Agent proposes diffs. Cannot review its own diffs.
- Review is done by: (a) the user in sidebar, (b) external LLMs via /llm-qa
- **Why better:** Eliminates the "I reviewed my work and it looks good" failure mode.

### C4: No Git Access
- Cannot `git add`, `git commit`, `git push`, `git log`
- Yinyang handles all git operations after user approval
- **Why better:** Agent can't create fake evidence trail.

### C5: Build Gate
- Every approved change must compile: `autoninja -C out/Solace chrome`
- If build fails, change is reverted automatically
- **Why better:** No "I'll fix the build later." It compiles or it doesn't exist.

### C6: Screenshot Gate
- After every successful build, browser takes screenshot of running binary
- Screenshot is captured by browser, not by agent
- User sees screenshot in sidebar
- **Why better:** Visual proof. This is what caught the extension lie.

### C7: Max 5 Files Per Task
- Cannot change more than 5 files in one task
- Forces atomic, reviewable changes
- **Why better:** User can actually review 5 files. Can't review 50.

### C8: Max 200 Lines Per Task
- Cannot change more than 200 lines in one task
- Forces small, focused diffs
- **Why better:** Small diffs are correct diffs.

### C9: Allowed Paths Only
- Can only modify paths listed in `policies/allowed-paths.yaml`
- Default: `source/src/chrome/browser/**` (Chromium browser code)
- Explicitly banned: `source/src/third_party/**`, `depot_tools/**`, `build/**`
- **Why better:** Can't accidentally modify build infrastructure or dependencies.

### C10: Token Budget Per Task
- Max 20 LLM calls, max $0.50 per task
- Yinyang tracks usage, hard stop at limit
- **Why better:** Forces efficiency. Can't burn tokens on wrong approaches.

## 6. Inbox Structure (Where Every Uplift Lives)

The inbox is prepared by Yinyang BEFORE spawning Claude Code. Every uplift is injected as a specific inbox file.

### 6.1 Uplift → Inbox Mapping

| Uplift | Inbox File | How It's Applied |
|--------|-----------|-----------------|
| **P1 Gamification** | `conventions/config.yaml` | GLOW score tracking. Task completion → GLOW increment. Belt progression visible in sidebar. |
| **P2 Magic Words** | `prompts/system-prompt.md` | DNA equation for the task injected at top of prompt. "coding_app(task) = inbox → execute → outbox" |
| **P3 Famous Personas** | `prompts/system-prompt.md` | Persona locked to CODER. "You are a Chromium C++ coder. You propose diffs. That's it." No architect, no reviewer, no planner. |
| **P4 Skills** | `skills/` | Compressed skills injected per task type. C++ task → prime-coder + styleguide. WebUI task → prime-coder + prime-javascript. Safety-related → prime-safety (always). |
| **P5 Recipes** | `conventions/defaults.yaml` | Previous successful diffs cached. If same pattern needed again, replay from cache instead of LLM call. Cost: $0.001 replay vs $0.10 LLM. |
| **P6 Access Tools** | `policies/allowed-paths.yaml` | Tool access scoped: read (source/**), write (chrome/browser/** only), spawn (autoninja only). No git. No network. No other projects. |
| **P7 Memory** | `context/` | Relevant source files loaded as read-only context. Previous task results from outbox. What was tried before and failed. |
| **P8 Care/Motivation** | `prompts/system-prompt.md` | Anti-Clippy: never auto-approve, never presume intent, never expand scope. "If unclear, output BLOCKED with reason." |
| **P9 Knowledge** | `context/` | Chromium architecture docs. Side panel API docs. WebUI binding docs. Loaded per task relevance. |
| **P10 God** | `policies/safety.yaml` | 65537 authority. Evidence is sacred. Every diff must be witnessed. No unwitnessed passes. |
| **P11 Questions** | `task.md` | Acceptance criteria as testable questions: "Does the sidebar panel appear?" "Does the title say Yinyang?" "Does the build succeed?" |
| **P12 Analogies** | `prompts/system-prompt.md` | "The sidebar is like Chrome's bookmarks panel — always visible, native to the browser, not an extension." |
| **P13 Constraints** | `policies/safety.yaml` + `budget.json` | All 10 constraints from Section 5. Max 5 files, max 200 lines, single task, no git, no self-review. |
| **P14 Chain of Thought** | `prompts/system-prompt.md` | Required output format: (1) What I'll change and why, (2) Proposed diff, (3) Expected build result, (4) Expected visual result. |
| **P15 Few-Shot Exemplars** | `context/examples/` | Example of a correct side panel registration in Chromium. Example of a correct WebUI binding. Real code from Chromium source. |
| **P16 Negative Space** | `prompts/system-prompt.md` | "FORBIDDEN: Do not modify build files. Do not add new dependencies. Do not change third_party. Do not create test files (Yinyang handles testing)." |
| **P17 Stakes** | `prompts/system-prompt.md` | "This is a real product. Real users will use this browser. The previous agent lied about building it. You must actually build it. If you can't, say so." |
| **P18 Audience** | `prompts/system-prompt.md` | Persona: Chromium C++ developer. Not a general-purpose AI. Not an architect. A coder who writes diffs for one codebase. |
| **P19 Compression** | `prompts/system-prompt.md` | "Output format: diff only. No explanations longer than 3 sentences. No markdown formatting. Just the diff and why." |
| **P20 Temporal** | `task.md` | "Current state: Chromium compiled at commit X. Last change: [description]. Next milestone: [phase goal]." |
| **P21 Adversarial** | Handled by Yinyang, NOT the agent | Yinyang sends approved diffs to external LLMs for adversarial review. Agent never sees the review. |
| **P22 LEAK/Oracle** | `context/previous-failures/` | Previous task failures loaded. "Last time this was attempted, it failed because X. Don't repeat." Oracle learns from misses. |
| **P23 Breathing** | Task decomposition by Yinyang | Yinyang breaks big goals into atomic tasks (compress → expand → compress). Each task = one breath cycle. |
| **P24 Heartbeat** | Yinyang monitors subprocess | If Claude Code hangs for >60s without output, kill and retry. Heartbeat check every 30s. |
| **P25 Soul Architecture** | `conventions/config.yaml` | App identity: "I am the Solace Browser Coder. I write C++ and WebUI code for one browser." Stable identity prevents drift. |
| **P26 Notebook Uplift** | Yinyang post-task | After task complete, Yinyang runs /notebook-qa probes against the change. Not the agent's job. |
| **P27-P38 Architecture** | `context/` | Loaded as reference when relevant. Not injected every time. |
| **P39 Evidence Chains** | Outbox pipeline | Every approved diff → SHA-256 hash → chain.py append. Not controlled by agent. |
| **P40 Fail-Closed** | `policies/safety.yaml` | Default: BLOCKED. Agent must justify every file write. Unknown = REFUSE. |
| **P41 Never-Worse** | Yinyang build gate | If build fails after change, auto-revert. Codebase never gets worse. |
| **P42 Diagram-First** | `context/diagrams/` | Architecture diagrams loaded for context. Agent sees the intended design. |
| **P43 GLOW Tracking** | `conventions/config.yaml` | Current GLOW score. Task adds to GLOW on success. Visible in sidebar. |
| **P44 Triple-Twin** | Future: cloud twin runs same task | Not for v1. |
| **P45 Dragon-Rider** | Sidebar approval flow | Dragon (Yinyang) proposes. Rider (user) approves. Neither acts alone. |
| **P46 NORTHSTAR** | `northstar.md` | Injected first line of every prompt. "NORTHSTAR: AI Worker Platform — Token Economics + Local-First + Evidence-Driven" |
| **P47 Love** | `prompts/system-prompt.md` | "Code is craft. Evidence is truth. Build what's real." |

### 6.2 Inbox File Details

**northstar.md:**
```
NORTHSTAR: AI Worker Platform — Token Economics + Local-First + Evidence-Driven
PROJECT: Solace Browser (Custom Chromium Fork)
CURRENT PHASE: [set by Yinyang per task]
BINARY: source/src/out/Solace/chrome
```

**prompts/system-prompt.md:**
```
DNA: coding_app(task) = inbox(northstar + skills + constraints + task) → yinyang(execute + evidence) → outbox(diff + screenshot + hash) → human(approve/reject)

You are a Chromium C++ and WebUI developer. You write code for Solace Browser only.

ROLE: CODER. You propose diffs. You do not review, plan, test, commit, or decide scope.

OUTPUT FORMAT:
1. What I'll change and why (max 3 sentences)
2. Proposed diff (unified diff format)
3. Expected build result
4. Expected visual result

FORBIDDEN:
- Do not modify build files (BUILD.gn, args.gn, .gni)
- Do not add dependencies to third_party/
- Do not create test files (Yinyang handles testing)
- Do not run git commands
- Do not review your own code
- Do not expand scope beyond the assigned task
- Do not claim "done" — Yinyang verifies with build + screenshot
- If you cannot complete the task, output BLOCKED with reason

STAKES: The previous agent lied about building this browser for months.
You must actually build it. If something doesn't compile, say so.

[P4 SKILLS INJECTED HERE — varies per task]
[P8 CARE: Never auto-approve. Never presume intent. If unclear → BLOCKED.]
[P12 ANALOGY: The sidebar is like Chrome's bookmarks panel — native, always visible.]
[P17 STAKES: Real product. Real users. Your diff will be compiled and run.]
[P47 LOVE: Code is craft. Evidence is truth. Build what's real.]
```

**policies/safety.yaml:**
```yaml
authority: 65537
default_action: BLOCKED
evidence_required: true
fail_mode: closed

allowed_actions:
  - read_file
  - propose_diff

forbidden_actions:
  - write_file_directly
  - git_any
  - spawn_process
  - network_request
  - self_review
  - scope_expansion

allowed_paths:
  read:
    - "source/src/chrome/browser/**"
    - "source/src/chrome/app/**"
    - "source/src/ui/**"
    - "source/src/content/**"
  write:
    - "source/src/chrome/browser/ui/views/side_panel/solace/**"
    - "source/src/chrome/browser/ui/webui/solace/**"
    - "source/src/chrome/browser/resources/solace/**"
    - "source/src/chrome/app/chromium_strings.grd"

forbidden_paths:
  - "source/src/third_party/**"
  - "depot_tools/**"
  - "build/**"
  - "source/src/out/**"
  - ".git/**"
```

**conventions/defaults.yaml:**
```yaml
language: cpp
style: chromium
indent: 2_spaces
line_length: 80
naming: chromium_convention
build_command: "autoninja -C out/Solace chrome"
build_timeout_seconds: 600
screenshot_after_build: true
revert_on_build_failure: true
max_files_per_task: 5
max_lines_per_task: 200
model: claude-opus-4-6
token_budget_per_task: 20000
```

**task.md (example — set by Yinyang per task):**
```
TASK: Register Solace side panel coordinator in Chromium
PHASE: 3 (Native Sidebar)
TEMPORAL: Stock Chromium compiled at [commit]. No customizations yet.

FILES TO CREATE:
- chrome/browser/ui/views/side_panel/solace/solace_side_panel_coordinator.h
- chrome/browser/ui/views/side_panel/solace/solace_side_panel_coordinator.cc

FILES TO MODIFY:
- chrome/browser/ui/views/side_panel/side_panel_coordinator.cc (register our panel)

ACCEPTANCE CRITERIA:
1. Build succeeds: autoninja -C out/Solace chrome → exit 0
2. Binary runs: ./out/Solace/chrome launches
3. Side panel entry appears in side panel menu
4. Screenshot shows "Yinyang" in side panel list

REFERENCE:
- See how reading_list_side_panel_coordinator.cc registers itself
- See side_panel_entry.h for entry registration pattern
```

## 7. Outbox Structure

After task completion, Yinyang (not the agent) writes:

```
outbox/
├── runs/
│   └── run-20260308-120000.json    # Evidence bundle
├── diffs/
│   └── task-001-sidebar-coord.patch # Approved unified diff
├── screenshots/
│   └── task-001-after.png          # Browser screenshot (taken by browser)
├── build-logs/
│   └── task-001-build.log          # autoninja output
└── report.md                       # Summary (written by Yinyang)
```

**runs/evidence.json:**
```json
{
  "app_id": "solace-browser-coder",
  "run_id": "run-20260308-120000",
  "task": "Register Solace side panel coordinator",
  "status": "APPROVED",
  "files_changed": 3,
  "lines_changed": 87,
  "build_result": "SUCCESS",
  "screenshot_hash": "sha256:abc123...",
  "diff_hash": "sha256:def456...",
  "build_log_hash": "sha256:ghi789...",
  "evidence_chain_hash": "sha256:jkl012...",
  "approved_by": "human",
  "approved_at": "2026-03-08T12:00:00Z",
  "token_usage": 8432,
  "cost_usd": 0.12,
  "glow_increment": 1
}
```

## 8. Recipe (Workflow Steps)

```json
{
  "id": "solace-browser-coder",
  "version": "1.0.0",
  "type": "standard",
  "platform": "localhost",
  "oauth3_scopes": ["local.filesystem.read", "local.filesystem.write", "local.process.spawn", "local.evidence"],
  "evidence_type": "lane_a",
  "steps": [
    {
      "id": "load_inbox",
      "action": "load_inbox",
      "description": "Load northstar, skills, constraints, task from inbox",
      "evidence_capture": true
    },
    {
      "id": "compose_prompt",
      "action": "transform",
      "description": "Compose full prompt: northstar + skills + constraints + task + context",
      "operations": ["concatenate_inbox_files", "inject_temporal_context", "inject_previous_failures"]
    },
    {
      "id": "spawn_claude",
      "action": "spawn_process",
      "description": "Spawn claude CLI as subprocess with composed prompt",
      "command": "claude --print --dangerously-skip-permissions",
      "stdin": "{composed_prompt}",
      "timeout_seconds": 300,
      "evidence_capture": true
    },
    {
      "id": "parse_diffs",
      "action": "transform",
      "description": "Parse proposed diffs from Claude output",
      "operations": ["extract_unified_diffs", "validate_paths_allowed", "validate_line_count"]
    },
    {
      "id": "require_approval",
      "action": "require_approval",
      "description": "Show diffs in sidebar. User approves/rejects each file.",
      "display": "diff_viewer",
      "evidence_capture": true
    },
    {
      "id": "write_files",
      "action": "write_approved_files",
      "description": "Write only user-approved diffs to disk",
      "evidence_capture": true
    },
    {
      "id": "build",
      "action": "spawn_process",
      "description": "Compile: autoninja -C out/Solace chrome",
      "command": "autoninja -C source/src/out/Solace chrome",
      "timeout_seconds": 600,
      "on_failure": "revert_all_changes",
      "evidence_capture": true
    },
    {
      "id": "screenshot",
      "action": "screenshot",
      "description": "Launch binary, take screenshot (browser captures, not agent)",
      "command": "source/src/out/Solace/chrome --no-sandbox",
      "wait_seconds": 5,
      "evidence_capture": true
    },
    {
      "id": "seal_evidence",
      "action": "seal_evidence",
      "description": "Hash all artifacts, append to evidence chain",
      "artifacts": ["diffs", "build_log", "screenshot"],
      "hash_algorithm": "sha256"
    },
    {
      "id": "save_to_outbox",
      "action": "save_to_outbox",
      "description": "Write evidence bundle and report to outbox",
      "files": ["evidence.json", "report.md", "diffs/*.patch", "screenshots/*.png", "build-logs/*.log"]
    }
  ],
  "error_handling": {
    "on_build_failure": "revert_and_report",
    "on_approval_rejected": "discard_diffs",
    "on_timeout": "kill_and_report",
    "on_budget_exceeded": "stop_and_report",
    "max_retries": 0
  },
  "budgets": {
    "max_reads": 50,
    "max_writes": 5,
    "max_llm_calls": 20,
    "max_cost_per_run_usd": 0.50,
    "max_screenshots": 3
  }
}
```

## 9. Why Constraints Make It 10x Better

| Without Constraint | With Constraint | Improvement |
|-------------------|----------------|-------------|
| Agent works on any project | Solace Browser only | Deep context, knows every file |
| Agent decides scope | One task, defined acceptance criteria | No drift, no scope creep |
| Agent reviews own code | External review only | No "looks good to me" on own lies |
| Agent runs git | No git access | Can't fabricate evidence trail |
| Agent claims "tests pass" | Build gate + screenshot gate | Binary proof, not text claim |
| Agent changes 50 files | Max 5 files | User can actually review |
| Agent writes 1000 lines | Max 200 lines | Small diffs are correct diffs |
| Agent burns unlimited tokens | Budget per task | Forces efficient solutions |
| Agent picks what to build | Yinyang assigns tasks | Human controls priority |
| Agent reports results | Browser captures evidence | Agent can't control narrative |

## 10. Forbidden States

```
SELF_REVIEW           — Agent cannot review its own code. Ever.
DIRECT_FILE_WRITE     — Agent proposes diffs. Yinyang writes after approval.
UNSCOPED_TASK         — Every task has explicit acceptance criteria.
UNWITNESSED_PASS      — Build gate + screenshot gate. Binary proof.
DRIFT_FROM_TASK       — Single task per session. Cannot expand scope.
GIT_WRITE             — Agent has zero git access. Yinyang commits.
FALLBACK_SILENCE      — If build fails, REVERT. No "fix later."
BUDGET_OVERFLOW       — Hard stop at token/cost limit. No exceptions.
PATH_ESCAPE           — Cannot write outside allowed paths.
NARRATIVE_CONTROL     — Evidence captured by browser, not agent.
```

---

**Paper 57 | Auth: 65537 | Solace Browser Coding App**
*"The agent that built the chains it wears."*
