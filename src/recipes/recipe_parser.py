"""Mermaid recipe parser plus deterministic recipe normalization."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Tuple


TRANSITION_PATTERN = re.compile(
    r"^(\[\*\]|[A-Za-z0-9_.\-/]+)\s*-->\s*(\[\*\]|[A-Za-z0-9_.\-/]+)(?:\s*:\s*(.+))?$"
)
MERMAID_BLOCK_PATTERN = re.compile(r"```(?:mermaid)?\s+(.*?)```", re.DOTALL)
STEP_HEADING_PATTERN = re.compile(r"^###\s+Step\s+\d+\s*:\s*(.+)$", re.MULTILINE)


KNOWN_ACTION_SCOPES: Dict[str, str] = {
    "branch": "browser.read",
    "classify": "browser.read",
    "click": "browser.click",
    "document": "browser.read",
    "extract": "browser.read",
    "fill": "browser.fill",
    "inspect": "browser.read",
    "navigate": "browser.navigate",
    "return": "browser.read",
    "screenshot": "browser.screenshot",
    "scroll": "browser.read",
    "search": "browser.read",
    "session": "browser.session",
    "summarize": "browser.read",
    "transform": "browser.read",
    "verify": "browser.verify",
    "wait": "browser.read",
}

ACTION_ALIASES: Dict[str, str] = {
    "capture_result": "screenshot",
    "check_auth": "verify",
    "check_element": "verify",
    "conditional": "branch",
    "conditional_click": "click",
    "create_object": "transform",
    "extract_all": "extract",
    "extract_text": "extract",
    "fill_slowly": "fill",
    "find_and_click": "click",
    "format_results": "transform",
    "human_type": "fill",
    "input": "fill",
    "keyboard": "click",
    "keyboard_press": "click",
    "load_session": "session",
    "log": "inspect",
    "noop": "inspect",
    "press": "click",
    "read_attribute": "extract",
    "return_result": "return",
    "save_session": "session",
    "scroll_and_extract": "extract",
    "snapshot": "screenshot",
    "triple_click": "click",
    "type": "fill",
    "verify_comment": "verify",
    "verify_deletion": "verify",
    "wait_for_element": "wait",
    "wait_for_selector": "wait",
}


class RecipeParseError(ValueError):
    """Raised when a recipe cannot be parsed safely."""


class RecipeValidationError(ValueError):
    """Raised when a parsed recipe is structurally invalid."""


@dataclass(frozen=True)
class RecipeTransition:
    index: int
    from_state: str
    to_state: str
    condition: str


@dataclass(frozen=True)
class RecipeAST:
    recipe_id: str
    states: Tuple[str, ...]
    initial_state: str
    transitions: Tuple[RecipeTransition, ...]

    def to_dict(self) -> Dict[str, object]:
        return {
            "recipe_id": self.recipe_id,
            "states": list(self.states),
            "initial_state": self.initial_state,
            "transitions": [
                {
                    "index": t.index,
                    "from": t.from_state,
                    "to": t.to_state,
                    "condition": t.condition,
                }
                for t in self.transitions
            ],
        }


@dataclass(frozen=True)
class DeterministicRecipeDAG:
    recipe_id: str
    version: str
    platform: str
    source_path: str
    source_format: str
    scopes: Tuple[str, ...]
    steps: Tuple[Dict[str, Any], ...]
    nodes: Tuple[str, ...]
    edges: Tuple[Dict[str, str], ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "version": self.version,
            "platform": self.platform,
            "source_path": self.source_path,
            "source_format": self.source_format,
            "scopes": list(self.scopes),
            "steps": [dict(step) for step in self.steps],
            "nodes": list(self.nodes),
            "edges": [dict(edge) for edge in self.edges],
        }


def parse(recipe_text: str, recipe_id: str = "recipe") -> RecipeAST:
    """Parse a Mermaid state diagram recipe into a structured AST."""
    if "stateDiagram-v2" not in recipe_text:
        raise RecipeParseError("recipe must declare 'stateDiagram-v2'")

    transitions: List[RecipeTransition] = []
    states: set[str] = set()

    for line_no, raw in enumerate(recipe_text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        if line == "stateDiagram-v2":
            continue

        match = TRANSITION_PATTERN.match(line)
        if not match:
            # Ignore non-transition lines but never silently ignore malformed arrows.
            if "-->" in line:
                raise RecipeParseError(f"invalid transition syntax at line {line_no}: {line}")
            continue

        src = match.group(1)
        dst = match.group(2)
        condition = (match.group(3) or "always").strip() or "always"

        transition = RecipeTransition(
            index=len(transitions) + 1,
            from_state=src,
            to_state=dst,
            condition=condition,
        )
        transitions.append(transition)

        if src != "[*]":
            states.add(src)
        if dst != "[*]":
            states.add(dst)

    if not transitions:
        raise RecipeParseError("recipe has no transitions")

    starts = [t for t in transitions if t.from_state == "[*]"]
    if len(starts) != 1:
        raise RecipeParseError("recipe must have exactly one start transition from [*]")

    initial_state = starts[0].to_state
    if initial_state == "[*]":
        raise RecipeParseError("start transition cannot terminate immediately")

    has_terminal = any(t.to_state == "[*]" for t in transitions)
    if not has_terminal:
        raise RecipeParseError("recipe must include at least one terminal transition to [*]")

    _validate_reachable(states=states, initial_state=initial_state, transitions=transitions)
    _validate_acyclic(initial_state=initial_state, transitions=transitions)

    return RecipeAST(
        recipe_id=recipe_id,
        states=tuple(sorted(states)),
        initial_state=initial_state,
        transitions=tuple(transitions),
    )


def _build_graph(transitions: List[RecipeTransition]) -> Dict[str, List[str]]:
    graph: Dict[str, List[str]] = {}
    for tr in transitions:
        graph.setdefault(tr.from_state, []).append(tr.to_state)
    return graph


def _validate_reachable(
    *,
    states: set[str],
    initial_state: str,
    transitions: List[RecipeTransition],
) -> None:
    graph = _build_graph(transitions)
    visited: set[str] = set()
    stack = [initial_state]

    while stack:
        node = stack.pop()
        if node == "[*]" or node in visited:
            continue
        visited.add(node)
        for nxt in graph.get(node, []):
            if nxt != "[*]":
                stack.append(nxt)

    unreachable = sorted(state for state in states if state not in visited)
    if unreachable:
        raise RecipeParseError(f"unreachable states: {unreachable}")


def _validate_acyclic(*, initial_state: str, transitions: List[RecipeTransition]) -> None:
    graph = _build_graph(transitions)
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> None:
        if node == "[*]":
            return
        if node in visiting:
            raise RecipeParseError(f"cycle detected at state: {node}")
        if node in visited:
            return

        visiting.add(node)
        for nxt in graph.get(node, []):
            if nxt != "[*]":
                dfs(nxt)
        visiting.remove(node)
        visited.add(node)

    dfs(initial_state)


def parse_deterministic(recipe_path: str | Path) -> Tuple[DeterministicRecipeDAG, str]:
    """Load a recipe artifact, normalize it, and return a canonical DAG hash."""
    path = Path(recipe_path)
    raw_text = path.read_text(encoding="utf-8")
    if not raw_text.strip():
        raise RecipeParseError(f"recipe file is empty: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = _load_json_payload(raw_text=raw_text, path=path)
        normalized = _normalize_json_recipe(payload=payload, path=path)
    elif suffix == ".md":
        normalized = _normalize_markdown_recipe(raw_text=raw_text, path=path)
    else:
        raise RecipeParseError(f"unsupported recipe file type: {path.suffix or '<none>'}")

    mermaid_fsm = str(normalized.get("mermaid_fsm") or "").strip()
    if mermaid_fsm:
        try:
            ast = parse(mermaid_fsm, recipe_id=str(normalized["recipe_id"]))
        except RecipeParseError as exc:
            raise RecipeValidationError(str(exc)) from exc
        nodes = tuple(sorted(ast.states))
        edges = tuple(
            {
                "from": tr.from_state,
                "to": tr.to_state,
                "condition": tr.condition,
            }
            for tr in sorted(ast.transitions, key=lambda tr: (tr.from_state, tr.to_state, tr.condition, tr.index))
        )
    else:
        nodes, edges = _build_linear_dag(tuple(normalized["steps"]))

    dag = DeterministicRecipeDAG(
        recipe_id=str(normalized["recipe_id"]),
        version=str(normalized["version"]),
        platform=str(normalized["platform"]),
        source_path=str(path),
        source_format=str(normalized["source_format"]),
        scopes=tuple(normalized["scopes"]),
        steps=tuple(normalized["steps"]),
        nodes=nodes,
        edges=edges,
    )
    canonical_payload = dag.to_dict()
    canonical_payload.pop("source_path", None)
    canonical = json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    dag_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return dag, dag_hash


def _load_json_payload(*, raw_text: str, path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RecipeParseError(f"invalid JSON in {path}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise RecipeParseError(f"recipe JSON must be an object: {path}")
    return payload


def _normalize_json_recipe(*, payload: Dict[str, Any], path: Path) -> Dict[str, Any]:
    recipe_id = _resolve_recipe_id(payload=payload, path=path)
    version = str(payload.get("version") or payload.get("recipe_version") or "1.0.0")
    platform = str(payload.get("platform") or payload.get("domain") or payload.get("site") or _infer_platform(path))
    steps = tuple(_extract_steps(payload=payload, path=path))
    scopes = tuple(_extract_scopes(payload=payload, steps=steps))
    return {
        "recipe_id": recipe_id,
        "version": version,
        "platform": platform,
        "source_format": "json",
        "steps": steps,
        "scopes": scopes,
        "mermaid_fsm": payload.get("mermaid_fsm"),
    }


def _normalize_markdown_recipe(*, raw_text: str, path: Path) -> Dict[str, Any]:
    recipe_id = path.stem
    mermaid_fsm = _extract_mermaid_fsm(raw_text)
    headings = [heading.strip() for heading in STEP_HEADING_PATTERN.findall(raw_text)]
    steps = tuple(
        _normalize_step_record(
            {"title": heading, "description": heading},
            index=index,
            strict_action=False,
        )
        for index, heading in enumerate(headings, start=1)
    )
    if not steps and not mermaid_fsm:
        raise RecipeValidationError(f"markdown recipe has no deterministic steps: {path}")

    scopes = ("browser.read",)
    if not steps:
        steps = (
            {
                "step_id": "s001",
                "index": 1,
                "action": "inspect",
                "target": None,
                "description": "Inspect markdown recipe artifact",
            },
        )
    return {
        "recipe_id": recipe_id,
        "version": "1.0.0",
        "platform": _infer_platform(path),
        "source_format": "markdown",
        "steps": steps,
        "scopes": scopes,
        "mermaid_fsm": mermaid_fsm,
    }


def _resolve_recipe_id(*, payload: Dict[str, Any], path: Path) -> str:
    recipe_id = str(payload.get("id") or payload.get("recipe_id") or "").strip()
    if recipe_id:
        return recipe_id

    # Legacy smoke recipes are identified only by filename plus required scope.
    required_scope = payload.get("required_scope")
    if isinstance(required_scope, str) and required_scope.strip():
        return path.stem.replace(".recipe", "")

    raise RecipeValidationError("missing required field: id or recipe_id")


def _extract_steps(*, payload: Dict[str, Any], path: Path) -> List[Dict[str, Any]]:
    if "steps" in payload:
        steps = payload.get("steps")
        if isinstance(steps, list) and not steps:
            raise RecipeValidationError(f"recipe has empty steps list: {path}")
        if isinstance(steps, list):
            return _normalize_step_records(steps, strict_action=True)

    for key in ("execution_trace", "actions", "implementation_steps"):
        items = payload.get(key)
        if isinstance(items, list) and items:
            return _normalize_step_records(items, strict_action=False)

    portals = payload.get("portals")
    portal_steps = _steps_from_portals(portals)
    if portal_steps:
        return portal_steps

    portals_discovered = payload.get("portals_discovered")
    discovered_steps = _steps_from_named_mapping(portals_discovered)
    if discovered_steps:
        return discovered_steps

    form_fields = payload.get("form_fields")
    if isinstance(form_fields, dict) and form_fields:
        return _steps_from_form_fields(payload=payload, form_fields=form_fields)

    landmarks = payload.get("landmarks")
    landmark_steps = _steps_from_named_mapping(landmarks)
    if landmark_steps:
        return landmark_steps

    fallback = _fallback_step(payload=payload)
    if fallback is not None:
        return [fallback]

    raise RecipeValidationError(f"recipe has no deterministic step source: {path}")


def _extract_scopes(*, payload: Dict[str, Any], steps: Iterable[Dict[str, Any]]) -> Tuple[str, ...]:
    raw_scopes = payload.get("oauth3_scopes")
    if isinstance(raw_scopes, list):
        scopes = sorted({str(scope).strip() for scope in raw_scopes if str(scope).strip()})
        if scopes:
            return tuple(scopes)

    required_scope = payload.get("required_scope")
    if isinstance(required_scope, str) and required_scope.strip():
        return (required_scope.strip(),)

    inferred = sorted(
        {
            KNOWN_ACTION_SCOPES[action]
            for action in (str(step.get("action") or "") for step in steps)
            if action in KNOWN_ACTION_SCOPES
        }
    )
    if inferred:
        return tuple(inferred)

    raise RecipeValidationError("recipe is missing scopes and no deterministic inference was possible")


def _normalize_step_records(items: List[Any], *, strict_action: bool) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        normalized.append(_normalize_step_record(item, index=index, strict_action=strict_action))
    return normalized


def _normalize_step_record(item: Any, *, index: int, strict_action: bool) -> Dict[str, Any]:
    if isinstance(item, str):
        description = item.strip()
        if not description:
            raise RecipeValidationError("step description cannot be empty")
        action = _normalize_action(description, strict=False)
        return {
            "step_id": f"s{index:03d}",
            "index": index,
            "action": action,
            "target": None,
            "description": description,
        }

    if not isinstance(item, dict):
        raise RecipeValidationError(f"unsupported step record type: {type(item).__name__}")

    raw_step = item.get("step")
    try:
        step_index = int(raw_step) if raw_step is not None else index
    except (TypeError, ValueError):
        step_index = index

    explicit_action = item.get("action")
    explicit_type = item.get("type")
    source_value = explicit_action if explicit_action is not None else explicit_type
    action = _normalize_action(
        str(source_value or item.get("title") or item.get("name") or item.get("description") or ""),
        strict=source_value is not None and strict_action,
    )
    target = _first_string(
        item.get("target"),
        item.get("selector"),
        item.get("path"),
        item.get("url"),
        item.get("href"),
        item.get("leads_to"),
        item.get("output"),
    )
    description = _first_string(
        item.get("description"),
        item.get("title"),
        item.get("text"),
        item.get("name"),
        source_value,
        f"step-{step_index}",
    )
    return {
        "step_id": f"s{step_index:03d}",
        "index": step_index,
        "action": action,
        "target": target,
        "description": description,
    }


def _normalize_action(raw: str, *, strict: bool) -> str:
    token = re.sub(r"[^a-z0-9_]+", "_", raw.strip().lower().replace("-", "_").replace(" ", "_")).strip("_")
    if token in ACTION_ALIASES:
        return ACTION_ALIASES[token]
    if token in KNOWN_ACTION_SCOPES:
        return token

    inferred = _infer_action(raw)
    if inferred:
        return inferred

    if strict:
        raise RecipeValidationError(f"unknown action type: {raw}")
    return "inspect"


def _infer_action(raw: str) -> str | None:
    lowered = raw.strip().lower()
    if not lowered:
        return None
    if any(token in lowered for token in ("navigate", "open ", "goto", "go to", "visit", "url")):
        return "navigate"
    if any(token in lowered for token in ("click", "submit", "press", "button", "commit")):
        return "click"
    if any(token in lowered for token in ("type", "fill", "input", "form", "password", "email")):
        return "fill"
    if any(token in lowered for token in ("screenshot", "snapshot", "capture")):
        return "screenshot"
    if any(token in lowered for token in ("verify", "check", "assert", "auth")):
        return "verify"
    if any(token in lowered for token in ("search", "extract", "read", "discover", "inspect", "portal", "landmark")):
        return "extract"
    if any(token in lowered for token in ("summarize", "summary")):
        return "summarize"
    if "classif" in lowered:
        return "classify"
    if any(token in lowered for token in ("wait", "loaded", "delay")):
        return "wait"
    if any(token in lowered for token in ("session", "token")):
        return "session"
    if any(token in lowered for token in ("update", "document", "report", "measure", "create", "save")):
        return "document"
    if any(token in lowered for token in ("scroll",)):
        return "scroll"
    return None


def _steps_from_portals(portals: Any) -> List[Dict[str, Any]]:
    if isinstance(portals, dict):
        items = []
        for name, value in portals.items():
            if isinstance(value, dict):
                value = {"name": name, **value}
            else:
                value = {"name": name, "target": value}
            items.append(value)
        return _normalize_step_records(items, strict_action=False)

    if isinstance(portals, list):
        return _normalize_step_records(portals, strict_action=False)
    return []


def _steps_from_named_mapping(mapping: Any) -> List[Dict[str, Any]]:
    if not isinstance(mapping, dict) or not mapping:
        return []
    records: List[Dict[str, Any]] = []
    for name, value in mapping.items():
        if isinstance(value, dict):
            record = {"name": name, **value}
        else:
            record = {"name": name, "description": f"{name}: {value}"}
        records.append(record)
    return _normalize_step_records(records, strict_action=False)


def _steps_from_form_fields(*, payload: Dict[str, Any], form_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for name, selector in form_fields.items():
        records.append(
            {
                "step": len(records) + 1,
                "action": "fill",
                "selector": selector,
                "description": f"Fill {name}",
            }
        )

    submit = payload.get("submit_button")
    if submit:
        records.append(
            {
                "step": len(records) + 1,
                "action": "click",
                "selector": submit,
                "description": "Submit form",
            }
        )
    return _normalize_step_records(records, strict_action=True)


def _fallback_step(*, payload: Dict[str, Any]) -> Dict[str, Any] | None:
    description = _first_string(
        payload.get("summary"),
        payload.get("description"),
        payload.get("title"),
        payload.get("task"),
        payload.get("workflow"),
        payload.get("source_episode"),
        payload.get("page_name"),
        payload.get("recipe_id"),
        payload.get("id"),
    )
    if not description:
        return None
    action = _normalize_action(description, strict=False)
    return {
        "step_id": "s001",
        "index": 1,
        "action": action,
        "target": None,
        "description": description,
    }


def _extract_mermaid_fsm(raw_text: str) -> str | None:
    for block in MERMAID_BLOCK_PATTERN.findall(raw_text):
        text = block.strip()
        if "stateDiagram-v2" in text:
            return text
    if "stateDiagram-v2" in raw_text:
        return raw_text[raw_text.index("stateDiagram-v2") :].strip()
    return None


def _build_linear_dag(steps: Tuple[Dict[str, Any], ...]) -> Tuple[Tuple[str, ...], Tuple[Dict[str, str], ...]]:
    if not steps:
        raise RecipeValidationError("cannot build DAG from empty steps")

    nodes = tuple(step["step_id"] for step in steps)
    edges: List[Dict[str, str]] = [{"from": "[*]", "to": nodes[0], "condition": "start"}]
    for left, right in zip(nodes, nodes[1:]):
        edges.append({"from": left, "to": right, "condition": "always"})
    edges.append({"from": nodes[-1], "to": "[*]", "condition": "done"})
    return nodes, tuple(edges)


def _infer_platform(path: Path) -> str:
    parent = path.parent.name
    if parent != "recipes":
        return parent
    stem = path.stem.replace(".recipe", "")
    head = stem.split("-", 1)[0]
    return head or "unknown"


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
