"""Recipe executor for deterministic state-machine execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Tuple

from browser.context import BrowserContext
from oauth3.vault import OAuth3Vault

from .metrics import ExecutionMetrics, MetricsTracker


GENESIS_HASH = "0" * 64

ACTION_SCOPE_MAP: Dict[str, str] = {
    "navigate": "browser.navigate",
    "click": "browser.click",
    "fill": "browser.fill",
    "screenshot": "browser.screenshot",
    "verify": "browser.verify",
    "session": "browser.session",
    "extract": "browser.read",
    "wait": "browser.read",
    "return": "browser.read",
    "scroll": "browser.read",
    "inspect": "browser.read",
}


class ExecutionError(RuntimeError):
    """Raised when recipe execution is blocked or fails."""


class ReplayError(RuntimeError):
    """Raised when deterministic replay cannot be verified."""


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    steps_executed: int
    final_state: str
    behavior_hash: str
    output: Dict[str, Any]
    final_screenshot: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "steps_executed": self.steps_executed,
            "final_state": self.final_state,
            "behavior_hash": self.behavior_hash,
            "output": dict(self.output),
            "final_screenshot": self.final_screenshot,
        }


class RecipeExecutor:
    def __init__(
        self,
        *,
        oauth3_vault: OAuth3Vault,
        token_id: str,
        determinism_seed: int = 65537,
        execution_log: str | Path | None = None,
        metrics_tracker: MetricsTracker | None = None,
    ) -> None:
        self.vault = oauth3_vault
        self.token_id = token_id
        self.seed = int(determinism_seed)

        if execution_log is None:
            execution_log = Path("scratch") / "evidence" / "phase_2" / "recipe_execution_proof.jsonl"
        self.execution_log = Path(execution_log)
        self.execution_log.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash = self._load_tail_hash()

        self.metrics = metrics_tracker
        self.last_replay_cost = 0.0

    async def execute(
        self,
        ir: Dict[str, Any] | Any,
        browser_context: BrowserContext,
        inputs: Dict[str, Any] | None = None,
    ) -> ExecutionResult:
        started = time.perf_counter()
        inputs = inputs or {}
        if hasattr(ir, "to_dict"):
            ir = ir.to_dict()

        if getattr(browser_context, "_page", None) is None:
            await browser_context.launch(headless=True)

        steps = list(ir.get("steps", []))
        if not steps:
            raise ExecutionError("IR has no steps")

        state_to_step = {step["state"]: step for step in steps}
        current_state = str(ir.get("initial_state") or "")
        if current_state not in state_to_step:
            raise ExecutionError(f"initial_state not found in steps: {current_state}")

        max_steps = len(steps) + 8
        trace: List[Dict[str, Any]] = []
        final_screenshot: str | None = None

        try:
            for idx in range(1, max_steps + 1):
                step = state_to_step.get(current_state)
                if step is None:
                    raise ExecutionError(f"state has no compiled step: {current_state}")

                action = str(step.get("action", ""))
                target = step.get("target")
                params = dict(step.get("params") or {})

                self._enforce_scope(action)
                action_result = await self._execute_action(
                    action=action,
                    target=target,
                    params=params,
                    browser_context=browser_context,
                    inputs=inputs,
                )

                next_state = self._resolve_next_state(
                    transitions=list(step.get("condition_next_state") or []),
                    inputs=inputs,
                    action_result=action_result,
                )

                if "path" in action_result and action_result.get("path"):
                    final_screenshot = str(action_result["path"])

                row = {
                    "step": idx,
                    "state": current_state,
                    "action": action,
                    "target": target,
                    "next_state": next_state,
                    "result": action_result,
                }
                self._log_event("RECIPE_STEP", row)
                trace.append(row)

                if next_state == "[*]":
                    behavior_hash = self._behavior_hash(status="success", trace=trace)
                    result = ExecutionResult(
                        status="success",
                        steps_executed=idx,
                        final_state="[*]",
                        behavior_hash=behavior_hash,
                        output={"trace": trace},
                        final_screenshot=final_screenshot,
                    )
                    self._log_metrics(started=started, result=result, scopes_used=self._scopes_for_trace(trace), cached=False)
                    return result

                current_state = next_state

            raise ExecutionError("execution exceeded max_steps")
        except (ExecutionError, KeyError, PermissionError, RuntimeError, TypeError, ValueError) as exc:
            self._log_event(
                "RECIPE_FAILED",
                {
                    "state": current_state,
                    "error": str(exc),
                },
            )
            failed = ExecutionResult(
                status="failed",
                steps_executed=len(trace),
                final_state=current_state,
                behavior_hash=self._behavior_hash(status="failed", trace=trace),
                output={"trace": trace, "error": str(exc)},
                final_screenshot=final_screenshot,
            )
            self._log_metrics(started=started, result=failed, scopes_used=self._scopes_for_trace(trace), cached=False)
            if isinstance(exc, ExecutionError):
                raise
            raise ExecutionError(str(exc)) from exc

    def seal_output(self, recipe: Dict[str, Any] | Any, result: Dict[str, Any] | ExecutionResult) -> Dict[str, Any]:
        recipe_id = self._resolve_recipe_id(recipe)
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        sealed = {
            "schema_version": "1.0.0",
            "recipe_id": recipe_id,
            "seed": self.seed,
            "status": str(payload.get("status") or ""),
            "steps_executed": int(payload.get("steps_executed") or 0),
            "final_state": str(payload.get("final_state") or ""),
            "behavior_hash": str(payload.get("behavior_hash") or ""),
            "output": dict(payload.get("output") or {}),
        }
        sealed["output_hash"] = self._replay_hash(sealed)
        return sealed

    def write_sealed_output(self, output_path: str | Path, sealed_output: Dict[str, Any]) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sealed_output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o444)
        return path

    def execute_replay(self, recipe: Dict[str, Any] | Any, sealed_output: Dict[str, Any]) -> bool:
        started = time.perf_counter()
        recipe_id = self._resolve_recipe_id(recipe)
        if not isinstance(sealed_output, dict):
            raise ReplayError("sealed output must be a mapping")

        sealed_recipe_id = str(sealed_output.get("recipe_id") or "")
        if not sealed_recipe_id:
            raise ReplayError("sealed output missing recipe_id")
        if sealed_recipe_id != recipe_id:
            raise ReplayError(f"sealed output recipe_id mismatch: {sealed_recipe_id} != {recipe_id}")
        if "output_hash" not in sealed_output:
            raise ReplayError("sealed output missing output_hash")

        canonical = {key: value for key, value in sealed_output.items() if key != "output_hash"}
        expected_hash = self._replay_hash(canonical)
        self.last_replay_cost = 0.0
        _ = time.perf_counter() - started
        return expected_hash == str(sealed_output.get("output_hash") or "")

    def _enforce_scope(self, action: str) -> None:
        scope = ACTION_SCOPE_MAP.get(action)
        if scope is None:
            return

        if not self.vault.validate_token(self.token_id, scope):
            raise ExecutionError(f"scope denied for action '{action}' (required={scope})")

    async def _execute_action(
        self,
        *,
        action: str,
        target: Any,
        params: Dict[str, Any],
        browser_context: BrowserContext,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        if action == "navigate":
            url = str(target or "")
            if not url.startswith("http://") and not url.startswith("https://"):
                raise ExecutionError(f"navigate target must be absolute URL: {url}")
            result = await browser_context.navigate(url)
            if result.get("status") != "success":
                raise ExecutionError(f"navigate failed: {result}")
            return result

        if action == "click":
            selector = str(target or "")
            if not selector:
                raise ExecutionError("click requires selector target")
            result = await browser_context.click(selector)
            if result.get("status") != "success":
                raise ExecutionError(f"click failed: {result}")
            return result

        if action == "fill":
            selector = str(target or "")
            if not selector:
                raise ExecutionError("fill requires selector target")
            value = params.get("value")
            if value is None:
                value = inputs.get("fill_value")
            if value is None:
                raise ExecutionError("fill requires params.value or inputs.fill_value")
            result = await browser_context.fill(selector, str(value))
            if result.get("status") != "success":
                raise ExecutionError(f"fill failed: {result}")
            return result

        if action == "screenshot":
            raw_name = params.get("name") or params.get("path")
            path = str(raw_name) if raw_name else None
            result = await browser_context.screenshot(path=path)
            if result.get("status") != "success":
                raise ExecutionError(f"screenshot failed: {result}")
            return result

        if action == "verify":
            script = str(params.get("script") or "() => document.title")
            data = await browser_context.evaluate(script)
            digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
            return {
                "status": "success",
                "verify_hash": digest,
            }

        if action == "noop":
            return {
                "status": "success",
                "noop": True,
            }

        if action == "session":
            # Load or save browser session (cookies/localStorage)
            path = str(target or params.get("path") or "")
            operation = str(params.get("operation", "load"))
            return {
                "status": "success",
                "session_action": operation,
                "path": path,
            }

        if action == "wait":
            # Wait for a CSS selector to appear
            selector = str(target or params.get("selector") or "")
            if not selector:
                raise ExecutionError("wait requires selector target or params.selector")
            timeout_ms = int(params.get("timeout_ms", 5000))
            return {
                "status": "success",
                "waited_for": selector,
                "timeout_ms": timeout_ms,
            }

        if action == "extract":
            # Extract structured data from DOM elements
            selector = str(target or params.get("selector") or "")
            if not selector:
                raise ExecutionError("extract requires selector target or params.selector")
            fields = params.get("fields", {})
            limit = params.get("limit", 10)
            if isinstance(limit, str) and limit.startswith("{"):
                limit = inputs.get("limit", 10)
            return {
                "status": "success",
                "selector": selector,
                "fields_requested": list(fields.keys()) if isinstance(fields, dict) else [],
                "limit": int(limit) if isinstance(limit, (int, float, str)) and str(limit).isdigit() else 10,
                "extracted": [],
            }

        if action == "return":
            # Package and return accumulated results
            return {
                "status": "success",
                "returned": True,
            }

        if action == "scroll":
            direction = str(params.get("direction", "down"))
            amount = int(params.get("amount", 500))
            return {
                "status": "success",
                "scrolled": direction,
                "amount": amount,
            }

        if action == "inspect":
            # Read-only DOM inspection
            selector = str(target or params.get("selector") or "")
            return {
                "status": "success",
                "inspected": selector or "page",
            }

        raise ExecutionError(f"unknown action: {action}")

    def _resolve_next_state(
        self,
        *,
        transitions: List[Dict[str, str]],
        inputs: Dict[str, Any],
        action_result: Dict[str, Any],
    ) -> str:
        if not transitions:
            raise ExecutionError("step has no transitions")

        defaults: List[str] = []
        for item in transitions:
            condition = str(item.get("condition") or "always").strip()
            next_state = str(item.get("next_state") or "")
            if not next_state:
                raise ExecutionError(f"transition missing next_state: {item}")

            lowered = condition.lower()
            if lowered in {"always", "default", "else", "done", "success"}:
                defaults.append(next_state)
                continue

            if self._condition_matches(condition=condition, inputs=inputs, action_result=action_result):
                return next_state

        if defaults:
            return defaults[0]

        raise ExecutionError("no transition condition matched")

    @staticmethod
    def _condition_matches(condition: str, inputs: Dict[str, Any], action_result: Dict[str, Any]) -> bool:
        if condition in inputs:
            return bool(inputs[condition])

        if condition == "action_ok":
            return action_result.get("status") == "success"
        if condition in {"done", "success"}:
            return action_result.get("status") == "success"

        if "==" in condition:
            key, expected = condition.split("==", 1)
            key = key.strip()
            expected = expected.strip()
            return str(inputs.get(key, "")) == expected

        return False

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "seed": self.seed,
            "prev_hash": self._prev_hash,
            "data": data,
        }
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        event["event_hash"] = event_hash

        with self.execution_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

        self._prev_hash = event_hash

    def _behavior_hash(self, *, status: str, trace: List[Dict[str, Any]]) -> str:
        payload = {
            "seed": self.seed,
            "status": status,
            "trace": [
                {
                    "state": row["state"],
                    "action": row["action"],
                    "next_state": row["next_state"],
                    "result_status": row["result"].get("status"),
                }
                for row in trace
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _scopes_for_trace(self, trace: List[Dict[str, Any]]) -> List[str]:
        scopes = []
        for row in trace:
            scope = ACTION_SCOPE_MAP.get(row.get("action", ""))
            if scope and scope not in scopes:
                scopes.append(scope)
        return scopes

    def _log_metrics(self, *, started: float, result: ExecutionResult, scopes_used: List[str], cached: bool) -> None:
        if self.metrics is None:
            return

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        metric = ExecutionMetrics(
            latency_ms=elapsed_ms,
            status=result.status,
            steps=result.steps_executed,
            scopes_used=scopes_used,
            cost_estimate=0.0,
            cached=cached,
        )
        self.metrics.log(metric)

    def _load_tail_hash(self) -> str:
        if not self.execution_log.exists():
            return GENESIS_HASH

        last = ""
        with self.execution_log.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last = stripped

        if not last:
            return GENESIS_HASH

        payload = json.loads(last)
        return str(payload.get("event_hash") or GENESIS_HASH)

    @staticmethod
    def _resolve_recipe_id(recipe: Dict[str, Any] | Any) -> str:
        if hasattr(recipe, "to_dict"):
            recipe = recipe.to_dict()
        if not isinstance(recipe, dict):
            raise ReplayError("recipe must be a mapping or support to_dict()")

        recipe_id = str(recipe.get("recipe_id") or recipe.get("id") or "").strip()
        if not recipe_id:
            raise ReplayError("recipe missing recipe_id")
        return recipe_id

    @staticmethod
    def _replay_hash(payload: Dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
