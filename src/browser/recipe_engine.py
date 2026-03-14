# Diagram: 01-triangle-architecture
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class FSMState(str, Enum):
    INTAKE = "INTAKE"
    INTENT_CLASSIFY = "INTENT_CLASSIFY"
    CACHE_LOOKUP = "CACHE_LOOKUP"
    HIT_VERIFY = "HIT_VERIFY"
    CACHE_MISS = "CACHE_MISS"
    LLM_GENERATE = "LLM_GENERATE"
    VALIDATE = "VALIDATE"
    EXECUTE = "EXECUTE"
    CHECKPOINT = "CHECKPOINT"
    EVIDENCE = "EVIDENCE"
    STORE = "STORE"
    EXIT_PASS = "EXIT_PASS"
    EXIT_BLOCKED = "EXIT_BLOCKED"
    EXIT_NEED_INFO = "EXIT_NEED_INFO"


@dataclass(frozen=True)
class RecipeRequest:
    intent: str
    platform: str
    action_type: str


@dataclass(frozen=True)
class CacheLookupResult:
    hit: bool
    recipe: Optional[Dict[str, Any]]


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class RecipeResult:
    status: str
    steps_executed: int = 0
    evidence_bundle: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class HitVerifyResult:
    valid: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class NeverWorseResult:
    promoted: bool
    status: str
    failed: list[str]


class RecipeEngine:
    def __init__(self, cache: Dict[str, Any], llm: Any) -> None:
        self.cache = cache
        self.llm = llm
        self._browser: Any = None

    def run(self, request: RecipeRequest) -> RecipeResult:
        if not request.intent or not request.platform or not request.action_type:
            return RecipeResult(status=FSMState.EXIT_NEED_INFO.value)

        cache_key = self._cache_key(request.intent, request.platform, request.action_type)
        lookup = self._cache_lookup(cache_key)
        recipe: Optional[Dict[str, Any]] = None

        if lookup.hit and lookup.recipe is not None:
            verify = self._hit_verify(lookup.recipe)
            if verify.valid:
                recipe = lookup.recipe

        if recipe is None:
            recipe = self._generate_with_retries(request)
            if recipe is None:
                return RecipeResult(status=FSMState.EXIT_BLOCKED.value)

        execution = self._execute(recipe)
        if execution.status == FSMState.EXIT_BLOCKED.value:
            return execution

        evidence_bundle = self._build_evidence_bundle(cache_key, recipe, execution.steps_executed)
        self.cache[cache_key] = recipe
        return RecipeResult(
            status=FSMState.EXIT_PASS.value,
            steps_executed=execution.steps_executed,
            evidence_bundle=evidence_bundle,
        )

    def _cache_key(self, intent: str, platform: str, action_type: str) -> str:
        normalized = intent.lower().strip() + platform + action_type
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _cache_lookup(self, cache_key: str) -> CacheLookupResult:
        recipe = self.cache.get(cache_key)
        return CacheLookupResult(hit=recipe is not None, recipe=recipe)

    def _hit_verify(self, recipe: Dict[str, Any]) -> HitVerifyResult:
        if not self._never_worse_check(recipe):
            return HitVerifyResult(valid=False, reason="stale_or_regressed")
        return HitVerifyResult(valid=True)

    def _never_worse_check(self, recipe: Dict[str, Any]) -> bool:
        return not bool(recipe.get("_stale"))

    def _generate_with_retries(self, request: RecipeRequest) -> Optional[Dict[str, Any]]:
        for _ in range(3):
            candidate = self._generate_recipe(request)
            result = self._validate(candidate)
            if result.valid:
                return candidate
        return None

    def _generate_recipe(self, request: RecipeRequest) -> Dict[str, Any]:
        if callable(self.llm):
            raw = self.llm(
                {
                    "intent": request.intent,
                    "platform": request.platform,
                    "action_type": request.action_type,
                }
            )
            if isinstance(raw, dict):
                return raw
            if isinstance(raw, str):
                return json.loads(raw)

        return {
            "recipe_id": str(uuid.uuid4()),
            "version": "1.0.0",
            "intent": request.intent,
            "platform": request.platform,
            "action_type": request.action_type,
            "oauth3_scopes_required": [],
            "max_steps": 10,
            "timeout_ms": 30000,
            "portals": [f"https://www.{request.platform}.com/"],
            "steps": [],
            "output_schema": "ok",
        }

    def _validate(self, recipe: Dict[str, Any]) -> ValidationResult:
        if "max_steps" not in recipe or "timeout_ms" not in recipe:
            return ValidationResult(valid=False, reason="missing_closure")
        portals = recipe.get("portals", [])
        if not isinstance(portals, list) or not portals:
            return ValidationResult(valid=False, reason="missing_portals")
        steps = recipe.get("steps", [])
        if not isinstance(steps, list):
            return ValidationResult(valid=False, reason="invalid_steps")
        return ValidationResult(valid=True)

    def _execute(self, recipe: Dict[str, Any]) -> RecipeResult:
        steps = list(recipe.get("steps", []))
        max_steps = int(recipe.get("max_steps", 0))
        if max_steps <= 0:
            return RecipeResult(status=FSMState.EXIT_BLOCKED.value, steps_executed=0)

        executed = 0
        for step in steps:
            if executed >= max_steps:
                return RecipeResult(status=FSMState.EXIT_BLOCKED.value, steps_executed=executed)

            step_result = self._run_step(step)
            executed += 1

            checkpoint = bool(step.get("checkpoint"))
            checkpoint_passed = bool(step_result.get("checkpoint_passed", step_result.get("status") == "PASS"))
            if checkpoint and not checkpoint_passed:
                self._rollback(step)
                return RecipeResult(status=FSMState.EXIT_BLOCKED.value, steps_executed=executed)

            if step_result.get("status") == "FAIL":
                return RecipeResult(status=FSMState.EXIT_BLOCKED.value, steps_executed=executed)

        return RecipeResult(status=FSMState.EXECUTE.value, steps_executed=executed)

    def _run_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "PASS", "checkpoint_passed": True}

    def _rollback(self, step: Dict[str, Any]) -> None:
        return None

    def _run_recipe_tests(self, old_recipe: Dict[str, Any], new_recipe: Dict[str, Any]) -> Dict[str, Any]:
        return {"all_passed": True, "failed": []}

    def _never_worse_gate(self, old_recipe: Dict[str, Any], new_recipe: Dict[str, Any]) -> NeverWorseResult:
        test_result = self._run_recipe_tests(old_recipe, new_recipe)
        all_passed = bool(test_result.get("all_passed"))
        failed = list(test_result.get("failed", []))
        return NeverWorseResult(
            promoted=all_passed,
            status="PROMOTED" if all_passed else "BLOCKED",
            failed=failed,
        )

    def _build_evidence_bundle(
        self, cache_key: str, recipe: Dict[str, Any], steps_executed: int
    ) -> Dict[str, Any]:
        seed = f"{cache_key}:{recipe.get('recipe_id','')}:{recipe.get('version','')}"
        bundle_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return {
            "bundle_id": bundle_id,
            "recipe_id": recipe.get("recipe_id"),
            "recipe_version": recipe.get("version"),
            "steps_executed": steps_executed,
            "status": "success",
        }
