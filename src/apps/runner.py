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
import logging
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

logger = logging.getLogger(__name__)


class AppRunnerError(RuntimeError):
    """Raised when the app runner encounters an unrecoverable error."""


# ---------------------------------------------------------------------------
# Platform recipe mapping: app-id → platform recipe directory + recipe file
# Maps app IDs to (platform_dir, recipe_filename) tuples in
# data/default/recipes/{platform_dir}/{recipe_filename}.
# ---------------------------------------------------------------------------
APP_RECIPE_MAP: dict[str, tuple[str, str]] = {
    "github-issue-triage": ("github", "github-issue-triage.json"),
    "linkedin-outreach": ("linkedin", "linkedin-discover-posts.recipe.json"),
    "linkedin-poster": ("linkedin", "linkedin-create-post.recipe.json"),
    "reddit-scanner": ("reddit", "reddit-browse-subreddit.json"),
    "slack-triage": ("slack", "slack-channel-summary.json"),
    "twitter-monitor": ("twitter", "twitter-read-timeline.json"),
    "twitter-poster": ("twitter", "twitter-post-tweet.json"),
}

# Site domain → platform directory name for dynamic resolution
SITE_TO_PLATFORM: dict[str, str] = {
    "github.com": "github",
    "mail.google.com": "gmail",
    "linkedin.com": "linkedin",
    "reddit.com": "reddit",
    "app.slack.com": "slack",
    "x.com": "twitter",
    "news.ycombinator.com": "hackernews",
}


def _is_noop_stub(raw: dict[str, Any]) -> bool:
    """Return True if the recipe is a noop stub (single noop step, no real actions)."""
    steps = raw.get("steps", [])
    if len(steps) != 1:
        return False
    step = steps[0]
    return step.get("action") == "noop"


def _find_project_recipes_root(app_root: Path) -> Path | None:
    """Walk up from app_root to find data/default/recipes/.

    The app_root lives under either:
        <project>/data/default/apps/<app-id>   (committed library)
        ~/.solace/apps/<app-id>                (installed)

    For the installed case we cannot find the project root, so we also
    check a well-known environment location.
    """
    # Case 1: app_root is inside the project tree
    # e.g. /path/to/solace-browser/data/default/apps/gmail-inbox-triage
    # Walk up to find data/default/recipes
    candidate = app_root
    for _ in range(8):
        candidate = candidate.parent
        recipes_dir = candidate / "data" / "default" / "recipes"
        if recipes_dir.is_dir():
            return recipes_dir
    return None


def resolve_recipe_path(
    app_root: Path,
    app_recipe_path: Path,
    *,
    manifest: dict[str, Any] | None = None,
) -> Path:
    """Resolve the effective recipe path for an app.

    Resolution order:
        1. If the app recipe.json has a ``recipe_ref`` field, resolve it
           relative to data/default/recipes/.
        2. If the app recipe is a noop stub, look up APP_RECIPE_MAP for
           a known platform recipe.
        3. If the app recipe is a noop stub and not in APP_RECIPE_MAP,
           attempt dynamic resolution from the manifest site field:
           site → platform dir → scan for matching recipe file.
        4. Otherwise return the original app recipe path (it has real steps).

    Args:
        app_root: The app directory (e.g. ~/.solace/apps/github-issue-triage).
        app_recipe_path: Path to the app's recipe.json.
        manifest: Optional pre-loaded manifest dict.

    Returns:
        Path to the recipe file to use for compilation.

    Raises:
        AppRunnerError: If recipe_ref points to a nonexistent file.
    """
    raw = json.loads(app_recipe_path.read_text(encoding="utf-8"))

    # --- 1. Explicit recipe_ref ---
    recipe_ref = raw.get("recipe_ref")
    if recipe_ref:
        recipes_root = _find_project_recipes_root(app_root)
        if recipes_root is None:
            raise AppRunnerError(
                f"App '{app_root.name}' has recipe_ref '{recipe_ref}' "
                "but cannot locate data/default/recipes/"
            )
        resolved = (recipes_root / recipe_ref).resolve()
        if not resolved.is_file():
            raise AppRunnerError(
                f"recipe_ref '{recipe_ref}' resolved to '{resolved}' which does not exist"
            )
        logger.info("Resolved recipe_ref '%s' → %s", recipe_ref, resolved)
        return resolved

    # --- 2. Noop stub → static map ---
    if _is_noop_stub(raw):
        app_id = raw.get("id", app_root.name)
        mapped = APP_RECIPE_MAP.get(app_id)
        if mapped:
            recipes_root = _find_project_recipes_root(app_root)
            if recipes_root is not None:
                platform_dir, recipe_file = mapped
                candidate = recipes_root / platform_dir / recipe_file
                # Also try top-level recipes dir for .recipe.json files
                if not candidate.is_file():
                    candidate = recipes_root / recipe_file
                if candidate.is_file():
                    logger.info(
                        "Noop stub '%s' → platform recipe %s",
                        app_id,
                        candidate,
                    )
                    return candidate

        # --- 3. Dynamic resolution from manifest site ---
        if manifest:
            site = str(manifest.get("site", ""))
            platform = SITE_TO_PLATFORM.get(site)
            if platform:
                recipes_root = _find_project_recipes_root(app_root)
                if recipes_root is not None:
                    platform_recipe_dir = recipes_root / platform
                    if platform_recipe_dir.is_dir():
                        # Look for a recipe whose name contains the app_id
                        # or the first recipe in the platform directory
                        best = _find_best_platform_recipe(
                            platform_recipe_dir, app_id
                        )
                        if best:
                            logger.info(
                                "Noop stub '%s' → dynamic platform recipe %s",
                                app_id,
                                best,
                            )
                            return best

        logger.debug(
            "Noop stub '%s' has no platform recipe available, using stub",
            raw.get("id", app_root.name),
        )

    # --- 4. Real recipe — use as-is ---
    return app_recipe_path


def _find_best_platform_recipe(platform_dir: Path, app_id: str) -> Path | None:
    """Find the best-matching recipe in a platform directory for an app ID.

    Matching strategy:
        1. Exact stem match: app_id matches recipe filename stem.
        2. Partial keyword match: significant parts of app_id appear in filename.
        3. First recipe in the directory as last resort.
    """
    recipes = sorted(
        p for p in platform_dir.iterdir()
        if p.is_file() and p.suffix == ".json"
    )
    if not recipes:
        return None

    # Exact match on stem
    for recipe_path in recipes:
        stem = recipe_path.stem.replace(".recipe", "")
        if stem == app_id:
            return recipe_path

    # Keyword overlap: split app_id on hyphens and find recipes
    # containing the most keywords
    app_keywords = set(app_id.split("-"))
    # Remove generic words
    app_keywords -= {"the", "a", "an", "and", "or"}

    best_score = 0
    best_path: Path | None = None
    for recipe_path in recipes:
        stem = recipe_path.stem.replace(".recipe", "")
        recipe_keywords = set(stem.split("-"))
        overlap = len(app_keywords & recipe_keywords)
        if overlap > best_score:
            best_score = overlap
            best_path = recipe_path

    if best_score >= 1:
        return best_path

    return None


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

    # 2. Load and compile recipe (with platform recipe resolution)
    app_recipe_path = app_root / "recipe.json"
    if not app_recipe_path.exists():
        raise AppRunnerError(f"App '{app_id}' missing recipe.json")
    manifest = io_manager.read_manifest(app_id)
    recipe_path = resolve_recipe_path(
        app_root, app_recipe_path, manifest=manifest
    )
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
    # manifest was already loaded above during recipe resolution.
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
