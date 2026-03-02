"""Local app recipe runner — wires lifecycle, compiler, executor, and budget gates.

Runs a local app recipe through the full Software 5.0 execution lifecycle:
    TRIGGER → BUDGET_CHECK → PREVIEW → APPROVAL → EXECUTE → SEAL

Components wired:
    - InboxOutboxManager: loads manifest, recipe, budget, writes runs
    - BudgetGateChecker: fail-closed gates B1-B6
    - RecipeCompiler: compile_from_steps (JSON) or compile_mermaid (FSM)
    - RecipeExecutor: deterministic state-machine execution
    - ExecutionLifecycleManager: 13-state diagram-14 lifecycle
    - BrowserContext: mock (preview) or playwright (execute)

Auth: 65537 | Rung: 641
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from budget_gates import BudgetGateChecker
from browser.context import BrowserContext
from execution_lifecycle import ApprovalDecision, ExecutionLifecycleManager, LifecycleResult
from inbox_outbox import InboxOutboxManager
from oauth3.vault import OAuth3Vault
from recipes.recipe_compiler import compile_from_steps, compile_mermaid, RecipeIR
from recipes.recipe_executor import RecipeExecutor
from recipes.recipe_parser import parse_deterministic


class AppRunnerError(RuntimeError):
    """Raised when the app runner encounters an unrecoverable error."""


def load_and_compile_recipe(app_root: Path, recipe_path: Path) -> RecipeIR:
    """Load a recipe file and compile it to IR.

    Handles both Mermaid FSM recipes and linear JSON steps recipes.
    """
    raw = json.loads(recipe_path.read_text(encoding="utf-8"))
    mermaid_fsm = raw.get("mermaid_fsm")
    if mermaid_fsm:
        recipe_id = str(raw.get("id") or raw.get("recipe_id") or recipe_path.stem)
        return compile_mermaid(mermaid_fsm, recipe_id=recipe_id)

    dag, _dag_hash = parse_deterministic(recipe_path)
    return compile_from_steps(
        recipe_id=dag.recipe_id,
        steps=list(dag.steps),
        scopes=dag.scopes,
        version=dag.version,
    )


def run_app(
    app_id: str,
    *,
    trigger: str = "manual",
    approval: ApprovalDecision = ApprovalDecision.APPROVE,
    vault: OAuth3Vault,
    token_id: str,
    solace_home: str | Path | None = None,
    risk_level: str = "low",
    user_id: str = "guest",
    inputs: dict[str, Any] | None = None,
    sleep_fn: Any = None,
    now_fn: Any = None,
) -> LifecycleResult:
    """Run a local app recipe through the full execution lifecycle.

    Args:
        app_id: App identifier (e.g. 'gmail-inbox-triage').
        trigger: What triggered the run ('manual', 'schedule', 'cross-app').
        approval: User's approval decision.
        vault: OAuth3Vault for scope enforcement.
        token_id: Issued token ID with required scopes.
        solace_home: Path to ~/.solace root (default: ~/.solace).
        risk_level: 'low', 'medium', 'high', or 'critical'.
        user_id: User identifier for e-sign.
        inputs: Runtime inputs passed to the recipe executor.
        sleep_fn: Optional sleep function (for testing).
        now_fn: Optional datetime function (for testing).

    Returns:
        LifecycleResult with run_id, state, preview, evidence path.

    Raises:
        AppRunnerError: On compilation or loading errors.
    """
    inputs = inputs or {}
    io_manager = InboxOutboxManager(solace_home=solace_home)

    # 1. Validate app structure
    io_manager.validate_inbox(app_id)
    app_root = io_manager.resolve_app_root(app_id)

    # 2. Load and compile recipe
    recipe_path = app_root / "recipe.json"
    if not recipe_path.exists():
        raise AppRunnerError(f"App '{app_id}' missing recipe.json")
    ir = load_and_compile_recipe(app_root, recipe_path)

    # 3. Build preview callback (mock browser — no real execution)
    def preview_callback(context: dict[str, Any]) -> dict[str, Any]:
        preview_browser = BrowserContext(
            oauth3_vault=vault,
            token_id=token_id,
            evidence_log=app_root / "outbox" / "runs" / "preview_events.jsonl",
            seed=65537,
        )
        preview_executor = RecipeExecutor(
            oauth3_vault=vault,
            token_id=token_id,
            determinism_seed=65537,
            execution_log=app_root / "outbox" / "runs" / "preview_proof.jsonl",
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                preview_executor.execute(ir.to_dict(), preview_browser, inputs)
            )
        finally:
            loop.close()

        step_summaries = [
            f"{row.get('action', '?')} → {row.get('next_state', '?')}"
            for row in result.output.get("trace", [])
        ]
        return {
            "preview": f"Will execute {result.steps_executed} steps: {', '.join(step_summaries)}",
            "actions": result.output.get("trace", []),
        }

    # 4. Build execute callback (real browser for production)
    def execute_callback(sealed_preview: dict[str, Any]) -> dict[str, Any]:
        run_id = sealed_preview.get("run_id", "unknown")
        exec_browser = BrowserContext(
            oauth3_vault=vault,
            token_id=token_id,
            evidence_log=app_root / "outbox" / "runs" / run_id / "browser_events.jsonl",
            seed=65537,
        )
        exec_executor = RecipeExecutor(
            oauth3_vault=vault,
            token_id=token_id,
            determinism_seed=65537,
            execution_log=app_root / "outbox" / "runs" / run_id / "execution_proof.jsonl",
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                exec_executor.execute(ir.to_dict(), exec_browser, inputs)
            )
        finally:
            loop.close()

        # Seal and persist output
        recipe_raw = json.loads(recipe_path.read_text(encoding="utf-8"))
        sealed = exec_executor.seal_output(recipe_raw, result)
        sealed_path = app_root / "outbox" / "runs" / run_id / "sealed_output.json"
        exec_executor.write_sealed_output(sealed_path, sealed)

        return {
            "status": result.status,
            "actions_summary": f"{result.steps_executed} steps executed",
            "cost_usd": 0.0,
        }

    # 5. Build budget check
    # B3 gate expects trigger to contain the target domain (e.g. "mail.google.com:manual").
    # Read the manifest site field to build the domain-prefixed trigger.
    manifest = io_manager.read_manifest(app_id)
    site_domain = str(manifest.get("site", ""))

    def budget_check(context: dict[str, Any]) -> dict[str, Any]:
        checker = BudgetGateChecker(io_manager.apps_root)
        budget_trigger = f"{site_domain}:{trigger}" if site_domain else trigger
        return checker.check_all({
            "app_id": app_id,
            "trigger": budget_trigger,
            "risk_level": risk_level,
        })

    # 6. Run lifecycle
    lifecycle_kwargs: dict[str, Any] = {"solace_home": solace_home}
    if sleep_fn is not None:
        lifecycle_kwargs["sleep_fn"] = sleep_fn
    if now_fn is not None:
        lifecycle_kwargs["now_fn"] = now_fn
    lifecycle = ExecutionLifecycleManager(**lifecycle_kwargs)

    return lifecycle.run(
        app_id=app_id,
        trigger=trigger,
        approval_decision=approval,
        preview_callback=preview_callback,
        execute_callback=execute_callback,
        budget_check=budget_check,
        risk_level=risk_level,
        user_id=user_id,
    )
