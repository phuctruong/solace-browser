"""Mermaid recipe parser for Phase 2 state machines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import re


TRANSITION_PATTERN = re.compile(
    r"^(\[\*\]|[A-Za-z0-9_.\-/]+)\s*-->\s*(\[\*\]|[A-Za-z0-9_.\-/]+)(?:\s*:\s*(.+))?$"
)


class RecipeParseError(ValueError):
    """Raised when a recipe cannot be parsed safely."""


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
