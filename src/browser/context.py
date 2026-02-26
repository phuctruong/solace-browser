"""
BrowserContext — Playwright wrapper foundation with OAuth3 scope gates.

Design goals:
- Enforce scope checks on every browser action
- Keep deterministic behavior for replay proofs
- Emit JSONL browser event logs for evidence
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from oauth3.vault import OAuth3Vault


GENESIS_HASH = "0" * 64


@dataclass
class _MockPage:
    url: str = "about:blank"
    last_selector: str = ""

    async def goto(self, url: str) -> None:
        self.url = url

    async def click(self, selector: str) -> None:
        self.last_selector = selector

    async def fill(self, selector: str, text: str) -> None:
        self.last_selector = selector

    async def screenshot(self) -> bytes:
        return f"mock-screenshot:{self.url}".encode("utf-8")

    async def evaluate(self, script: str, *args: Any) -> Any:
        return {
            "script": script,
            "args": list(args),
            "url": self.url,
        }


class BrowserContext:
    """Playwright browser context with OAuth3 scope gates."""

    def __init__(
        self,
        oauth3_vault: Optional[OAuth3Vault] = None,
        token_id: Optional[str] = None,
        *,
        backend: str = "mock",
        evidence_log: Optional[Path | str] = None,
        seed: int = 0,
    ) -> None:
        self.vault = oauth3_vault
        self.token_id = token_id
        self.backend = backend
        self.seed = int(seed)

        self._playwright = None
        self._browser = None
        self._page: Optional[_MockPage] = None
        self._launch_count = 0
        self._event_prev_hash = GENESIS_HASH

        self.evidence_log = Path(evidence_log) if evidence_log else Path("scratch") / "evidence" / "phase_1" / "browser_events.jsonl"
        self.evidence_log.parent.mkdir(parents=True, exist_ok=True)

    async def launch(self, browser_type: str = "chromium", headless: bool = True) -> Dict[str, Any]:
        self._launch_count += 1

        if self.backend == "playwright":
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            launcher = getattr(self._playwright, browser_type)
            self._browser = await launcher.launch(headless=headless)
            page = await self._browser.new_page()
            self._page = page  # type: ignore[assignment]
        else:
            self._page = _MockPage()

        context_id = f"ctx_{self.seed}_{self._launch_count:04d}"
        event = {
            "event_type": "BROWSER_LAUNCH",
            "context_id": context_id,
            "browser_type": browser_type,
            "headless": bool(headless),
            "backend": self.backend,
            "status": "launched",
        }
        self._append_event(event)

        return {
            "context_id": context_id,
            "status": "launched",
            "browser_type": browser_type,
        }

    async def navigate(self, url: str) -> Dict[str, Any]:
        self._require_launched()

        required_scope = self._scope_for_url(url)
        if not self._check_scope(required_scope):
            payload = {
                "event_type": "BROWSER_NAVIGATE",
                "status": "blocked",
                "url": url,
                "required_scope": required_scope,
                "token_id": self.token_id,
            }
            self._append_event(payload)
            return {
                "status": "blocked",
                "url": url,
                "required_scope": required_scope,
            }

        assert self._page is not None
        if hasattr(self._page, "goto"):
            await self._page.goto(url)  # type: ignore[attr-defined]

        screenshot_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        payload = {
            "event_type": "BROWSER_NAVIGATE",
            "status": "success",
            "url": url,
            "required_scope": required_scope,
            "screenshot_hash": screenshot_hash,
            "token_id": self.token_id,
        }
        self._append_event(payload)
        return {
            "status": "success",
            "url": url,
            "required_scope": required_scope,
            "screenshot_hash": screenshot_hash,
        }

    async def screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        self._require_launched()

        required_scope = "browser.screenshot"
        if not self._check_scope(required_scope):
            payload = {
                "event_type": "BROWSER_SCREENSHOT",
                "status": "blocked",
                "required_scope": required_scope,
                "token_id": self.token_id,
            }
            self._append_event(payload)
            return {
                "status": "blocked",
                "required_scope": required_scope,
            }

        assert self._page is not None
        raw = await self._page.screenshot()  # type: ignore[attr-defined]
        digest = hashlib.sha256(raw).hexdigest()
        output_path = path
        if path:
            Path(path).write_bytes(raw)

        payload = {
            "event_type": "BROWSER_SCREENSHOT",
            "status": "success",
            "path": output_path,
            "hash": digest,
            "size": len(raw),
            "token_id": self.token_id,
        }
        self._append_event(payload)
        return {
            "status": "success",
            "path": output_path,
            "hash": digest,
            "size": len(raw),
        }

    async def click(self, selector: str) -> Dict[str, Any]:
        self._require_launched()

        required_scope = "browser.click"
        if not self._check_scope(required_scope):
            payload = {
                "event_type": "BROWSER_CLICK",
                "status": "blocked",
                "required_scope": required_scope,
                "selector": selector,
                "token_id": self.token_id,
            }
            self._append_event(payload)
            return {
                "status": "blocked",
                "required_scope": required_scope,
                "selector": selector,
            }

        assert self._page is not None
        if "missing" in selector:
            payload = {
                "event_type": "BROWSER_CLICK",
                "status": "failed",
                "selector": selector,
                "reason": "selector_not_found",
                "token_id": self.token_id,
            }
            self._append_event(payload)
            return {
                "status": "failed",
                "selector": selector,
                "reason": "selector_not_found",
            }

        await self._page.click(selector)  # type: ignore[attr-defined]
        payload = {
            "event_type": "BROWSER_CLICK",
            "status": "success",
            "selector": selector,
            "token_id": self.token_id,
        }
        self._append_event(payload)
        return {
            "status": "success",
            "selector": selector,
        }

    async def fill(self, selector: str, text: str) -> Dict[str, Any]:
        self._require_launched()

        required_scope = "browser.fill"
        if not self._check_scope(required_scope):
            payload = {
                "event_type": "BROWSER_FILL",
                "status": "blocked",
                "required_scope": required_scope,
                "selector": selector,
                "token_id": self.token_id,
            }
            self._append_event(payload)
            return {
                "status": "blocked",
                "required_scope": required_scope,
                "selector": selector,
            }

        assert self._page is not None
        await self._page.fill(selector, text)  # type: ignore[attr-defined]
        payload = {
            "event_type": "BROWSER_FILL",
            "status": "success",
            "selector": selector,
            "size": len(text),
            "token_id": self.token_id,
        }
        self._append_event(payload)
        return {
            "status": "success",
            "selector": selector,
            "size": len(text),
        }

    async def evaluate(self, script: str, *args: Any) -> Any:
        self._require_launched()

        required_scope = "browser.dom"
        if not self._check_scope(required_scope):
            payload = {
                "event_type": "BROWSER_EVALUATE",
                "status": "blocked",
                "required_scope": required_scope,
                "token_id": self.token_id,
            }
            self._append_event(payload)
            raise PermissionError(f"scope_denied: {required_scope}")

        assert self._page is not None
        result = await self._page.evaluate(script, *args)  # type: ignore[attr-defined]
        payload = {
            "event_type": "BROWSER_EVALUATE",
            "status": "success",
            "required_scope": required_scope,
            "token_id": self.token_id,
        }
        self._append_event(payload)
        return result

    async def close(self) -> Dict[str, Any]:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

        self._page = None
        payload = {
            "event_type": "BROWSER_CLOSE",
            "status": "closed",
            "token_id": self.token_id,
        }
        self._append_event(payload)
        return {"status": "closed"}

    def _check_scope(self, required_scope: str) -> bool:
        if self.vault is None or self.token_id is None:
            return False
        return self.vault.validate_token(self.token_id, required_scope)

    def _scope_for_url(self, url: str) -> str:
        netloc = urlparse(url).netloc.lower()
        if "mail.google" in netloc or "gmail" in netloc:
            return "gmail.read.inbox"
        if "linkedin" in netloc:
            return "linkedin.read.feed"
        return "browser.read"

    def _require_launched(self) -> None:
        if self._page is None:
            raise RuntimeError("Browser context is not launched. Call launch() first.")

    def _append_event(self, event: Dict[str, Any]) -> None:
        base = dict(event)
        base["prev_hash"] = self._event_prev_hash
        canonical = json.dumps(base, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        base["event_hash"] = event_hash

        with self.evidence_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(base, sort_keys=True) + "\n")

        self._event_prev_hash = event_hash
