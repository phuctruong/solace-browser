#!/usr/bin/env python3
"""Solace Browser Coder — Companion App Runner

Wraps Claude Code CLI as a chained subprocess.
Reads task from inbox, composes prompt with all uplifts,
spawns claude, parses diffs, shows for approval.

This script does NOT need the browser. It runs standalone.
When Yinyang sidebar is built, it replaces this script's
approval UI with the native sidebar.

Usage:
    python run.py                    # Interactive: pick task from inbox
    python run.py task.md            # Run specific task file
    python run.py --test             # Dry run: compose prompt, don't spawn claude
"""

import json
import hashlib
import subprocess
import sys
import os
import re
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(__file__).parent
INBOX = APP_DIR / "inbox"
OUTBOX = APP_DIR / "outbox"
PROJECT_ROOT = Path("/home/phuc/projects/solace-browser")

def load_inbox_file(path: Path) -> str:
    """Load a single inbox file."""
    if not path.exists():
        return ""
    return path.read_text().strip()

def load_budget() -> dict:
    """Load and return budget, checking limits."""
    budget_path = APP_DIR / "budget.json"
    budget = json.loads(budget_path.read_text())
    if budget["current_usage"]["tasks_today"] >= budget["daily_max_tasks"]:
        print(f"BLOCKED: Daily task limit reached ({budget['daily_max_tasks']})")
        sys.exit(1)
    if budget["current_usage"]["cost_today_usd"] >= budget["daily_max_cost_usd"]:
        print(f"BLOCKED: Daily cost limit reached (${budget['daily_max_cost_usd']})")
        sys.exit(1)
    return budget

def load_config() -> dict:
    """Load app config."""
    import yaml
    config_path = INBOX / "conventions" / "config.yaml"
    if config_path.exists():
        return yaml.safe_load(config_path.read_text())
    return {}

def compose_prompt(task_content: str) -> str:
    """Compose full prompt from inbox files. Every uplift injected here."""
    parts = []

    # P46 NORTHSTAR — first line always
    northstar = load_inbox_file(INBOX / "northstar.md")
    if northstar:
        parts.append(northstar)

    # P2 + P3 + P8 + P12 + P14 + P16 + P17 + P18 + P19 + P47 — system prompt
    system_prompt = load_inbox_file(INBOX / "prompts" / "system-prompt.md")
    if system_prompt:
        parts.append(system_prompt)

    # P4 Skills — load all from inbox/skills/
    skills_dir = INBOX / "skills"
    if skills_dir.exists():
        for skill_file in sorted(skills_dir.glob("*.md")):
            skill = skill_file.read_text().strip()
            if skill:
                parts.append(f"=== SKILL: {skill_file.stem} ===\n{skill}")

    # P13 Constraints — safety policy
    safety = load_inbox_file(INBOX / "policies" / "safety.yaml")
    if safety:
        parts.append(f"=== SAFETY POLICY ===\n{safety}")

    # P6 Allowed paths
    paths = load_inbox_file(INBOX / "policies" / "allowed-paths.yaml")
    if paths:
        parts.append(f"=== ALLOWED PATHS ===\n{paths}")

    # P22 LEAK/Oracle — previous failures
    failures_dir = INBOX / "previous-failures"
    if failures_dir.exists():
        for fail_file in sorted(failures_dir.glob("*.md"))[-3:]:
            parts.append(f"=== PREVIOUS FAILURE ===\n{fail_file.read_text().strip()}")

    # P15 Few-shot exemplars
    examples_dir = INBOX / "examples"
    if examples_dir.exists():
        for ex_file in sorted(examples_dir.glob("*.md"))[:2]:
            parts.append(f"=== EXAMPLE ===\n{ex_file.read_text().strip()}")

    # P9 Knowledge — context files
    context_dir = INBOX / "context"
    if context_dir.exists():
        for ctx_file in sorted(context_dir.glob("*"))[:5]:
            if ctx_file.is_file():
                content = ctx_file.read_text().strip()[:5000]
                parts.append(f"=== CONTEXT: {ctx_file.name} ===\n{content}")

    # P20 Temporal — task with current state
    parts.append(f"=== TASK ===\n{task_content}")

    return "\n\n---\n\n".join(parts)

def parse_diffs(output: str) -> list[dict]:
    """Extract unified diffs from Claude output."""
    diffs = []
    # Match diff blocks between ``` markers or --- +++ patterns
    diff_pattern = re.compile(
        r'(?:^---\s+a/(.+?)\n\+\+\+\s+b/(.+?)\n(?:@@.*\n(?:[ +-].*\n)*))',
        re.MULTILINE
    )
    for match in diff_pattern.finditer(output):
        diffs.append({
            "old_path": match.group(1),
            "new_path": match.group(2),
            "content": match.group(0),
        })

    # Also try to find diffs in code blocks
    code_blocks = re.findall(r'```(?:diff)?\n(.*?)```', output, re.DOTALL)
    for block in code_blocks:
        if '---' in block and '+++' in block:
            lines = block.strip().split('\n')
            for i, line in enumerate(lines):
                if line.startswith('--- '):
                    old_path = line.replace('--- a/', '').replace('--- ', '').strip()
                    if i + 1 < len(lines) and lines[i+1].startswith('+++ '):
                        new_path = lines[i+1].replace('+++ b/', '').replace('+++ ', '').strip()
                        diffs.append({
                            "old_path": old_path,
                            "new_path": new_path,
                            "content": block.strip(),
                        })
                        break

    return diffs

def validate_paths(diffs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Check diffs against allowed-paths policy. Returns (allowed, blocked)."""
    import yaml
    policy_path = INBOX / "policies" / "allowed-paths.yaml"
    if not policy_path.exists():
        return diffs, []

    policy = yaml.safe_load(policy_path.read_text())
    write_patterns = policy.get("write", [])
    forbidden_patterns = policy.get("forbidden", [])

    allowed = []
    blocked = []

    for diff in diffs:
        path = diff["new_path"]
        is_forbidden = any(
            _glob_match(path, pattern) for pattern in forbidden_patterns
        )
        is_allowed = any(
            _glob_match(path, pattern) for pattern in write_patterns
        )
        if is_forbidden or not is_allowed:
            blocked.append(diff)
        else:
            allowed.append(diff)

    return allowed, blocked

def _glob_match(path: str, pattern: str) -> bool:
    """Simple glob matching for path policies."""
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path.startswith(prefix)
    return path == pattern

def show_diff_for_approval(diff: dict) -> bool:
    """Show a diff and ask for approval. Returns True if approved."""
    print(f"\n{'='*60}")
    print(f"FILE: {diff['new_path']}")
    print(f"{'='*60}")
    print(diff['content'])
    print(f"{'='*60}")
    while True:
        response = input("APPROVE this change? [y/n/q]: ").strip().lower()
        if response == 'y':
            return True
        if response in ('n', 'q'):
            return False

def sha256_hash(content: str) -> str:
    """SHA-256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()

def save_evidence(task_name: str, diffs: list[dict], claude_output: str, approved: list[dict]):
    """Save evidence bundle to outbox."""
    now = datetime.now(timezone.utc)
    run_id = f"run-{now.strftime('%Y%m%d-%H%M%S')}"
    run_dir = OUTBOX / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save approved diffs
    diff_dir = OUTBOX / "diffs"
    diff_dir.mkdir(parents=True, exist_ok=True)
    for i, diff in enumerate(approved):
        diff_path = diff_dir / f"{run_id}-{i}.patch"
        diff_path.write_text(diff["content"])

    # Evidence bundle
    evidence = {
        "app_id": "solace-browser-coder",
        "run_id": run_id,
        "task": task_name,
        "timestamp": now.isoformat(),
        "status": "APPROVED" if approved else "REJECTED",
        "files_changed": len(approved),
        "total_proposed": len(diffs),
        "diffs_hash": sha256_hash(json.dumps([d["content"] for d in approved])),
        "output_hash": sha256_hash(claude_output),
    }

    evidence_path = run_dir / f"{run_id}.json"
    evidence_path.write_text(json.dumps(evidence, indent=2))
    print(f"\nEvidence saved: {evidence_path}")
    return evidence

def update_budget(cost: float):
    """Update budget after task completion."""
    budget_path = APP_DIR / "budget.json"
    budget = json.loads(budget_path.read_text())
    budget["current_usage"]["tasks_today"] += 1
    budget["current_usage"]["cost_today_usd"] += cost
    budget["remaining_runs"] -= 1
    budget_path.write_text(json.dumps(budget, indent=2))

def run_task(task_path: Path, dry_run: bool = False):
    """Execute a single coding task through the chained pipeline."""
    print(f"\n{'#'*60}")
    print(f"# SOLACE BROWSER CODER — Task: {task_path.name}")
    print(f"{'#'*60}")

    # Step 1: Load budget, check limits
    budget = load_budget()
    print(f"Budget: {budget['remaining_runs']} runs left, ${budget['daily_max_cost_usd'] - budget['current_usage']['cost_today_usd']:.2f} remaining today")

    # Step 2: Load task
    task_content = task_path.read_text().strip()
    print(f"Task loaded: {len(task_content)} chars")

    # Step 3: Compose prompt (all uplifts injected)
    prompt = compose_prompt(task_content)
    print(f"Prompt composed: {len(prompt)} chars ({len(prompt.split())} words)")

    if dry_run:
        print("\n=== DRY RUN — Composed Prompt ===")
        print(prompt)
        print("=== END DRY RUN ===")
        return

    # Step 4: Spawn Claude Code CLI
    print("\nSpawning Claude Code CLI...")
    try:
        result = subprocess.run(
            ["claude", "--print", "--dangerously-skip-permissions"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PROJECT_ROOT),
        )
        claude_output = result.stdout
        if result.returncode != 0:
            print(f"Claude CLI error (exit {result.returncode}):")
            print(result.stderr[:500])
            save_evidence(task_path.stem, [], claude_output, [])
            return
    except subprocess.TimeoutExpired:
        print("BLOCKED: Claude CLI timed out (300s)")
        return
    except FileNotFoundError:
        print("BLOCKED: 'claude' CLI not found in PATH")
        return

    print(f"Claude output: {len(claude_output)} chars")

    # Step 5: Parse diffs
    diffs = parse_diffs(claude_output)
    if not diffs:
        print("\nNo diffs found in Claude output. Raw output:")
        print(claude_output[:2000])
        save_evidence(task_path.stem, [], claude_output, [])
        return

    print(f"Found {len(diffs)} proposed diff(s)")

    # Step 6: Validate paths
    allowed, blocked = validate_paths(diffs)
    if blocked:
        print(f"\nBLOCKED {len(blocked)} diff(s) — forbidden paths:")
        for d in blocked:
            print(f"  BLOCKED: {d['new_path']}")

    if not allowed:
        print("No diffs in allowed paths. Task blocked.")
        save_evidence(task_path.stem, diffs, claude_output, [])
        return

    # Step 7: Show diffs for approval
    approved = []
    for diff in allowed:
        if show_diff_for_approval(diff):
            approved.append(diff)
        else:
            print(f"  REJECTED: {diff['new_path']}")

    if not approved:
        print("\nAll diffs rejected. Nothing to write.")
        save_evidence(task_path.stem, diffs, claude_output, [])
        return

    # Step 8: Save evidence
    evidence = save_evidence(task_path.stem, diffs, claude_output, approved)

    # Step 9: Update budget
    update_budget(0.10)  # Estimated cost per task

    print(f"\n{'='*60}")
    print(f"TASK COMPLETE — {len(approved)} file(s) approved")
    print(f"Evidence: {evidence['run_id']}")
    print(f"Next: User writes approved diffs, runs build, takes screenshot")
    print(f"{'='*60}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Dry run with a sample task
        sample_task = INBOX / "context" / "sample-task.md"
        if not sample_task.exists():
            sample_task = Path("/dev/stdin")
            print("No sample task. Enter task (Ctrl+D to end):")
        run_task(sample_task, dry_run=True)
    elif len(sys.argv) > 1:
        task_path = Path(sys.argv[1])
        if not task_path.exists():
            task_path = INBOX / sys.argv[1]
        if not task_path.exists():
            print(f"Task file not found: {sys.argv[1]}")
            sys.exit(1)
        run_task(task_path)
    else:
        # List available tasks
        task_files = sorted(INBOX.glob("task-*.md"))
        if not task_files:
            print("No tasks in inbox. Create inbox/task-001-*.md")
            sys.exit(0)
        print("Available tasks:")
        for i, tf in enumerate(task_files):
            print(f"  [{i+1}] {tf.name}")
        choice = input("Pick task number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(task_files):
            run_task(task_files[int(choice) - 1])

if __name__ == "__main__":
    main()
