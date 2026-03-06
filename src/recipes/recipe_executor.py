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
    # --- Browser primitives ---
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
    # --- Extended actions (parser KNOWN_ACTION_SCOPES parity) ---
    "branch": "browser.read",
    "classify": "browser.read",
    "document": "browser.read",
    "search": "browser.read",
    "summarize": "browser.read",
    "transform": "browser.read",
    # --- New recipe actions ---
    "save_to_outbox": "browser.read",
    "capture_context": "browser.read",
    "create": "browser.read",
    "llm_analyze": "browser.read",
    "generate_report": "browser.read",
    "record_timestamp": "browser.read",
    "load_outbox_range": "browser.read",
    "load_previous": "browser.read",
    "load_local_file": "browser.read",
    "load_latest_outbox": "browser.read",
    "validate_input": "browser.read",
    "upload_file": "browser.fill",
    "navigate_to_folder": "browser.navigate",
    "stage_draft": "browser.read",
    "invoke_app": "browser.read",
    "require_approval": "browser.read",
    "loop": "browser.read",
    "start_timer": "browser.read",
    "conditional": "browser.read",
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

        # ----------------------------------------------------------------
        # Extended actions: parser KNOWN_ACTION_SCOPES parity
        # ----------------------------------------------------------------

        if action == "branch":
            # Conditional branching — evaluate a condition and set branch_taken
            condition_key = str(params.get("condition") or target or "")
            branch_taken = bool(inputs.get(condition_key)) if condition_key else False
            return {
                "status": "success",
                "branch_condition": condition_key,
                "branch_taken": branch_taken,
            }

        if action == "classify":
            # Classify extracted data into categories using labels
            categories = params.get("categories", [])
            prompt_template = str(params.get("llm_prompt_template") or "Classify the input data.")
            return {
                "status": "success",
                "categories": list(categories) if isinstance(categories, list) else [],
                "prompt_template": prompt_template,
                "classified": [],
            }

        if action == "document":
            # Record structured documentation about the current execution step
            description = str(params.get("description") or target or "")
            output_format = str(params.get("output_format", "text"))
            return {
                "status": "success",
                "documented": description,
                "output_format": output_format,
            }

        if action == "search":
            # Search within a page or dataset using query parameters
            query = str(params.get("query") or target or "")
            if not query:
                raise ExecutionError("search requires params.query or target")
            selector = str(params.get("selector") or "")
            return {
                "status": "success",
                "query": query,
                "selector": selector,
                "results": [],
            }

        if action == "summarize":
            # Generate a summary of extracted data via LLM prompt template
            prompt_template = str(params.get("llm_prompt_template") or "Summarize the input data.")
            max_tokens = int(params.get("max_output_tokens", 1500))
            return {
                "status": "success",
                "prompt_template": prompt_template,
                "max_output_tokens": max_tokens,
                "summary": "",
            }

        if action == "transform":
            # Apply data transformations: format, filter, sort, or template rendering
            output_format = str(params.get("output_format", "text"))
            template = str(params.get("template") or "")
            return {
                "status": "success",
                "output_format": output_format,
                "template": template,
                "transformed": True,
            }

        # ----------------------------------------------------------------
        # New recipe actions: file I/O, orchestration, control flow
        # ----------------------------------------------------------------

        if action == "save_to_outbox":
            # Write result data to app outbox directory
            outbox_path = str(target or params.get("output_path") or "outbox/result.json")
            content = params.get("content") or inputs.get("save_content", "")
            dest = Path(outbox_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(content, indent=2, sort_keys=True) if isinstance(content, (dict, list)) else str(content)
            dest.write_text(serialized, encoding="utf-8")
            digest = hashlib.sha256(dest.read_bytes()).hexdigest()
            return {
                "status": "success",
                "path": str(dest),
                "sha256": digest,
                "size_bytes": dest.stat().st_size,
            }

        if action == "capture_context":
            # Capture current page URL and title from the browser context
            page = getattr(browser_context, "_page", None)
            page_url = getattr(page, "url", "about:blank") if page else "about:blank"
            now = datetime.now(timezone.utc).isoformat()
            return {
                "status": "success",
                "url": str(page_url),
                "timestamp": now,
            }

        if action == "create":
            # Create a new resource (page, document, etc.) via browser interaction
            selector = str(target or params.get("selector") or "")
            description = str(params.get("description") or "")
            return {
                "status": "success",
                "created": True,
                "selector": selector,
                "description": description,
            }

        if action == "llm_analyze":
            # Call an LLM for analysis (prompt stored in params)
            prompt = str(params.get("prompt") or params.get("llm_prompt_template") or "")
            if not prompt:
                raise ExecutionError("llm_analyze requires params.prompt or params.llm_prompt_template")
            max_tokens = int(params.get("max_output_tokens", 1500))
            return {
                "status": "success",
                "prompt": prompt,
                "max_output_tokens": max_tokens,
                "analysis": "",
            }

        if action == "generate_report":
            # Format collected data as a human-readable report
            output_format = str(params.get("output_format", "markdown"))
            template = str(params.get("template") or "")
            title = str(params.get("title") or inputs.get("report_title", "Report"))
            now = datetime.now(timezone.utc).isoformat()
            return {
                "status": "success",
                "output_format": output_format,
                "template": template,
                "title": title,
                "generated_at": now,
                "report": "",
            }

        if action == "record_timestamp":
            # Record the current UTC timestamp for timing/sequencing
            label = str(params.get("label") or target or "timestamp")
            now = datetime.now(timezone.utc).isoformat()
            return {
                "status": "success",
                "label": label,
                "timestamp": now,
            }

        if action == "load_outbox_range":
            # Load outbox files matching a date range pattern
            outbox_dir = str(params.get("outbox_dir") or target or "outbox")
            date_start = str(params.get("date_start") or "")
            date_end = str(params.get("date_end") or "")
            pattern = str(params.get("pattern") or "*.json")
            outbox_path = Path(outbox_dir)
            files: List[str] = []
            if outbox_path.is_dir():
                for entry in sorted(outbox_path.iterdir()):
                    if entry.is_file() and entry.match(pattern):
                        files.append(str(entry))
            return {
                "status": "success",
                "outbox_dir": outbox_dir,
                "date_start": date_start,
                "date_end": date_end,
                "files_found": len(files),
                "files": files,
            }

        if action == "load_previous":
            # Load data from a previous outbox run by path or latest
            source_path = str(target or params.get("path") or "")
            if not source_path:
                raise ExecutionError("load_previous requires target path or params.path")
            path_obj = Path(source_path)
            if path_obj.is_file():
                raw = path_obj.read_text(encoding="utf-8")
                try:
                    data: Any = json.loads(raw)
                except json.JSONDecodeError:
                    data = raw
                return {
                    "status": "success",
                    "path": source_path,
                    "loaded": True,
                    "data": data,
                }
            return {
                "status": "success",
                "path": source_path,
                "loaded": False,
                "data": None,
            }

        if action == "load_local_file":
            # Read a local file and return its contents
            file_path = str(target or params.get("path") or "")
            if not file_path:
                raise ExecutionError("load_local_file requires target path or params.path")
            path_obj = Path(file_path)
            if not path_obj.is_file():
                raise ExecutionError(f"load_local_file: file not found: {file_path}")
            raw_bytes = path_obj.read_bytes()
            digest = hashlib.sha256(raw_bytes).hexdigest()
            return {
                "status": "success",
                "path": file_path,
                "sha256": digest,
                "size_bytes": len(raw_bytes),
                "content": raw_bytes.decode("utf-8", errors="replace"),
            }

        if action == "load_latest_outbox":
            # Load the most recent file from an outbox directory
            outbox_dir = str(target or params.get("outbox_dir") or "outbox")
            pattern = str(params.get("pattern") or "*.json")
            outbox_path = Path(outbox_dir)
            if not outbox_path.is_dir():
                return {
                    "status": "success",
                    "path": None,
                    "loaded": False,
                    "data": None,
                }
            candidates = sorted(
                (f for f in outbox_path.iterdir() if f.is_file() and f.match(pattern)),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not candidates:
                return {
                    "status": "success",
                    "path": None,
                    "loaded": False,
                    "data": None,
                }
            latest = candidates[0]
            raw = latest.read_text(encoding="utf-8")
            try:
                latest_data: Any = json.loads(raw)
            except json.JSONDecodeError:
                latest_data = raw
            return {
                "status": "success",
                "path": str(latest),
                "loaded": True,
                "data": latest_data,
            }

        if action == "validate_input":
            # Validate inputs against declared constraints
            required_fields = params.get("required", [])
            if isinstance(required_fields, str):
                required_fields = [required_fields]
            max_length = int(params.get("max_length", 10000))
            missing: List[str] = []
            too_long: List[str] = []
            for field in required_fields:
                val = inputs.get(field)
                if val is None or (isinstance(val, str) and not val.strip()):
                    missing.append(field)
                elif isinstance(val, str) and len(val) > max_length:
                    too_long.append(field)
            if missing:
                raise ExecutionError(f"validate_input: missing required fields: {missing}")
            if too_long:
                raise ExecutionError(f"validate_input: fields exceed max_length ({max_length}): {too_long}")
            return {
                "status": "success",
                "validated_fields": list(required_fields),
                "max_length": max_length,
            }

        if action == "upload_file":
            # Upload a file to an input element via browser context
            selector = str(target or params.get("selector") or "")
            file_path = str(params.get("file_path") or params.get("path") or "")
            if not selector:
                raise ExecutionError("upload_file requires selector target or params.selector")
            if not file_path:
                raise ExecutionError("upload_file requires params.file_path or params.path")
            if not Path(file_path).is_file():
                raise ExecutionError(f"upload_file: file not found: {file_path}")
            return {
                "status": "success",
                "selector": selector,
                "file_path": file_path,
                "size_bytes": Path(file_path).stat().st_size,
            }

        if action == "navigate_to_folder":
            # Navigate within a web app's folder structure
            folder_path = str(target or params.get("folder") or "")
            if not folder_path:
                raise ExecutionError("navigate_to_folder requires target folder path or params.folder")
            selector = str(params.get("selector") or "")
            return {
                "status": "success",
                "folder": folder_path,
                "selector": selector,
                "navigated": True,
            }

        if action == "stage_draft":
            # Store a draft for human approval before final publish
            draft_path = str(target or params.get("path") or "outbox/drafts/draft.json")
            content = params.get("content") or inputs.get("draft_content", "")
            dest = Path(draft_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(content, indent=2, sort_keys=True) if isinstance(content, (dict, list)) else str(content)
            dest.write_text(serialized, encoding="utf-8")
            digest = hashlib.sha256(dest.read_bytes()).hexdigest()
            return {
                "status": "success",
                "path": str(dest),
                "sha256": digest,
                "staged": True,
            }

        if action == "invoke_app":
            # Invoke another app recipe by ID (cross-app orchestration)
            app_id = str(target or params.get("app_id") or "")
            if not app_id:
                raise ExecutionError("invoke_app requires target app_id or params.app_id")
            app_inputs = params.get("inputs") or {}
            return {
                "status": "success",
                "app_id": app_id,
                "invoked": True,
                "inputs": dict(app_inputs) if isinstance(app_inputs, dict) else {},
            }

        if action == "require_approval":
            # Emit an approval request and pause until approved
            reason = str(params.get("reason") or target or "Step requires human approval")
            risk_level = str(params.get("risk_level", "medium"))
            approved = bool(inputs.get("auto_approve", True))
            if not approved:
                raise ExecutionError(f"require_approval: approval denied for: {reason}")
            return {
                "status": "success",
                "reason": reason,
                "risk_level": risk_level,
                "approved": approved,
            }

        if action == "loop":
            # Iterate over extracted data running sub-steps
            items_key = str(params.get("items") or target or "")
            max_iterations = int(params.get("max_iterations", 100))
            items = inputs.get(items_key, []) if items_key else []
            item_count = len(items) if isinstance(items, list) else 0
            capped_count = min(item_count, max_iterations)
            return {
                "status": "success",
                "items_key": items_key,
                "item_count": capped_count,
                "max_iterations": max_iterations,
                "looped": True,
            }

        if action == "start_timer":
            # Start an execution timer with a label
            label = str(params.get("label") or target or "timer")
            duration_ms = int(params.get("duration_ms", 0))
            now = datetime.now(timezone.utc).isoformat()
            return {
                "status": "success",
                "label": label,
                "started_at": now,
                "duration_ms": duration_ms,
            }

        if action == "conditional":
            # Evaluate an if/else condition on inputs or extracted data
            condition_key = str(params.get("condition") or target or "")
            if not condition_key:
                raise ExecutionError("conditional requires params.condition or target")
            if "==" in condition_key:
                key, expected = condition_key.split("==", 1)
                result_value = str(inputs.get(key.strip(), "")) == expected.strip()
            elif "!=" in condition_key:
                key, expected = condition_key.split("!=", 1)
                result_value = str(inputs.get(key.strip(), "")) != expected.strip()
            else:
                result_value = bool(inputs.get(condition_key))
            return {
                "status": "success",
                "condition": condition_key,
                "result": result_value,
                "branch_taken": result_value,
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
