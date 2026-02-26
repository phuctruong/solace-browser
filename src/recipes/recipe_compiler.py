"""Recipe compiler: AST -> deterministic IR."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, List, Tuple

from .recipe_parser import RecipeAST, RecipeParseError, RecipeTransition


class CompilationError(ValueError):
    """Raised when AST cannot be compiled into a safe IR."""


ACTION_SCOPE_MAP: Dict[str, str] = {
    "navigate": "browser.navigate",
    "click": "browser.click",
    "fill": "browser.fill",
    "screenshot": "browser.screenshot",
    "verify": "browser.verify",
}


@dataclass(frozen=True)
class RecipeStepIR:
    step_id: str
    state: str
    action: str
    target: str | None
    params: Dict[str, Any]
    condition_next_state: Tuple[Dict[str, str], ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "state": self.state,
            "action": self.action,
            "target": self.target,
            "params": dict(self.params),
            "condition_next_state": [dict(item) for item in self.condition_next_state],
        }


@dataclass(frozen=True)
class RecipeIR:
    recipe_id: str
    version: str
    determinism_seed: int
    initial_state: str
    scopes_required: Tuple[str, ...]
    steps: Tuple[RecipeStepIR, ...]
    ir_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "version": self.version,
            "determinism_seed": self.determinism_seed,
            "initial_state": self.initial_state,
            "scopes_required": list(self.scopes_required),
            "steps": [step.to_dict() for step in self.steps],
            "ir_hash": self.ir_hash,
        }


def compile(ast: RecipeAST, determinism_seed: int = 65537) -> RecipeIR:
    if not ast.states:
        raise CompilationError("AST has no states")

    outgoing = _group_outgoing(ast.transitions)
    _validate_all_states_reachable(ast)
    _validate_all_states_exit(ast)
    _validate_acyclic(ast)

    steps: List[RecipeStepIR] = []
    scopes_used: set[str] = set()

    for idx, state in enumerate(ast.states, start=1):
        transitions = outgoing.get(state, [])
        if not transitions:
            raise CompilationError(f"state has no outgoing transition: {state}")

        action, target, params = _infer_action(state)
        if action not in ACTION_SCOPE_MAP and action != "noop":
            raise CompilationError(f"unknown action handler: {action}")
        if action in ACTION_SCOPE_MAP:
            scopes_used.add(ACTION_SCOPE_MAP[action])

        condition_next_state = tuple(
            {
                "condition": tr.condition,
                "next_state": tr.to_state,
            }
            for tr in transitions
        )
        steps.append(
            RecipeStepIR(
                step_id=f"s{idx}",
                state=state,
                action=action,
                target=target,
                params=params,
                condition_next_state=condition_next_state,
            )
        )

    payload = {
        "recipe_id": ast.recipe_id,
        "version": "1.0.0",
        "determinism_seed": int(determinism_seed),
        "initial_state": ast.initial_state,
        "scopes_required": sorted(scopes_used),
        "steps": [step.to_dict() for step in steps],
    }
    ir_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    return RecipeIR(
        recipe_id=payload["recipe_id"],
        version=payload["version"],
        determinism_seed=payload["determinism_seed"],
        initial_state=payload["initial_state"],
        scopes_required=tuple(payload["scopes_required"]),
        steps=tuple(steps),
        ir_hash=ir_hash,
    )


def compile_mermaid(recipe_text: str, recipe_id: str = "recipe", determinism_seed: int = 65537) -> RecipeIR:
    from .recipe_parser import parse

    try:
        ast = parse(recipe_text=recipe_text, recipe_id=recipe_id)
    except RecipeParseError as exc:
        raise CompilationError(str(exc)) from exc
    return compile(ast=ast, determinism_seed=determinism_seed)


def _group_outgoing(transitions: Tuple[RecipeTransition, ...]) -> Dict[str, List[RecipeTransition]]:
    grouped: Dict[str, List[RecipeTransition]] = {}
    for tr in transitions:
        grouped.setdefault(tr.from_state, []).append(tr)
    return grouped


def _validate_all_states_reachable(ast: RecipeAST) -> None:
    graph = _group_outgoing(ast.transitions)
    visited: set[str] = set()
    stack = [ast.initial_state]

    while stack:
        node = stack.pop()
        if node == "[*]" or node in visited:
            continue
        visited.add(node)
        for tr in graph.get(node, []):
            if tr.to_state != "[*]":
                stack.append(tr.to_state)

    unreachable = sorted(state for state in ast.states if state not in visited)
    if unreachable:
        raise CompilationError(f"unreachable states from start: {unreachable}")


def _validate_all_states_exit(ast: RecipeAST) -> None:
    reverse_graph: Dict[str, List[str]] = {}
    for tr in ast.transitions:
        reverse_graph.setdefault(tr.to_state, []).append(tr.from_state)

    can_reach_end: set[str] = set(["[*]"])
    stack = ["[*]"]
    while stack:
        node = stack.pop()
        for prev in reverse_graph.get(node, []):
            if prev not in can_reach_end:
                can_reach_end.add(prev)
                stack.append(prev)

    dead_end_states = sorted(state for state in ast.states if state not in can_reach_end)
    if dead_end_states:
        raise CompilationError(f"states cannot reach terminal [*]: {dead_end_states}")


def _validate_acyclic(ast: RecipeAST) -> None:
    graph = _group_outgoing(ast.transitions)
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> None:
        if node == "[*]":
            return
        if node in visiting:
            raise CompilationError(f"infinite loop detected at state: {node}")
        if node in visited:
            return
        visiting.add(node)
        for tr in graph.get(node, []):
            if tr.to_state != "[*]":
                dfs(tr.to_state)
        visiting.remove(node)
        visited.add(node)

    dfs(ast.initial_state)


def _infer_action(state: str) -> Tuple[str, str | None, Dict[str, Any]]:
    lowered = state.lower()
    safe_name = lowered.replace(".", "-").replace("_", "-")

    if "navigate" in lowered:
        target = "https://example.com"
        if "gmail" in lowered:
            target = "https://mail.google.com"
        elif "linkedin" in lowered:
            target = "https://www.linkedin.com"
        return ("navigate", target, {})

    if "click" in lowered or "send" in lowered or "submit" in lowered:
        return ("click", f"#{safe_name}", {})

    if "fill" in lowered or "input" in lowered or "type" in lowered:
        return ("fill", f"#{safe_name}", {"value": "demo"})

    if "screenshot" in lowered or "snapshot" in lowered or "capture" in lowered:
        return ("screenshot", None, {"name": f"{safe_name}.png"})

    if "verify" in lowered or "check" in lowered or "assert" in lowered:
        return ("verify", None, {"script": "() => document.title"})

    if "done" in lowered or "complete" in lowered:
        return ("noop", None, {})

    raise CompilationError(f"cannot infer action for state '{state}'")
