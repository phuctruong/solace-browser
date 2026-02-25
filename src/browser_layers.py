"""
Reference browser multi-layer wrapper.

Implements a minimal 5-layer contract used by diagram-driven tests:
L1 heartbeat, L2 intent classification, L3 recipe match,
L4 execution trace + snapshots, L5 evidence bundle.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class HeartbeatResult:
    browser_alive: bool
    session_active: bool
    recipe_store_ready: bool
    overall: str


@dataclass
class ClassifiedIntent:
    normalized_intent: str
    platform: str
    action_type: str
    cache_key: str
    status: str = "PASS"
    reason: Optional[str] = None


@dataclass
class RecipeMatchResult:
    hit: bool
    cache_key: str
    recipe: Optional[Dict[str, Any]]


@dataclass
class ExecutionResult:
    trace_id: str
    recipe_id: str
    status: str
    before_snapshot: bytes
    after_snapshot: bytes
    execution_trace: List[Dict[str, Any]] = field(default_factory=list)
    model_used: str = "haiku"
    error: Optional[str] = None


@dataclass
class EvidenceResult:
    bundle: Dict[str, Any]


def get_browser_page() -> Any:
    """Default browser page probe used by heartbeat checks."""

    class _DummyPage:
        session_active = True

        def is_connected(self) -> bool:
            return True

        def content(self) -> str:
            return "<!DOCTYPE html><html><body>ok</body></html>"

    return _DummyPage()


def heartbeat_check(*, browser: Any | None = None, recipe_store_ready: bool = True) -> HeartbeatResult:
    page = browser or get_browser_page()

    is_connected = getattr(page, "is_connected", None)
    if callable(is_connected):
        browser_alive = bool(is_connected())
    elif is_connected is None:
        browser_alive = True
    else:
        browser_alive = bool(is_connected)

    session_active = bool(getattr(page, "session_active", True))
    store_ready = bool(recipe_store_ready)
    overall = "PASS" if (browser_alive and session_active and store_ready) else "BLOCKED"
    return HeartbeatResult(
        browser_alive=browser_alive,
        session_active=session_active,
        recipe_store_ready=store_ready,
        overall=overall,
    )


def classify_intent(intent: str) -> ClassifiedIntent:
    text = " ".join((intent or "").strip().lower().split())
    if not text:
        return ClassifiedIntent(
            normalized_intent="",
            platform="unknown",
            action_type="navigate",
            cache_key="",
            status="NEED_INFO",
            reason="ambiguous_intent",
        )

    platform = _detect_platform(text)
    action_type = _detect_action(text, platform)

    tmp = ClassifiedIntent(
        normalized_intent=text,
        platform=platform,
        action_type=action_type,
        cache_key="",
    )
    tmp.cache_key = compute_cache_key(tmp)
    return tmp


def compute_cache_key(classified_intent: ClassifiedIntent) -> str:
    canonical = f"{classified_intent.normalized_intent}|{classified_intent.platform}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def recipe_match(cache_key: str, *, cache: Dict[str, Dict[str, Any]]) -> RecipeMatchResult:
    recipe = cache.get(cache_key)
    return RecipeMatchResult(
        hit=recipe is not None,
        cache_key=cache_key,
        recipe=recipe,
    )


def execute_layer(
    *,
    recipe: Dict[str, Any],
    browser: Any,
    cache_hit: bool = True,
) -> ExecutionResult:
    before_snapshot = _capture_dom_snapshot(browser)

    steps = list(recipe.get("steps", []))
    max_steps = int(recipe.get("max_steps", 0))
    trace: List[Dict[str, Any]] = []
    status = "EXIT_PASS"
    error: Optional[str] = None

    if max_steps <= 0:
        status = "EXIT_BLOCKED"
        error = "invalid_max_steps"
    else:
        for idx, step in enumerate(steps, start=1):
            if idx > max_steps:
                status = "EXIT_BLOCKED"
                error = "max_steps_exceeded"
                break

            action = str(step.get("action", "")).strip().lower()
            selector = step.get("selector")
            try:
                _run_browser_action(browser, action, selector)
                trace.append(
                    {
                        "step_number": idx,
                        "action": action,
                        "status": "ok",
                    }
                )
            except Exception as exc:  # noqa: BLE001
                status = "EXIT_BLOCKED"
                error = str(exc)
                trace.append(
                    {
                        "step_number": idx,
                        "action": action,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                break

    after_snapshot = _capture_dom_snapshot(browser)

    return ExecutionResult(
        trace_id=str(uuid.uuid4()),
        recipe_id=str(recipe.get("recipe_id", "unknown")),
        status=status,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        execution_trace=trace,
        model_used="haiku" if cache_hit else "sonnet",
        error=error,
    )


def evidence_layer(
    *,
    before_snapshot: bytes,
    after_snapshot: bytes,
    action_id: str,
    platform: str,
    action_type: str,
    oauth3_token_id: str,
    pzip: Any | None = None,
    prev_chain_link: Optional[str] = None,
    rung_achieved: int = 641,
) -> Dict[str, Any]:
    before_compressed = _compress_snapshot(before_snapshot, pzip)
    after_compressed = _compress_snapshot(after_snapshot, pzip)

    before_hash = hashlib.sha256(before_compressed).hexdigest()
    after_hash = hashlib.sha256(after_compressed).hexdigest()
    diff_hash = hashlib.sha256(before_compressed + b"::" + after_compressed).hexdigest()

    timestamp = datetime.now(timezone.utc).isoformat()
    chain_prev = prev_chain_link or hashlib.sha256(b"genesis").hexdigest()

    bundle_seed = f"{action_id}:{timestamp}:{diff_hash}"
    bundle_id = hashlib.sha256(bundle_seed.encode("utf-8")).hexdigest()
    signature_seed = f"{bundle_id}:{oauth3_token_id}:{chain_prev}"
    signature = hashlib.sha256(signature_seed.encode("utf-8")).hexdigest()

    return {
        "schema_version": "1.0.0",
        "bundle_id": bundle_id,
        "action_id": action_id,
        "action_type": action_type,
        "platform": platform,
        "before_snapshot_pzip_hash": before_hash,
        "after_snapshot_pzip_hash": after_hash,
        "diff_hash": diff_hash,
        "oauth3_token_id": oauth3_token_id,
        "timestamp_iso8601": timestamp,
        "sha256_chain_link": chain_prev,
        "signature": signature,
        "alcoa_fields": {
            "attributable": "system",
            "legible": True,
            "contemporaneous": timestamp,
            "original": True,
            "accurate": True,
            "complete": True,
            "consistent": True,
            "enduring": True,
            "available": True,
        },
        "rung_achieved": int(rung_achieved),
        "created_by": "browser_layers",
    }


def _detect_platform(text: str) -> str:
    if "linkedin" in text:
        return "linkedin"
    if "gmail" in text or "email" in text:
        return "gmail"
    if "twitter" in text or "tweet" in text:
        return "twitter"
    if "reddit" in text:
        return "reddit"
    if "hackernews" in text or "hn" in text:
        return "hackernews"
    if "github" in text:
        return "github"
    if "notion" in text:
        return "notion"
    if "substack" in text:
        return "substack"
    if "tunnel" in text:
        return "tunnel"
    if "file" in text or "command" in text or "terminal" in text:
        return "machine"
    return "machine"


def _detect_action(text: str, platform: str) -> str:
    if any(k in text for k in ["delete", "remove"]):
        return "delete_post"
    if any(k in text for k in ["send email", "send an email", "email"]):
        return "send_email"
    if any(k in text for k in ["read inbox", "inbox"]):
        return "read_inbox"
    if "tweet" in text:
        return "create_tweet"
    if any(k in text for k in ["search", "find"]):
        return "search"
    if any(k in text for k in ["issue", "bug report", "github issue"]):
        return "create_issue"
    if any(k in text for k in ["execute", "command", "terminal"]):
        return "execute_command"
    if any(k in text for k in ["write file", "save file"]):
        return "write_file"
    if any(k in text for k in ["read file", "open file"]):
        return "read_file"
    if any(k in text for k in ["read", "browse", "view"]):
        return "read_feed"
    if platform in {"linkedin", "twitter", "reddit", "hackernews", "substack"}:
        return "create_post"
    return "navigate"


def _capture_dom_snapshot(browser: Any) -> bytes:
    content = getattr(browser, "content", None)
    if callable(content):
        raw = content()
    else:
        raw = "<!DOCTYPE html><html><body></body></html>"

    if isinstance(raw, bytes):
        return raw
    return str(raw).encode("utf-8")


def _run_browser_action(browser: Any, action: str, selector: Any) -> None:
    if action == "click" and hasattr(browser, "click"):
        browser.click(selector)
    elif action == "type" and hasattr(browser, "type"):
        browser.type(selector, "")
    elif action == "navigate" and hasattr(browser, "goto"):
        browser.goto(selector)


def _compress_snapshot(snapshot: bytes, pzip: Any | None) -> bytes:
    if pzip is not None and hasattr(pzip, "compress"):
        compressed = pzip.compress(snapshot)
        if isinstance(compressed, bytes):
            return compressed
        return str(compressed).encode("utf-8")
    return snapshot
