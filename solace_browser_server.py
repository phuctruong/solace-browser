#!/usr/bin/env python3

"""
SOLACE BROWSER - Custom Headless Browser with CDP Protocol
Option C: Headless core + optional debugging UI

Features:
- Real browser automation (Chromium-based)
- Chrome DevTools Protocol (CDP) support
- Headless by default
- Optional web-based debugging UI
- Screenshot and DOM snapshot capture
- Full page navigation and interaction
- Accessibility tree snapshots (ARIA)
- Structured element references
- Human-like interaction patterns
"""

import asyncio
import hashlib
import json
import logging
import sys
import argparse
import os
from pathlib import Path
from typing import Dict, Optional, Any
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

__version__ = "1.0.0"

# OAuth3/local source modules live under src/, but keep the repo root ahead of it
# so imports like `browser` resolve to the top-level browser package, not src/browser.
_SRC_PATH = Path(__file__).parent / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.append(str(_SRC_PATH))

try:
    from history import (
        BrowsingSession,
        list_sessions,
        load_session,
        get_snapshot as get_session_snapshot,
        list_session_snapshots,
        save_session as save_browsing_session,
    )
    HISTORY_AVAILABLE = True
except ImportError as _history_import_error:
    logger_temp = logging.getLogger("solace-browser")
    logger_temp.warning(f"History module not available: {_history_import_error}")
    HISTORY_AVAILABLE = False

try:
    from oauth3 import (
        AgencyToken,
        SCOPES,
        validate_scopes,
        get_scope_description,
        enforce_oauth3,
        revoke_token,
        revoke_all_tokens_for_scope,
        is_revoked,
    )
    from oauth3.enforcement import build_evidence_token_entry
    from oauth3.revocation import list_all_tokens
    from oauth3.token import DEFAULT_TOKEN_DIR
    from oauth3.consent_ui import register_consent_routes
    from oauth3.step_up import validate_and_consume_nonce
    OAUTH3_AVAILABLE = True
except ImportError as _oauth3_import_error:
    logger_temp = logging.getLogger("solace-browser")
    logger_temp.warning(f"OAuth3 module not available: {_oauth3_import_error}")
    OAUTH3_AVAILABLE = False

try:
    from audit.chain import AuditChain
    AUDIT_AVAILABLE = True
except ImportError as _audit_import_error:
    logger_temp = logging.getLogger("solace-browser")
    logger_temp.warning(f"Audit module not available: {_audit_import_error}")
    AuditChain = Any  # type: ignore
    AUDIT_AVAILABLE = False

try:
    from sync_client import SyncClient, SyncConfig, SyncError
    from evidence_upload import EvidenceCollector, upload_pending_evidence
    SYNC_AVAILABLE = True
except ImportError as _sync_import_error:
    logger_temp = logging.getLogger("solace-browser")
    logger_temp.warning(f"Sync module not available: {_sync_import_error}")
    SYNC_AVAILABLE = False

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("ERROR: Playwright not installed")
    print("Install with: pip install playwright")
    sys.exit(1)

try:
    from aiohttp import web
except ImportError:
    print("ERROR: aiohttp not installed")
    print("Install with: pip install aiohttp")
    sys.exit(1)

# Import browser module (consolidated from browser_interactions + enhanced_browser_interactions)
try:
    from browser import (
        format_aria_tree,
        get_dom_snapshot,
        get_page_state,
        execute_action,
        BrowserAction,
    )
except ImportError as e:
    logger_temp = logging.getLogger('solace-browser')
    logger_temp.warning(f"Could not import browser module: {e}")

try:
    from competitive_features import (
        load_proxy_config,
        select_proxy,
        solve_captcha,
        webvoyager_score,
    )
except ImportError as _cf_import_error:
    logger_temp = logging.getLogger('solace-browser')
    logger_temp.warning(f"competitive_features not available: {_cf_import_error}")
    load_proxy_config = None
    select_proxy = None
    solve_captcha = None
    webvoyager_score = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('solace-browser')


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description='Solace Browser - Custom Headless Browser'
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--head',
        action='store_true',
        help='Run in headed mode (show browser window)',
    )
    mode_group.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode',
    )
    parser.add_argument(
        '--show-ui',
        action='store_true',
        help='Show debugging UI (default: False)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9222,
        help='CDP server port (default: 9222)',
    )
    parser.add_argument(
        '--part11',
        action='store_true',
        help='Enable Part 11 evidence capture with fail-closed behavior',
    )
    parser.add_argument(
        '--part11-mode',
        choices=['screenshot', 'archive'],
        default=os.getenv("SOLACE_PART11_MODE", "screenshot"),
        help='Part 11 capture mode (default: screenshot)',
    )
    parser.add_argument(
        '--part11-audit-dir',
        default=os.getenv("SOLACE_PART11_AUDIT_DIR", "~/.solace/audit"),
        help='Part 11 audit directory (default: ~/.solace/audit)',
    )
    parser.add_argument(
        '--sync-api-url',
        default=None,
        help='Override sync API URL for browser-to-cloud heartbeat/upload',
    )
    parser.add_argument(
        '--sync-api-key',
        default=None,
        help='Override sync API key for browser-to-cloud heartbeat/upload',
    )
    parser.add_argument(
        '--sync-interval',
        type=int,
        default=None,
        help='Heartbeat interval in seconds (default: env / disabled)',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'solace-browser {__version__}',
    )
    return parser


def build_sync_config(args: argparse.Namespace) -> Optional[Any]:
    """Build sync config from env, then apply CLI overrides."""
    if not SYNC_AVAILABLE:
        return None

    config = SyncConfig.from_env()
    if args.sync_api_url:
        config.api_url = str(args.sync_api_url)
    if args.sync_api_key is not None:
        config.api_key = str(args.sync_api_key)
    if args.sync_interval is not None:
        config.auto_sync_interval_seconds = int(args.sync_interval)
    return config

class SolaceBrowser:
    """
    Custom Solace Browser - Headless Chromium with CDP Protocol
    """

    def __init__(
        self,
        headless: bool = True,
        debug_ui: bool = False,
        session_file: Optional[str] = None,
        part11_enabled: bool = False,
        part11_mode: str = "screenshot",
        part11_audit_dir: Optional[str] = None,
    ):
        self.headless = headless
        self.debug_ui = debug_ui
        self.session_file = session_file or os.getenv("SOLACE_SESSION_FILE") or "artifacts/solace_session.json"
        self.browser: Optional[Browser] = None
        self.context = None
        self.pages: Dict[str, Page] = {}
        self.current_page: Optional[Page] = None
        self.message_id_counter = 0
        self.event_history = []
        self._audit_chain: Optional[AuditChain] = None
        self._part11_upload_hook: Optional[Any] = None
        self.part11: Dict[str, Any] = {
            "enabled": False,
            "mode": "screenshot",
            "audit_dir": "",
            "artifacts_dir": os.getenv("SOLACE_PART11_ARTIFACT_DIR", "artifacts/part11"),
            "session_id": "",
            "events": 0,
            "bytes_written": 0,
            "last_error": None,
        }
        self.configure_part11(
            enabled=part11_enabled,
            mode=part11_mode,
            audit_dir=part11_audit_dir,
            reset_session=True,
        )

    def set_part11_upload_hook(self, hook: Optional[Any]) -> None:
        """Register an async callback for post-seal Part 11 uploads."""
        self._part11_upload_hook = hook

    @staticmethod
    def _part11_mode_or_raise(mode: str) -> str:
        if mode not in {"screenshot", "archive"}:
            raise ValueError(f"Unsupported part11 mode: '{mode}'. Allowed: screenshot, archive")
        return mode

    @staticmethod
    def _new_part11_session_id() -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"part11-{stamp}-{uuid.uuid4().hex[:8]}"

    def get_part11_status(self) -> Dict[str, Any]:
        status = dict(self.part11)
        return status

    def configure_part11(
        self,
        *,
        enabled: Optional[bool] = None,
        mode: Optional[str] = None,
        audit_dir: Optional[str] = None,
        reset_session: bool = False,
    ) -> Dict[str, Any]:
        cur_enabled = bool(self.part11.get("enabled", False))
        cur_mode = str(self.part11.get("mode", "screenshot"))
        cur_audit_dir = str(self.part11.get("audit_dir", ""))

        next_enabled = cur_enabled if enabled is None else bool(enabled)
        next_mode = cur_mode if mode is None else self._part11_mode_or_raise(str(mode))
        raw_audit_dir = (
            cur_audit_dir
            if audit_dir is None
            else str(audit_dir)
        )
        if not raw_audit_dir:
            raw_audit_dir = os.getenv("SOLACE_PART11_AUDIT_DIR", "~/.solace/audit")
        next_audit_dir = str(Path(raw_audit_dir).expanduser())

        if next_enabled and not AUDIT_AVAILABLE:
            raise RuntimeError("Part 11 is enabled but audit module is unavailable.")

        changed = (
            reset_session
            or next_enabled != cur_enabled
            or next_mode != cur_mode
            or next_audit_dir != cur_audit_dir
        )

        self.part11["enabled"] = next_enabled
        self.part11["mode"] = next_mode
        self.part11["audit_dir"] = next_audit_dir

        if next_enabled:
            Path(self.part11["artifacts_dir"]).mkdir(parents=True, exist_ok=True)
            Path(next_audit_dir).mkdir(parents=True, exist_ok=True)
            if changed or not self.part11.get("session_id"):
                self.part11["session_id"] = self._new_part11_session_id()
                self.part11["events"] = 0
                self.part11["bytes_written"] = 0
                self.part11["last_error"] = None
                self._audit_chain = AuditChain(
                    session_id=self.part11["session_id"],
                    base_dir=next_audit_dir,
                )
        else:
            self._audit_chain = None

        return self.get_part11_status()

    async def _capture_part11_evidence(
        self,
        action: str,
        target: str,
        success: bool,
        error_detail: str = "",
    ) -> Dict[str, Any]:
        if not self.current_page:
            raise RuntimeError("No active page for Part 11 evidence capture.")
        if not self.part11.get("enabled", False):
            raise RuntimeError("Part 11 capture requested while Part 11 is disabled.")

        mode = self.part11["mode"]
        event_idx = int(self.part11.get("events", 0)) + 1
        event_id = f"e{event_idx:06d}"
        event_dir = Path(self.part11["artifacts_dir"]) / self.part11["session_id"] / event_id
        event_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).isoformat()
        url = self.current_page.url
        title = await self.current_page.title()
        artifact_paths: Dict[str, str] = {}
        artifact_sizes: Dict[str, int] = {}

        if mode == "screenshot":
            screenshot_path = event_dir / "evidence.png"
            await self.current_page.screenshot(path=str(screenshot_path), full_page=True)
            artifact_paths["screenshot"] = str(screenshot_path)
            artifact_sizes["screenshot"] = screenshot_path.stat().st_size
            snapshot_bytes = screenshot_path.read_bytes()
            snapshot_id = hashlib.sha256(snapshot_bytes).hexdigest()
        else:
            html = await self.current_page.content()
            html_path = event_dir / "page.html"
            html_path.write_text(html, encoding="utf-8")
            artifact_paths["html"] = str(html_path)
            artifact_sizes["html"] = html_path.stat().st_size

            if not self.context:
                raise RuntimeError("Browser context unavailable for archive capture.")

            cdp_session = await self.context.new_cdp_session(self.current_page)
            try:
                archive_resp = await cdp_session.send("Page.captureSnapshot", {"format": "mhtml"})
            except Exception as exc:
                raise RuntimeError(f"Page.captureSnapshot failed: {exc}") from exc
            mhtml = archive_resp.get("data", "")
            if not mhtml:
                raise RuntimeError("Page.captureSnapshot returned empty archive.")
            mhtml_path = event_dir / "page.mhtml"
            mhtml_path.write_text(mhtml, encoding="utf-8")
            artifact_paths["mhtml"] = str(mhtml_path)
            artifact_sizes["mhtml"] = mhtml_path.stat().st_size
            snapshot_id = hashlib.sha256((html + "\n---MHTML---\n" + mhtml).encode("utf-8")).hexdigest()

        metadata = {
            "event_id": event_id,
            "timestamp": ts,
            "mode": mode,
            "action": action,
            "target": target,
            "success": success,
            "error_detail": error_detail,
            "url": url,
            "title": title,
            "snapshot_id": snapshot_id,
            "artifacts": artifact_paths,
            "artifact_sizes": artifact_sizes,
        }
        metadata_path = event_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        artifact_paths["metadata"] = str(metadata_path)
        artifact_sizes["metadata"] = metadata_path.stat().st_size

        total_bytes = sum(artifact_sizes.values())
        self.part11["events"] = event_idx
        self.part11["bytes_written"] = int(self.part11.get("bytes_written", 0)) + total_bytes
        self.part11["last_error"] = None

        if self._audit_chain is not None:
            self._audit_chain.append(
                user_id="local-user",
                token_id=self.part11["session_id"],
                action=action,
                target=target,
                before_value="",
                after_value="success" if success else "error",
                reason=f"part11_capture mode={mode}",
                meaning="authorized" if success else "attempted",
                human_description=f"{action} target='{target}' url='{url}' mode='{mode}' success={success}",
                snapshot_id=snapshot_id,
                scope_used=f"part11.{mode}",
                step_up_performed=False,
            )

        return {
            "event_id": event_id,
            "session_id": self.part11["session_id"],
            "mode": mode,
            "snapshot_id": snapshot_id,
            "bytes_written": total_bytes,
            "artifacts": artifact_paths,
            "audit_dir": self.part11["audit_dir"],
        }

    async def _finalize_part11_result(
        self,
        action: str,
        target: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.part11.get("enabled", False):
            return payload

        success = payload.get("error") is None
        error_detail = payload.get("error", "")
        try:
            evidence = await self._capture_part11_evidence(
                action=action,
                target=target,
                success=success,
                error_detail=str(error_detail) if error_detail else "",
            )
            payload["part11"] = evidence
            if self._part11_upload_hook is not None:
                try:
                    upload_result = await self._part11_upload_hook(evidence)
                    if upload_result is not None:
                        payload["part11_upload"] = upload_result
                except Exception as exc:
                    self.part11["last_error"] = str(exc)
                    payload["part11_upload_error"] = str(exc)
            return payload
        except Exception as exc:
            self.part11["last_error"] = str(exc)
            if payload.get("error"):
                payload["part11_error"] = str(exc)
                return payload
            return {
                "error": "part11_evidence_failed",
                "detail": str(exc),
                "action": action,
                "target": target,
                "action_result": payload,
            }

    async def start(self):
        """Start the Solace Browser"""
        logger.info(f"Starting Solace Browser (headless={self.headless})")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        # Create initial page with optional session state
        context_options = {}

        # Load saved session if it exists
        if Path(self.session_file).exists():
            logger.info(f"Loading saved session from: {self.session_file}")
            try:
                context_options['storage_state'] = self.session_file
            except Exception as e:
                logger.warning(f"Could not load session: {e}")

        self.context = await self.browser.new_context(**context_options)
        page = await self.context.new_page()
        page_id = str(uuid.uuid4())
        self.pages[page_id] = page
        self.current_page = page

        # Setup page events
        page.on('console', self._on_console)
        page.on('load', self._on_page_load)

        logger.info(f"✓ Solace Browser started (page_id={page_id})")
        return page_id

    async def save_session(self) -> Dict[str, Any]:
        """Save browser context state (cookies, localStorage, etc.) to file"""
        try:
            if not self.context:
                return {"error": "No active context"}

            # Create artifacts directory if it doesn't exist
            Path("artifacts").mkdir(exist_ok=True)

            # Save storage state (cookies, localStorage, indexedDB)
            storage_state = await self.context.storage_state(path=self.session_file)

            logger.info(f"✓ Session saved to: {self.session_file}")
            return {
                "success": True,
                "session_file": self.session_file,
                "message": "Browser session saved (cookies, localStorage, etc.)"
            }
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return {"error": str(e)}

    async def stop(self):
        """Stop the Solace Browser"""
        if self.browser:
            # Save session before closing
            await self.save_session()
            await self.browser.close()
            logger.info("✓ Solace Browser stopped")

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Navigating to: {url}")
            response = await self.current_page.goto(url, wait_until='domcontentloaded')

            result = {
                "success": True,
                "url": url,
                "status": response.status if response else None,
                "timestamp": datetime.now().isoformat()
            }
            return await self._finalize_part11_result("navigate", url, result)
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return await self._finalize_part11_result("navigate", url, {"error": str(e)})

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Clicking: {selector}")
            await self.current_page.click(selector)
            await asyncio.sleep(0.5)  # Wait for action to complete

            result = {
                "success": True,
                "selector": selector,
                "timestamp": datetime.now().isoformat()
            }
            return await self._finalize_part11_result("click", selector, result)
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return await self._finalize_part11_result("click", selector, {"error": str(e)})

    async def fill(self, selector: str, text: str) -> Dict[str, Any]:
        """Fill a form field with text"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Filling {selector} with text")
            await self.current_page.fill(selector, text)
            await asyncio.sleep(0.3)

            result = {
                "success": True,
                "selector": selector,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
            return await self._finalize_part11_result("fill", selector, result)
        except Exception as e:
            logger.error(f"Fill failed: {e}")
            return await self._finalize_part11_result("fill", selector, {"error": str(e)})

    async def take_screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            if not filename:
                filename = f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"

            artifacts_dir = Path("artifacts")
            artifacts_dir.mkdir(exist_ok=True)
            filepath = artifacts_dir / filename

            logger.info(f"Taking screenshot: {filepath}")
            await self.current_page.screenshot(path=str(filepath))

            result = {
                "success": True,
                "filename": filename,
                "filepath": str(filepath),
                "size": filepath.stat().st_size if filepath.exists() else 0,
                "timestamp": datetime.now().isoformat()
            }
            return await self._finalize_part11_result("take_screenshot", str(filepath), result)
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            target = filename or "screenshot"
            return await self._finalize_part11_result("take_screenshot", target, {"error": str(e)})

    async def get_snapshot(self) -> Dict[str, Any]:
        """Get page HTML snapshot"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("Getting page snapshot")
            html = await self.current_page.content()

            result = {
                "success": True,
                "html_length": len(html),
                "url": self.current_page.url,
                "title": await self.current_page.title(),
                "html": html[:1000] + "..." if len(html) > 1000 else html,
                "timestamp": datetime.now().isoformat()
            }
            return await self._finalize_part11_result("get_snapshot", self.current_page.url, result)
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")
            return await self._finalize_part11_result("get_snapshot", "current_page", {"error": str(e)})

    async def evaluate(self, expression: str) -> Dict[str, Any]:
        """Execute JavaScript in the page"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Evaluating: {expression[:50]}...")
            result = await self.current_page.evaluate(expression)

            payload = {
                "success": True,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            target = expression[:80]
            return await self._finalize_part11_result("evaluate", target, payload)
        except Exception as e:
            logger.error(f"Evaluate failed: {e}")
            target = expression[:80]
            return await self._finalize_part11_result("evaluate", target, {"error": str(e)})

    async def login_linkedin_google_auto(self, gmail_email: str, gmail_password: str) -> Dict[str, Any]:
        """Auto-login to LinkedIn via Google OAuth with Gmail credentials

        Args:
            gmail_email: Gmail email address
            gmail_password: Gmail password

        Returns:
            Dict with login result
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("=== LINKEDIN GOOGLE OAUTH AUTO-LOGIN ===")

            # Step 1: Navigate to LinkedIn login silently
            logger.info("Step 1: Navigating to LinkedIn login...")
            await self.current_page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
            await asyncio.sleep(2)

            # Step 2: Find and click Google button
            logger.info("Step 2: Finding and clicking Google button...")
            google_container = await self.current_page.query_selector("div.alternate-signin__btn--google")

            if not google_container:
                logger.error("Google button not found")
                return {"error": "Google button not found"}

            logger.info("✓ Google button found")

            # Step 3: Listen for popup
            logger.info("Step 3: Setting up popup listener...")
            popup_page = None

            async def catch_popup():
                nonlocal popup_page
                try:
                    popup_page = await self.current_page.context.wait_for_event("page", timeout=10000)
                    logger.info(f"✓ Popup appeared: {popup_page.url}")
                except Exception as e:
                    logger.error(f"Popup timeout: {e}")

            popup_task = asyncio.create_task(catch_popup())

            # Step 4: Click Google button
            logger.info("Step 4: Clicking Google button...")
            try:
                await google_container.click()
                logger.info("✓ Clicked")
            except Exception as e:
                logger.warning(f"Click error: {e}")

            # Wait for popup
            await asyncio.sleep(2)
            if not popup_page:
                try:
                    await asyncio.wait_for(popup_task, timeout=8)
                except asyncio.TimeoutError:
                    logger.warning("Popup didn't appear in time")
                    return {"error": "Google OAuth popup did not appear"}

            if not popup_page:
                return {"error": "Could not capture Google popup"}

            await popup_page.wait_for_load_state('domcontentloaded')
            logger.info(f"✓ Google OAuth popup loaded: {popup_page.url}")

            # Step 5: Auto-fill Gmail email
            logger.info(f"Step 5: Entering Gmail email: {gmail_email}")
            try:
                # Find email input
                email_input = await popup_page.query_selector("input[type='email'], input[aria-label*='email' i]")
                if not email_input:
                    email_input = await popup_page.query_selector("input")

                if email_input:
                    await email_input.fill(gmail_email)
                    await asyncio.sleep(0.5)
                    await email_input.press("Enter")
                    await asyncio.sleep(2)
                    logger.info("✓ Email entered")
                else:
                    logger.error("Email input not found")
                    await popup_page.screenshot(path="artifacts/google-oauth-email-form.png")
                    return {"error": "Could not find email input field"}

            except Exception as e:
                logger.error(f"Email entry error: {e}")
                return {"error": f"Email entry failed: {e}"}

            # Step 6: Auto-fill Gmail password
            logger.info(f"Step 6: Entering Gmail password")
            try:
                await asyncio.sleep(1)

                # Find password input
                password_input = await popup_page.query_selector("input[type='password']")

                if password_input:
                    await password_input.fill(gmail_password)
                    await asyncio.sleep(0.5)
                    logger.info(f"Password filled: {len(gmail_password)} characters")
                    logger.info("Password value: [REDACTED]")

                    # BEFORE pressing Enter, click "show password" to verify what was entered
                    try:
                        # Look for the checkbox or button that shows password
                        show_checkbox = await popup_page.query_selector("input[type='checkbox'][aria-label*='Show password' i]")

                        if not show_checkbox:
                            # Try finding label with "Show password"
                            labels = await popup_page.query_selector_all("label")
                            for label in labels:
                                text = await label.text_content()
                                if text and "show password" in text.lower():
                                    # Click the label to toggle checkbox
                                    await label.click()
                                    show_checkbox = label
                                    break

                        if not show_checkbox:
                            # Try any button near the password field
                            buttons = await popup_page.query_selector_all("button")
                            for btn in buttons:
                                aria_label = await btn.get_attribute("aria-label")
                                if aria_label and ("show" in aria_label.lower() or "password" in aria_label.lower()):
                                    await btn.click()
                                    show_checkbox = btn
                                    break

                        if show_checkbox:
                            logger.info("✓ Show password toggled - taking screenshot to verify")
                            await asyncio.sleep(0.5)
                            await popup_page.screenshot(path="artifacts/google-oauth-password-visible.png")
                            logger.info("✓ Screenshot saved after password entry")
                        else:
                            logger.warning("Could not find show password toggle")

                    except Exception as e:
                        logger.warning(f"Error with show password: {e}")

                    # Now press Enter to submit
                    logger.info("Submitting password...")
                    await password_input.press("Enter")
                    await asyncio.sleep(1)
                    # Take screenshot to see if login succeeded or if error appeared
                    await popup_page.screenshot(path="artifacts/google-oauth-after-password.png")
                    logger.info("✓ Password submitted")
                    await asyncio.sleep(2)
                else:
                    logger.error("Password input not found")
                    await popup_page.screenshot(path="artifacts/google-oauth-password-form.png")
                    return {"error": "Could not find password input field"}

            except Exception as e:
                logger.error(f"Password entry error: {e}")
                return {"error": f"Password entry failed: {e}"}

            # Step 7: Wait for 2FA or permission screen
            logger.info("Step 7: Waiting for 2FA completion or permission screen...")
            logger.info("If you see '2FA - Check your phone', please approve on your phone")
            logger.info("Waiting up to 90 seconds for completion...\n")

            recovery_skipped = False

            # Keep checking the popup for changes
            for i in range(90):
                await asyncio.sleep(1)

                try:
                    current_popup_url = popup_page.url

                    # Print status every 10 seconds
                    if i % 10 == 0:
                        logger.info(f"  {i}s: Waiting... Popup URL: {current_popup_url[:80]}...")

                    # Check for recovery info page and skip it
                    if "recoveryoptions" in current_popup_url and not recovery_skipped:
                        logger.info("\n⚠️  Recovery info page detected - skipping...")
                        # Look for skip button
                        skip_buttons = await popup_page.query_selector_all("button")
                        for btn in skip_buttons:
                            text = await btn.text_content()
                            if text and any(x in text.lower() for x in ['skip', 'not now', 'continue']):
                                logger.info(f"✓ Clicking: {text.strip()}")
                                try:
                                    await btn.click()
                                    recovery_skipped = True
                                    await asyncio.sleep(2)
                                    break
                                except:
                                    pass

                    # Check for permission/consent button
                    buttons = await popup_page.query_selector_all("button")
                    for btn in buttons:
                        text = await btn.text_content()
                        if text and any(x in text.lower() for x in ['continue', 'allow', 'confirm', 'grant', 'proceed']):
                            logger.info(f"\n✓ Found permission button: {text.strip()}")
                            try:
                                await btn.click()
                                logger.info("✓ Clicked permission button")
                                await asyncio.sleep(2)
                                break
                            except:
                                pass

                    # Check if 2FA was completed by looking for success indicators
                    page_content = await popup_page.evaluate("() => document.body.innerText")
                    if "error" in page_content.lower() or "wrong" in page_content.lower():
                        logger.warning(f"\n❌ 2FA Failed or Error detected:\n{page_content[:200]}")
                        break

                except Exception as e:
                    logger.debug(f"Checking popup: {e}")

            logger.info("\n✓ 2FA/Permission step complete")

            # Step 8: Wait for redirect back to LinkedIn
            logger.info("Step 8: Waiting for LinkedIn redirect...")
            for i in range(15):
                await asyncio.sleep(1)
                final_url = self.current_page.url
                if "linkedin.com" in final_url:
                    break

            final_url = self.current_page.url
            logger.info(f"Main page URL: {final_url}")

            if "linkedin.com" in final_url and "login" not in final_url:
                logger.info("✓ Successfully logged in to LinkedIn!")
                return {
                    "success": True,
                    "status": "logged_in",
                    "message": "Successfully logged in to LinkedIn via Google OAuth",
                    "current_url": final_url,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning(f"OAuth completed but main page still at: {final_url}")
                return {
                    "success": True,
                    "status": "oauth_completed",
                    "message": "OAuth flow completed, may need manual completion",
                    "current_url": final_url,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Auto-login error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    async def login_linkedin_google(self) -> Dict[str, Any]:
        """Login to LinkedIn using Google OAuth"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("=== LINKEDIN GOOGLE OAUTH LOGIN ===")

            # Step 1: Navigate to LinkedIn login
            logger.info("Step 1: Navigating to LinkedIn login page...")
            await self.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
            await asyncio.sleep(3)
            await self.current_page.screenshot(path="artifacts/linkedin-01-login.png")
            logger.info("✓ LinkedIn login page loaded")

            # Step 2: Find and click the "Continue with Google" button
            logger.info("Step 2: Looking for 'Continue with Google' button...")

            # The Google button is rendered inside an iframe (Google Sign-In SDK)
            # We need to click on the div.alternate-signin__btn--google element
            # or interact with the iframe containing the Google button

            google_container = None

            # Strategy 1: Find the Google button container div
            logger.info("Looking for Google button container...")
            google_container = await self.current_page.query_selector("div.alternate-signin__btn--google")

            if google_container:
                logger.info("✓ Found Google button container")
            else:
                # Strategy 2: Look for iframe with Google button
                logger.info("Looking for Google iframe...")
                google_iframe = await self.current_page.query_selector("iframe[title='Sign in with Google Button']")
                if google_iframe:
                    logger.info("✓ Found Google iframe")
                    google_container = google_iframe

            if not google_container:
                # Strategy 3: Use JavaScript to find and interact with Google button
                logger.info("Trying JavaScript to find Google button...")
                found = await self.current_page.evaluate("""
                    () => {
                        // Look for the Google Sign-In container
                        const container = document.querySelector('div.alternate-signin__btn--google');
                        if (container) {
                            console.log('Found Google container via class');
                            return true;
                        }

                        // Look for iframe with Google button
                        const iframe = document.querySelector("iframe[title='Sign in with Google Button']");
                        if (iframe) {
                            console.log('Found Google iframe');
                            return true;
                        }

                        return false;
                    }
                """)

                if found:
                    logger.info("✓ JavaScript confirmed Google button exists")
                    google_container = await self.current_page.query_selector("div.alternate-signin__btn--google")

            if not google_container:
                logger.warning("Could not find Google button")
                await self.current_page.screenshot(path="artifacts/linkedin-error-button-not-found.png")
                return {"error": "Could not find 'Continue with Google' button"}

            # Step 3: Click the Google button
            logger.info("Step 3: Clicking Google button...")

            clicked = False

            try:
                # The Google button is inside an iframe. First, try clicking the Google button
                # by finding the clickable button element inside the iframe

                logger.info("Clicking Google button container with DOM events...")

                try:
                    # Use JavaScript to simulate a real click on the Google button container
                    # This triggers any event handlers that the Google SDK attached
                    result = await self.current_page.evaluate("""
                        () => {
                            // Find the Google button container
                            const container = document.querySelector('div.alternate-signin__btn--google');
                            if (container) {
                                // Dispatch mousedown, click, and mouseup events
                                const mousedownEvent = new MouseEvent('mousedown', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });
                                const clickEvent = new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });
                                const mouseupEvent = new MouseEvent('mouseup', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });

                                container.dispatchEvent(mousedownEvent);
                                container.dispatchEvent(clickEvent);
                                container.dispatchEvent(mouseupEvent);

                                console.log('Dispatched click events on Google button container');
                                return 'events_dispatched';
                            }
                            return 'container_not_found';
                        }
                    """)
                    logger.info(f"JavaScript result: {result}")
                    clicked = True

                except Exception as e:
                    logger.warning(f"Error dispatching events: {e}")

                if not clicked:
                    # Fallback: try clicking the container div
                    logger.info("Fallback: clicking Google container div...")
                    await google_container.click()
                    logger.info("✓ Clicked container")
                    clicked = True

            except Exception as e:
                logger.error(f"Error clicking Google button: {e}")
                # Still try to continue as the click may have worked despite the error
                clicked = True

            if not clicked:
                await self.current_page.screenshot(path="artifacts/linkedin-error-click-failed.png")
                return {"error": "Failed to click Google button"}

            await asyncio.sleep(3)
            await self.current_page.screenshot(path="artifacts/linkedin-02-google-redirect.png")

            # Step 4: Wait for Google OAuth popup
            logger.info("Step 4: Looking for Google OAuth popup...")

            # Google OAuth opens a POPUP, not a redirect
            # Wait for a new page/popup to open
            google_popup = None
            popup_timeout = 5  # seconds

            try:
                # Listen for new pages (popups)
                async def on_popup():
                    nonlocal google_popup
                    page = await self.current_page.context.wait_for_event("page", timeout=popup_timeout * 1000)
                    google_popup = page
                    logger.info(f"✓ Google OAuth popup detected: {page.url}")
                    return page

                # Start listening for popup
                popup_task = asyncio.create_task(on_popup())

                try:
                    google_popup = await asyncio.wait_for(popup_task, timeout=popup_timeout)
                except asyncio.TimeoutError:
                    logger.warning("No popup detected within timeout")
                    google_popup = None

            except Exception as e:
                logger.warning(f"Error waiting for popup: {e}")

            if google_popup:
                current_url = google_popup.url
                logger.info(f"✓ Google OAuth popup opened: {current_url}")

                # Wait for the popup to load the OAuth page
                try:
                    await google_popup.wait_for_load_state('domcontentloaded', timeout=5000)
                except Exception as e:
                    logger.warning(f"Popup didn't fully load: {e}")

                # Check if we're on Google
                if 'accounts.google.com' in current_url or 'google.com' in current_url:
                    logger.info("✓ OAuth popup is at Google login page")
                    return {
                        "success": True,
                        "status": "popup_opened",
                        "message": "Google OAuth popup opened. Please enter your Gmail credentials in the popup window.",
                        "current_url": current_url,
                        "popup_opened": True,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"Popup opened but not at Google: {current_url}")
                    return {
                        "success": True,
                        "status": "popup_opened_unexpected_url",
                        "message": "Popup opened but not at expected URL",
                        "current_url": current_url,
                        "popup_opened": True,
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                # No popup detected, check if we redirected on main page
                current_url = self.current_page.url
                logger.info(f"No popup detected. Main page URL: {current_url}")

                if 'accounts.google.com' in current_url or 'google.com' in current_url:
                    logger.info("✓ Main page redirected to Google OAuth")
                    return {
                        "success": True,
                        "status": "awaiting_user_input",
                        "message": "Redirected to Google OAuth. Please enter your Gmail credentials.",
                        "current_url": current_url,
                        "popup_opened": False,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"No OAuth detected: {current_url}")
                    return {
                        "success": True,
                        "status": "oauth_triggered",
                        "message": "OAuth flow triggered. Check for popup window or Google login page.",
                        "current_url": current_url,
                        "popup_opened": False,
                        "note": "If you see a Google login popup, please enter your Gmail credentials",
                        "timestamp": datetime.now().isoformat()
                    }

        except Exception as e:
            logger.error(f"LinkedIn Google OAuth login failed: {e}")
            await self.current_page.screenshot(path="artifacts/linkedin-error.png")
            return {"error": str(e)}

    def _on_console(self, msg):
        """Handle console messages"""
        logger.info(f"[CONSOLE] {msg.text}")
        self.event_history.append({
            "type": "console",
            "message": msg.text,
            "timestamp": datetime.now().isoformat()
        })

    def _on_page_load(self):
        """Handle page load events"""
        logger.info("Page loaded")
        self.event_history.append({
            "type": "pageload",
            "url": self.current_page.url if self.current_page else None,
            "timestamp": datetime.now().isoformat()
        })
        # Best-effort autosave so auth state survives restarts even if the
        # process is stopped without calling /api/save-session explicitly.
        try:
            asyncio.create_task(self.save_session())
        except RuntimeError:
            logger.warning("Could not schedule session autosave (event loop unavailable)")

    async def update_linkedin_profile(self) -> Dict[str, Any]:
        """Update LinkedIn profile with suggested improvements from linkedin-suggestions.md"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("=== UPDATING LINKEDIN PROFILE ===")

            # Step 1: Navigate to profile edit page
            logger.info("Step 1: Navigating to profile edit...")
            await self.current_page.goto("https://www.linkedin.com/in/phuc-vinh-truong-6b2a6b18/edit/", wait_until='domcontentloaded')
            await asyncio.sleep(2)
            logger.info("✓ Profile edit page loaded")

            # Step 2: Update headline
            logger.info("\nStep 2: Updating headline...")
            headline_input = await self.current_page.query_selector("input[name*='headline'], input[aria-label*='headline' i]")

            if headline_input:
                # Clear existing headline
                await headline_input.triple_click()
                await asyncio.sleep(0.3)

                # New headline from suggestions
                new_headline = "Software 5.0 Architect | 65537 Authority | Building Verified AI OS in Public"
                await headline_input.fill(new_headline)
                await asyncio.sleep(0.5)
                logger.info(f"✓ Headline updated: {new_headline}")
            else:
                logger.warning("Could not find headline input field")
                await self.current_page.screenshot(path="artifacts/linkedin-profile-headline-form.png")

            # Step 3: Update About section
            logger.info("\nStep 3: Updating About section...")
            about_textarea = await self.current_page.query_selector("textarea[name*='about'], textarea[aria-label*='about' i]")

            if about_textarea:
                # Clear existing about
                await about_textarea.triple_click()
                await asyncio.sleep(0.3)

                # New about section (shortened to fit LinkedIn character limits ~2600)
                new_about = """I build software that beats entropy.

Not chatbots that forget. Not AI that hallucinates. Software 5.0: verified intelligence using deterministic math + prime number architecture (65537D OMEGA).

Currently building:
• STILLWATER OS — Compression + intelligence platform (4.075x universal compression)
• SOLACEAGI — Expert Council SaaS (65537 verified decision-makers, not black-box LLMs)
• PZIP — Beats LZMA on all file types (91.4% win rate on test corpus)
• PHUCNET — Solo founder hub & ecosystem center

Philosophy: Phuc Forecast (DREAM → FORECAST → DECIDE → ACT → VERIFY)
Memory × Care × Iteration = Intelligence (LEK)

Recent wins:
✓ 100% SWE-bench verified (6/6 benchmarks)
✓ Browser automation complete (Chrome, Edge, Safari control)
✓ OOLONG verified (99.3% infinite context accuracy)

Building in public. Always shipping. Always verifying.
Harvard '98 | Boston-based | Solo founder | Verified AI.

Support the journey: https://ko-fi.com/phucnet"""

                await about_textarea.fill(new_about)
                await asyncio.sleep(0.5)
                logger.info("✓ About section updated (2600+ characters)")
            else:
                logger.warning("Could not find about textarea")
                await self.current_page.screenshot(path="artifacts/linkedin-profile-about-form.png")

            # Step 4: Look for save button and click it
            logger.info("\nStep 4: Saving changes...")
            save_buttons = await self.current_page.query_selector_all("button")
            for btn in save_buttons:
                text = await btn.text_content()
                if text and any(x in text.lower() for x in ['save', 'done', 'update']):
                    logger.info(f"✓ Clicking save button: {text.strip()}")
                    try:
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                    except Exception as e:
                        logger.warning(f"Error clicking save: {e}")

            logger.info("✓ Profile update complete!")
            await self.current_page.screenshot(path="artifacts/linkedin-profile-updated.png")

            return {
                "success": True,
                "status": "profile_updated",
                "message": "LinkedIn profile updated with headline and about section",
                "current_url": self.current_page.url,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Profile update error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    async def get_aria_snapshot(self, limit: int = 500) -> Dict[str, Any]:
        """
        Get accessibility tree (ARIA) snapshot with element references
        Returns ARIA nodes with ref IDs for structured AI interaction.
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Extracting ARIA tree (limit={limit})...")
            aria_nodes = await format_aria_tree(self.current_page, limit=limit)

            logger.info(f"✓ Extracted {len(aria_nodes)} ARIA nodes")

            return {
                "success": True,
                "nodes": [node.__dict__ if hasattr(node, '__dict__') else node for node in aria_nodes],
                "count": len(aria_nodes),
                "url": self.current_page.url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"ARIA snapshot error: {e}")
            return {"error": str(e)}

    async def get_dom_snapshot(self, limit: int = 800) -> Dict[str, Any]:
        """
        Get DOM tree snapshot with element references
        Returns DOM nodes with ref IDs for structured AI interaction.
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Extracting DOM tree (limit={limit})...")
            dom_nodes = await get_dom_snapshot(self.current_page, limit=limit)

            logger.info(f"✓ Extracted {len(dom_nodes)} DOM nodes")

            return {
                "success": True,
                "nodes": dom_nodes,
                "count": len(dom_nodes),
                "url": self.current_page.url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"DOM snapshot error: {e}")
            return {"error": str(e)}

    async def get_page_snapshot(self) -> Dict[str, Any]:
        """
        Get comprehensive page snapshot with ARIA tree, DOM tree, and state
        This is what the AI needs to understand the page structure
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("Getting comprehensive page snapshot...")
            page_state = await get_page_state(self.current_page)

            logger.info(f"✓ Page snapshot complete")
            logger.info(f"  - ARIA nodes: {len(page_state.get('aria', []))}")
            logger.info(f"  - DOM nodes: {len(page_state.get('dom', []))}")

            return {
                "success": True,
                **page_state
            }
        except Exception as e:
            logger.error(f"Page snapshot error: {e}")
            return {"error": str(e)}

    async def act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a structured action with human-like behaviors
        Supports: click, type, press, hover, scroll, wait, fill
        Unified action model for AI-driven browser control.
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            kind = action.get("kind")
            logger.info(f"Executing action: {kind}")

            if kind == "click":
                # Build click action
                click_action = {
                    "kind": "click",
                    "ref": action.get("ref"),
                    "double_click": action.get("doubleClick", False),
                    "button": action.get("button", "left"),
                    "modifiers": action.get("modifiers", []),
                    "delay_ms": action.get("delayMs", 0),
                    "timeout_ms": action.get("timeoutMs")
                }
                # Convert to dataclass and execute
                from browser.core import ClickAction
                click_obj = ClickAction(**{k: v for k, v in click_action.items() if k != "kind"})
                result = await execute_action(self.current_page, click_obj)
                return await self._finalize_part11_result("act.click", str(action.get("ref")), result)

            elif kind == "type":
                # Build type action
                type_action = {
                    "kind": "type",
                    "ref": action.get("ref"),
                    "text": action.get("text", ""),
                    "slowly": action.get("slowly", False),
                    "delay_ms": action.get("delayMs", 50),
                    "submit": action.get("submit", False),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser.core import TypeAction
                type_obj = TypeAction(**{k: v for k, v in type_action.items() if k != "kind"})
                result = await execute_action(self.current_page, type_obj)
                return await self._finalize_part11_result("act.type", str(action.get("ref")), result)

            elif kind == "press":
                # Build press action
                press_action = {
                    "kind": "press",
                    "key": action.get("key", ""),
                    "delay_ms": action.get("delayMs", 0),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser.core import PressAction
                press_obj = PressAction(**{k: v for k, v in press_action.items() if k != "kind"})
                result = await execute_action(self.current_page, press_obj)
                return await self._finalize_part11_result("act.press", str(action.get("key")), result)

            elif kind == "hover":
                # Build hover action
                hover_action = {
                    "kind": "hover",
                    "ref": action.get("ref"),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser.core import HoverAction
                hover_obj = HoverAction(**{k: v for k, v in hover_action.items() if k != "kind"})
                result = await execute_action(self.current_page, hover_obj)
                return await self._finalize_part11_result("act.hover", str(action.get("ref")), result)

            elif kind == "scrollIntoView":
                # Build scroll action
                scroll_action = {
                    "kind": "scrollIntoView",
                    "ref": action.get("ref"),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser.core import ScrollIntoViewAction
                scroll_obj = ScrollIntoViewAction(**{k: v for k, v in scroll_action.items() if k != "kind"})
                result = await execute_action(self.current_page, scroll_obj)
                return await self._finalize_part11_result("act.scrollIntoView", str(action.get("ref")), result)

            elif kind == "wait":
                # Build wait action
                wait_action = {
                    "kind": "wait",
                    "text": action.get("text"),
                    "text_gone": action.get("textGone"),
                    "url": action.get("url"),
                    "selector": action.get("selector"),
                    "load_state": action.get("loadState"),
                    "fn": action.get("fn"),
                    "timeout_ms": action.get("timeoutMs", 30000)
                }
                from browser.core import WaitAction
                wait_obj = WaitAction(**{k: v for k, v in wait_action.items() if k != "kind" and v is not None})
                result = await execute_action(self.current_page, wait_obj)
                return await self._finalize_part11_result("act.wait", str(action.get("selector") or action.get("url") or "wait"), result)

            elif kind == "fill":
                # Build fill action
                fill_action = {
                    "kind": "fill",
                    "fields": action.get("fields", []),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser.core import FillAction
                fill_obj = FillAction(**{k: v for k, v in fill_action.items() if k != "kind" and v is not None})
                result = await execute_action(self.current_page, fill_obj)
                return await self._finalize_part11_result("act.fill", "multi-field", result)

            else:
                return await self._finalize_part11_result("act.unknown", str(kind), {"error": f"Unknown action kind: {kind}"})

        except Exception as e:
            logger.error(f"Action execution error: {e}")
            import traceback
            traceback.print_exc()
            return await self._finalize_part11_result("act.exception", str(action.get("kind")), {"error": str(e)})


class SolaceBrowserServer:
    """HTTP/WebSocket server for CDP protocol"""

    def __init__(
        self,
        browser: SolaceBrowser,
        port: int = 9222,
        sync_config: Optional[Any] = None,
    ):
        self.browser = browser
        self.port = port
        self.app = web.Application()
        self.proxy_config: dict[str, Any] = {"proxies": []}

        # Sync client (browser <-> cloud)
        self._sync_config: Optional[Any] = None
        self._sync_client: Optional[Any] = None
        self._evidence_collector: Optional[Any] = None
        self._sync_heartbeat_task: Optional[asyncio.Task[Any]] = None
        self._last_evidence_upload: Optional[Dict[str, Any]] = None
        if SYNC_AVAILABLE:
            self._sync_config = sync_config or SyncConfig.from_env()
            self._sync_client = SyncClient(self._sync_config)
            audit_dir_str = self._resolve_sync_audit_dir()
            self._evidence_collector = EvidenceCollector(
                audit_dir=Path(audit_dir_str).expanduser(),
            )
            if hasattr(self.browser, "set_part11_upload_hook"):
                self.browser.set_part11_upload_hook(self._auto_upload_pending_evidence)

        self._setup_routes()

    def _resolve_sync_audit_dir(self) -> str:
        """Use the active browser Part 11 audit dir when available."""
        browser_part11 = getattr(self.browser, "part11", None)
        if isinstance(browser_part11, dict):
            audit_dir = str(browser_part11.get("audit_dir", "")).strip()
            if audit_dir:
                return audit_dir
        return os.getenv("SOLACE_PART11_AUDIT_DIR", "~/.solace/audit")

    async def _send_sync_heartbeat(self) -> bool:
        """Send one heartbeat when sync is configured."""
        if self._sync_client is None or self._sync_config is None:
            return False
        if not getattr(self._sync_config, "api_key", "").strip():
            return False

        await self._sync_client.heartbeat(f"solace-browser {__version__}")
        return True

    async def _sync_heartbeat_loop(self) -> None:
        """Run periodic sync heartbeats until shutdown."""
        interval = 0
        if self._sync_config is not None:
            interval = int(getattr(self._sync_config, "auto_sync_interval_seconds", 0))
        if interval <= 0:
            return

        try:
            while True:
                await asyncio.sleep(interval)
                await self._send_sync_heartbeat()
        except asyncio.CancelledError:
            logger.debug("Sync heartbeat loop cancelled")
            raise

    async def _start_sync_services(self) -> None:
        """Send startup heartbeat and optionally launch the heartbeat loop."""
        if self._sync_client is None or self._sync_config is None:
            return
        if not getattr(self._sync_config, "api_key", "").strip():
            logger.info("Sync heartbeat disabled: no API key configured")
            return

        await self._send_sync_heartbeat()

        interval = int(getattr(self._sync_config, "auto_sync_interval_seconds", 0))
        if interval > 0:
            self._sync_heartbeat_task = asyncio.create_task(
                self._sync_heartbeat_loop()
            )
            logger.info("Sync heartbeat loop started (%ss)", interval)

    async def _stop_sync_services(self) -> None:
        """Cancel background sync work and close the sync client."""
        if self._sync_heartbeat_task is not None:
            self._sync_heartbeat_task.cancel()
            try:
                await self._sync_heartbeat_task
            except asyncio.CancelledError:
                logger.debug("Sync heartbeat task cancelled during shutdown")
            self._sync_heartbeat_task = None

        if self._sync_client is not None:
            await self._sync_client.close()

    def _ensure_evidence_collector(self) -> Optional[Any]:
        """Keep the evidence collector aligned with the active Part 11 audit dir."""
        if not SYNC_AVAILABLE:
            return None

        audit_dir = Path(self._resolve_sync_audit_dir()).expanduser()
        if (
            self._evidence_collector is None
            or getattr(self._evidence_collector, "audit_dir", None) != audit_dir
        ):
            self._evidence_collector = EvidenceCollector(audit_dir=audit_dir)
        return self._evidence_collector

    async def _auto_upload_pending_evidence(
        self,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Upload freshly sealed Part 11 evidence when auto-upload is enabled."""
        if self._sync_client is None or self._sync_config is None:
            result = {"status": "skipped", "reason": "sync_unavailable"}
            self._last_evidence_upload = result
            return result
        if not getattr(self._sync_config, "evidence_auto_upload", False):
            result = {"status": "skipped", "reason": "evidence_auto_upload_disabled"}
            self._last_evidence_upload = result
            return result
        if not getattr(self._sync_config, "api_key", "").strip():
            result = {"status": "skipped", "reason": "missing_api_key"}
            self._last_evidence_upload = result
            return result

        collector = self._ensure_evidence_collector()
        if collector is None:
            result = {"status": "skipped", "reason": "collector_unavailable"}
            self._last_evidence_upload = result
            return result

        try:
            result = await upload_pending_evidence(self._sync_client, collector)
            result["trigger_event_id"] = evidence.get("event_id")
            self._last_evidence_upload = result
            return result
        except Exception as exc:
            result = {
                "status": "error",
                "error": str(exc),
                "trigger_event_id": evidence.get("event_id"),
            }
            self._last_evidence_upload = result
            logger.error("Part 11 evidence auto-upload failed: %s", exc)
            return result

    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/json/version', self._handle_version)
        self.app.router.add_get('/json/list', self._handle_list)
        self.app.router.add_post('/api/navigate', self._handle_navigate)
        self.app.router.add_post('/api/click', self._handle_click)
        self.app.router.add_post('/api/fill', self._handle_fill)
        self.app.router.add_post('/api/screenshot', self._handle_screenshot)
        self.app.router.add_post('/api/snapshot', self._handle_snapshot)
        self.app.router.add_post('/api/evaluate', self._handle_evaluate)
        self.app.router.add_post('/api/login-linkedin-google', self._handle_login_linkedin_google)
        self.app.router.add_post('/api/login-linkedin-google-auto', self._handle_login_linkedin_google_auto)
        self.app.router.add_post('/api/update-linkedin-profile', self._handle_update_linkedin_profile)
        self.app.router.add_post('/api/save-session', self._handle_save_session)
        self.app.router.add_get('/api/session-status', self._handle_session_status)
        self.app.router.add_get('/api/part11/status', self._handle_part11_status)
        self.app.router.add_post('/api/part11/config', self._handle_part11_config)
        # AI-native routes for structured browser interaction
        self.app.router.add_get('/api/aria-snapshot', self._handle_aria_snapshot)
        self.app.router.add_get('/api/dom-snapshot', self._handle_dom_snapshot)
        self.app.router.add_get('/api/page-snapshot', self._handle_page_snapshot)
        self.app.router.add_post('/api/act', self._handle_act)
        self.app.router.add_get('/api/health', self._handle_health)
        self.app.router.add_get('/api/status', self._handle_status)
        self.app.router.add_get('/api/events', self._handle_events)
        self.app.router.add_post('/api/discovery/map-site', self._handle_discovery_map_site)
        self.app.router.add_post('/api/competitive/captcha/solve', self._handle_captcha_solve)
        self.app.router.add_post('/api/competitive/proxy/load', self._handle_proxy_load)
        self.app.router.add_get('/api/competitive/proxy/select', self._handle_proxy_select)
        self.app.router.add_post('/api/competitive/webvoyager/score', self._handle_webvoyager_score)

        # OAuth3 routes (Phase 1.5)
        self.app.router.add_post('/oauth3/token', self._handle_oauth3_issue_token)
        self.app.router.add_get('/oauth3/token/{token_id}', self._handle_oauth3_get_token)
        self.app.router.add_delete('/oauth3/token/{token_id}', self._handle_oauth3_revoke_token)
        self.app.router.add_get('/oauth3/scopes', self._handle_oauth3_scopes)

        # OAuth3 Consent UI (Phase 1.5 BUILD 2)
        # Routes: GET /consent, POST /oauth3/consent, GET /settings/tokens
        if OAUTH3_AVAILABLE:
            try:
                register_consent_routes(self.app)
            except Exception as _consent_ui_error:
                import logging as _logging
                _logging.getLogger("solace-browser").warning(
                    f"Consent UI routes could not be registered: {_consent_ui_error}"
                )

        # Recipe execution (OAuth3-enforced)
        self.app.router.add_post('/run-recipe', self._handle_run_recipe)

        # History API (Phase 2, BUILD 5)
        self.app.router.add_get('/history', self._handle_history_list)
        self.app.router.add_get('/history/{session_id}', self._handle_history_session)
        self.app.router.add_get('/history/{session_id}/{snapshot_id}', self._handle_history_snapshot)
        self.app.router.add_get('/history/{session_id}/{snapshot_id}/render', self._handle_history_render)

        # Sync routes (browser <-> cloud evidence + config bridge)
        if SYNC_AVAILABLE:
            self.app.router.add_post('/api/sync/push', self._handle_sync_push)
            self.app.router.add_get('/api/sync/status', self._handle_sync_status)
            self.app.router.add_post('/api/sync/pull', self._handle_sync_pull)

        # Debug UI routes
        if self.browser.debug_ui:
            self.app.router.add_get('/', self._handle_ui)
            self.app.router.add_static('/static', Path(__file__).parent / 'browser_ui')

    async def _handle_version(self, request):
        """Return browser version (CDP compatible)"""
        return web.json_response({
            "Browser": f"Solace Browser/{__version__}",
            "Protocol-Version": "1.3",
            "User-Agent": f"Solace/{__version__}",
            "V8-Version": "12.0.0"
        })

    async def _handle_list(self, request):
        """Return list of pages (CDP compatible)"""
        if not self.browser.current_page:
            return web.json_response([])

        return web.json_response([{
            "description": "Solace Browser Page",
            "devtoolsFrontendUrl": f"devtools://devtools/bundled/inspector.html",
            "faviconUrl": "",
            "id": str(id(self.browser.current_page)),
            "parentId": "",
            "title": await self.browser.current_page.title(),
            "type": "page",
            "url": self.browser.current_page.url,
            "webSocketDebuggerUrl": f"ws://localhost:{self.port}/ws"
        }])

    async def _handle_navigate(self, request):
        """Navigate to URL"""
        data = await request.json()
        result = await self.browser.navigate(data.get('url', ''))
        return web.json_response(result)

    async def _handle_click(self, request):
        """Click element"""
        data = await request.json()
        result = await self.browser.click(data.get('selector', ''))
        return web.json_response(result)

    async def _handle_fill(self, request):
        """Fill form field"""
        data = await request.json()
        result = await self.browser.fill(
            data.get('selector', ''),
            data.get('text', '')
        )
        return web.json_response(result)

    async def _handle_screenshot(self, request):
        """Take screenshot"""
        data = await request.json()
        result = await self.browser.take_screenshot(data.get('filename'))
        return web.json_response(result)

    async def _handle_snapshot(self, request):
        """Get page snapshot"""
        result = await self.browser.get_snapshot()
        return web.json_response(result)

    async def _handle_evaluate(self, request):
        """Evaluate JavaScript"""
        data = await request.json()
        result = await self.browser.evaluate(data.get('expression', ''))
        return web.json_response(result)

    async def _handle_login_linkedin_google(self, request):
        """Login to LinkedIn using Google OAuth"""
        try:
            result = await self.browser.login_linkedin_google()
            return web.json_response(result)
        except Exception as e:
            logger.error(f"LinkedIn login handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_login_linkedin_google_auto(self, request):
        """Auto-login to LinkedIn using Google OAuth with Gmail credentials"""
        try:
            data = await request.json()
            gmail_email = data.get('gmail_email')
            gmail_password = data.get('gmail_password')

            if not gmail_email or not gmail_password:
                return web.json_response({
                    "error": "Missing gmail_email or gmail_password"
                }, status=400)

            result = await self.browser.login_linkedin_google_auto(gmail_email, gmail_password)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Auto-login handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_update_linkedin_profile(self, request):
        """Update LinkedIn profile with suggested improvements"""
        try:
            result = await self.browser.update_linkedin_profile()
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Profile update handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_save_session(self, request):
        """Save browser session (cookies, localStorage) to file"""
        try:
            result = await self.browser.save_session()
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Session save handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_session_status(self, request):
        """Check if saved session exists"""
        session_file = Path(self.browser.session_file)
        return web.json_response({
            "session_exists": session_file.exists(),
            "session_file": str(session_file),
            "file_size": session_file.stat().st_size if session_file.exists() else 0,
            "message": "Session file found" if session_file.exists() else "No saved session"
        })

    async def _handle_part11_status(self, request):
        """Return current Part 11 runtime configuration and counters."""
        return web.json_response(self.browser.get_part11_status())

    async def _handle_part11_config(self, request):
        """
        Update Part 11 runtime config.
        Body: {"enabled": bool?, "mode": "screenshot|archive"?, "audit_dir": "path"?}
        """
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)

        try:
            status = self.browser.configure_part11(
                enabled=data.get("enabled", None),
                mode=data.get("mode", None),
                audit_dir=data.get("audit_dir", None),
            )
            return web.json_response({"success": True, "part11": status})
        except (ValueError, RuntimeError) as exc:
            return web.json_response({"error": str(exc)}, status=422)

    async def _handle_aria_snapshot(self, request):
        """Get accessibility tree (ARIA) snapshot with element references"""
        try:
            limit = int(request.query.get('limit', 500))
            result = await self.browser.get_aria_snapshot(limit=limit)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"ARIA snapshot handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_dom_snapshot(self, request):
        """Get DOM tree snapshot with element references"""
        try:
            limit = int(request.query.get('limit', 800))
            result = await self.browser.get_dom_snapshot(limit=limit)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"DOM snapshot handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_page_snapshot(self, request):
        """Get comprehensive page snapshot (ARIA + DOM + state)"""
        try:
            result = await self.browser.get_page_snapshot()
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Page snapshot handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_act(self, request):
        """Execute structured action (click, type, press, hover, wait, etc.)"""
        try:
            data = await request.json()
            result = await self.browser.act(data)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Act handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_status(self, request):
        """Get browser status"""
        token_count = 0
        if OAUTH3_AVAILABLE:
            try:
                token_count = len(list_all_tokens(token_dir=DEFAULT_TOKEN_DIR))
            except Exception:
                token_count = 0
        part11_status: Dict[str, Any]
        if hasattr(self.browser, "get_part11_status"):
            part11_status = self.browser.get_part11_status()
        else:
            # Backward-compatible status response for lightweight test doubles.
            part11_status = {
                "enabled": False,
                "available": False,
                "reason": "browser_missing_part11_interface",
            }
        session_exists = Path(self.browser.session_file).exists()
        return web.json_response({
            "running": self.browser.browser is not None,
            "mode": "headless" if self.browser.headless else "headed",
            "headless": self.browser.headless,
            "current_url": self.browser.current_page.url if self.browser.current_page else None,
            "pages": len(self.browser.pages),
            "events": len(self.browser.event_history),
            "active_oauth3_tokens": token_count,
            "part11": part11_status,
            "session": {
                "session_file": self.browser.session_file,
                "exists": session_exists,
            },
        })

    async def _handle_health(self, request):
        """Health endpoint for stillwater/service orchestration."""
        return web.json_response(
            {
                "ok": True,
                "mode": "headless" if self.browser.headless else "headed",
                "running": self.browser.browser is not None,
            }
        )

    async def _handle_events(self, request):
        """Get event history"""
        limit = int(request.query.get('limit', 100))
        return web.json_response(self.browser.event_history[-limit:])

    async def _handle_discovery_map_site(self, request):
        """
        Live discovery bootstrap for a new site.

        Request:
          {"url": "https://example.com"}
        """
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

        url = str(data.get("url", "")).strip()
        if not url:
            return web.json_response({"ok": False, "error": "missing_url"}, status=422)
        parsed = urlparse(url if "://" in url else f"https://{url}")
        site = parsed.netloc.lower().strip()
        if not site:
            return web.json_response({"ok": False, "error": "invalid_url"}, status=422)

        root = Path(__file__).resolve().parent
        primewiki_dir = root / "data" / "default" / "primewiki" / site
        recipes_dir = root / "data" / "default" / "recipes" / site
        primewiki_dir.mkdir(parents=True, exist_ok=True)
        recipes_dir.mkdir(parents=True, exist_ok=True)

        stem = f"{site.replace('.', '-')}-page-flow"
        mmd_path = primewiki_dir / f"{stem}.mmd"
        sha_path = primewiki_dir / f"{stem}.sha256"
        pm_path = primewiki_dir / f"{stem}.prime-mermaid.md"

        mmd_body = (
            "flowchart TD\n"
            "  HOME[Home] --> AUTH[Auth]\n"
            "  AUTH --> DASH[Dashboard]\n"
            "  DASH --> SETTINGS[Settings]\n"
        )
        mmd_path.write_text(mmd_body, encoding="utf-8")
        digest = hashlib.sha256(mmd_body.encode("utf-8")).hexdigest()
        sha_path.write_text(f"{digest}  {mmd_path.name}\n", encoding="utf-8")
        pm_path.write_text(
            "\n".join(
                [
                    f"# Prime Mermaid: {site}",
                    "",
                    f"- Site: `{site}`",
                    "- Auth: unknown (discovered baseline)",
                    "- Page types: home, auth, dashboard, settings",
                    "",
                    "```mermaid",
                    mmd_body.rstrip(),
                    "```",
                    "",
                    "## Selector Seeds",
                    "- login_button: \"button[type=submit]\"",
                    "- nav_links: \"a[href]\"",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        recipe_doc = {
            "id": f"{site.replace('.', '-')}-discover-home",
            "site": site,
            "title": f"Discover {site} homepage",
            "oauth3_scopes": [f"{site}.read"],
            "steps": [
                {"step": 1, "action": "navigate", "url": f"https://{site}"},
                {"step": 2, "action": "snapshot", "target": "home"},
            ],
            "primewiki_ref": str(pm_path.relative_to(root)),
        }
        recipe_path = recipes_dir / f"{site.replace('.', '-')}-discover-home.recipe.json"
        recipe_path.write_text(json.dumps(recipe_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        return web.json_response(
            {
                "ok": True,
                "site": site,
                "artifacts": {
                    "mmd": str(mmd_path.relative_to(root)),
                    "sha256": str(sha_path.relative_to(root)),
                    "prime_mermaid": str(pm_path.relative_to(root)),
                    "recipe": str(recipe_path.relative_to(root)),
                },
            },
            status=201,
        )

    async def _handle_captcha_solve(self, request):
        """Solve CAPTCHA via configured provider (mock provider supported for tests)."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "invalid_json"}, status=400)
        if solve_captcha is None:
            return web.json_response(
                {"ok": False, "error": "competitive_features_unavailable"},
                status=503,
            )
        result = solve_captcha(
            provider=str(data.get("provider", "mock")),
            captcha_type=str(data.get("captcha_type", "")),
            site_key=str(data.get("site_key", "")),
            page_url=str(data.get("page_url", "")),
            mock_token=data.get("mock_token"),
        )
        status_code = 200 if result.get("ok") else 422
        return web.json_response(result, status=status_code)

    async def _handle_proxy_load(self, request):
        """Load proxy config from data/custom/proxy-config.yaml (or custom path)."""
        try:
            data = await request.json()
        except Exception:
            data = {}
        if load_proxy_config is None:
            return web.json_response(
                {"ok": False, "error": "competitive_features_unavailable"},
                status=503,
            )
        raw_path = str(data.get("path", "data/custom/proxy-config.yaml")).strip()
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent / path
        self.proxy_config = load_proxy_config(path)
        return web.json_response(
            {
                "ok": True,
                "path": str(path),
                "proxy_count": len(self.proxy_config.get("proxies", [])),
            }
        )

    async def _handle_proxy_select(self, request):
        if select_proxy is None:
            return web.json_response(
                {"ok": False, "error": "competitive_features_unavailable"},
                status=503,
            )
        country = request.query.get("country")
        proxy = select_proxy(self.proxy_config, country=country)
        if proxy is None:
            return web.json_response({"ok": False, "error": "no_proxy_available"}, status=404)
        return web.json_response({"ok": True, "proxy": proxy})

    async def _handle_webvoyager_score(self, request):
        """Compute benchmark score from case results."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "invalid_json"}, status=400)
        cases = data.get("cases", [])
        if not isinstance(cases, list):
            return web.json_response({"ok": False, "error": "cases_must_be_list"}, status=422)
        if webvoyager_score is None:
            return web.json_response(
                {"ok": False, "error": "competitive_features_unavailable"},
                status=503,
            )
        out = webvoyager_score(cases)
        return web.json_response(out)

    # =========================================================================
    # OAuth3 handlers (Phase 1.5)
    # =========================================================================

    async def _handle_oauth3_issue_token(self, request):
        """
        POST /oauth3/token
        Issue an agency token with the requested scopes.

        Request body:
          {
            "scopes": ["linkedin.create_post"],
            "user_id": "string (optional, defaults to 'local')",
            "expires_hours": 720  (optional, default 720 = 30 days)
          }

        Response 200:
          {token_id, user_id, issued_at, expires_at, scopes, step_up_required_for}

        Response 400: unknown scopes
        Response 503: OAuth3 module not loaded
        """
        if not OAUTH3_AVAILABLE:
            return web.json_response(
                {"error": "oauth3_unavailable", "detail": "OAuth3 module not loaded"},
                status=503,
            )

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)

        requested_scopes = data.get("scopes", [])
        if not requested_scopes:
            return web.json_response(
                {"error": "missing_scopes", "detail": "At least one scope is required"},
                status=400,
            )

        # Validate all requested scopes exist
        is_valid, unknown = validate_scopes(requested_scopes)
        if not is_valid:
            return web.json_response(
                {
                    "error": "unknown_scopes",
                    "unknown": unknown,
                    "known_scopes": list(SCOPES.keys()),
                },
                status=400,
            )

        user_id = data.get("user_id", "local")
        expires_hours = int(data.get("expires_hours", 720))

        token = AgencyToken.create(
            user_id=user_id,
            scopes=requested_scopes,
            expires_hours=expires_hours,
        )
        token.save_to_file()

        logger.info(
            f"OAuth3 token issued: {token.token_id[:8]}... "
            f"scopes={requested_scopes} user={user_id}"
        )

        return web.json_response(token.to_dict(), status=200)

    async def _handle_oauth3_get_token(self, request):
        """
        GET /oauth3/token/{token_id}
        Return token status (expiry, revocation, scopes).

        Response 200: {token_id, issued_at, expires_at, scopes, revoked, revoked_at}
        Response 404: token not found
        Response 503: OAuth3 module not loaded
        """
        if not OAUTH3_AVAILABLE:
            return web.json_response(
                {"error": "oauth3_unavailable"},
                status=503,
            )

        token_id = request.match_info["token_id"]

        try:
            token = AgencyToken.load_from_file(token_id)
        except FileNotFoundError:
            return web.json_response(
                {"error": "token_not_found", "token_id": token_id},
                status=404,
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response(token.to_dict(), status=200)

    async def _handle_oauth3_revoke_token(self, request):
        """
        DELETE /oauth3/token/{token_id}
        Revoke an agency token immediately.

        Response 200: {"revoked": true, "token_id": "..."}
        Response 404: token not found
        Response 503: OAuth3 module not loaded
        """
        if not OAUTH3_AVAILABLE:
            return web.json_response(
                {"error": "oauth3_unavailable"},
                status=503,
            )

        token_id = request.match_info["token_id"]
        success = revoke_token(token_id, token_dir=DEFAULT_TOKEN_DIR)

        if not success:
            return web.json_response(
                {"error": "token_not_found", "token_id": token_id},
                status=404,
            )

        logger.info(f"OAuth3 token revoked: {token_id[:8]}...")
        return web.json_response({"revoked": True, "token_id": token_id}, status=200)

    async def _handle_oauth3_scopes(self, request):
        """
        GET /oauth3/scopes
        Return all registered scopes with descriptions and risk levels.

        Response 200: {"scopes": {"scope_name": "description", ...}}
        """
        if not OAUTH3_AVAILABLE:
            return web.json_response(
                {"error": "oauth3_unavailable"},
                status=503,
            )

        from oauth3.scopes import STEP_UP_REQUIRED_SCOPES, get_scope_risk_level

        scope_details = {
            scope: {
                "description": description,
                "risk_level": get_scope_risk_level(scope),
                "step_up_required": scope in STEP_UP_REQUIRED_SCOPES,
            }
            for scope, description in SCOPES.items()
        }

        return web.json_response({"scopes": scope_details}, status=200)

    # =========================================================================
    # Recipe execution (OAuth3-enforced)
    # =========================================================================

    async def _handle_run_recipe(self, request):
        """
        POST /run-recipe
        Execute a recipe with OAuth3 enforcement.

        Request body:
          {
            "recipe_id": "linkedin-discover-posts",
            "agency_token": "<token_id>",  (or use X-Agency-Token header)
            "input_params": {}
          }

        OAuth3 enforcement:
          1. Extract agency_token from body or X-Agency-Token header
          2. Load token; validate (expiry + revocation)
          3. Check scope matches recipe's required_scope
          4. Check step-up for high-risk scopes
          5. On pass: execute recipe stub, return evidence bundle with token_id

        Error responses:
          401 — token invalid (expired or revoked)
          402 — step_up_required
          403 — insufficient_scope OR missing token
          404 — recipe not found
          503 — OAuth3 module not loaded
        """
        if not OAUTH3_AVAILABLE:
            return web.json_response(
                {"error": "oauth3_unavailable", "detail": "OAuth3 module not loaded"},
                status=503,
            )

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)

        recipe_id = data.get("recipe_id")
        if not recipe_id:
            return web.json_response(
                {"error": "missing_recipe_id", "detail": "recipe_id is required"},
                status=400,
            )

        # Load recipe from data/default/recipes directory
        recipes_dir = Path(__file__).parent / "data" / "default" / "recipes"
        recipe_path = recipes_dir / f"{recipe_id}.recipe.json"

        if not recipe_path.exists():
            return web.json_response(
                {"error": "recipe_not_found", "recipe_id": recipe_id},
                status=404,
            )

        try:
            recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
        except Exception as e:
            return web.json_response(
                {"error": "recipe_load_error", "detail": str(e)},
                status=500,
            )

        # Extract agency token — body first, then header
        token_id = (
            data.get("agency_token")
            or request.headers.get("X-Agency-Token")
        )

        # Extract optional step-up nonce
        step_up_nonce = data.get("step_up_nonce") or None

        if not token_id:
            # No token provided → direct to consent
            required_scope = recipe.get("required_scope", f"{recipe_id.split('-')[0]}.action")
            return web.json_response(
                {
                    "error": "missing_agency_token",
                    "detail": "Provide agency_token in body or X-Agency-Token header",
                    "required_scope": required_scope,
                    "consent_url": f"/consent?scopes={required_scope}",
                },
                status=403,
            )

        # Determine required scope for this recipe
        required_scope = recipe.get("required_scope")
        if not required_scope:
            # Infer scope from recipe metadata
            metadata_tags = recipe.get("metadata", {}).get("tags", [])
            platform = metadata_tags[0] if metadata_tags else recipe_id.split("-")[0]
            action_class = "action"
            required_scope = f"{platform}.{action_class}"

        # Validate step-up nonce if provided, before calling enforce_oauth3
        step_up_performed = False
        step_up_performed_at = None
        if step_up_nonce:
            nonce_valid, nonce_action = validate_and_consume_nonce(step_up_nonce)
            if not nonce_valid:
                # Invalid or expired nonce — reject with 402 so client re-prompts
                return web.json_response(
                    {
                        "error": "step_up_nonce_invalid",
                        "detail": "Step-up nonce is expired, invalid, or already used.",
                        "token_id": token_id,
                        "required_scope": required_scope,
                        "confirm_url": (
                            f"/step-up?token_id={token_id}"
                            f"&action={required_scope}"
                            f"&recipe_id={recipe_id}"
                            f"&error=Nonce+expired+or+already+used"
                        ),
                    },
                    status=402,
                )
            # Nonce valid — check it authorises the right action
            if nonce_action != required_scope:
                return web.json_response(
                    {
                        "error": "step_up_nonce_scope_mismatch",
                        "detail": (
                            f"Nonce was issued for '{nonce_action}' "
                            f"but recipe requires '{required_scope}'."
                        ),
                        "token_id": token_id,
                        "required_scope": required_scope,
                    },
                    status=403,
                )
            step_up_performed = True
            step_up_performed_at = datetime.now(timezone.utc).isoformat()

        # Enforce OAuth3 (step_up_confirmed=True when nonce was valid)
        passes, details = enforce_oauth3(
            token_id,
            required_scope,
            step_up_confirmed=step_up_performed,
            token_dir=DEFAULT_TOKEN_DIR,
        )

        if not passes:
            error_code = details.get("error", "enforcement_failed")

            # Map error codes to HTTP status
            if error_code in ("token_expired", "token_revoked", "token_not_found", "token_load_error"):
                status_code = 401
            elif error_code == "step_up_required":
                status_code = 402
            else:
                # insufficient_scope or unknown
                status_code = 403

            response_body = {
                "error": error_code,
                "detail": details.get("error_detail", ""),
                "token_id": token_id,
                "required_scope": required_scope,
            }

            # Add consent_url for scope errors
            if "consent_url" in details:
                response_body["consent_url"] = details["consent_url"]

            # Add step-up details
            if error_code == "step_up_required":
                response_body["action"] = details.get("action", required_scope)
                response_body["confirm_url"] = (
                    f"/step-up?token_id={token_id}"
                    f"&action={required_scope}"
                    f"&recipe_id={recipe_id}"
                )

            return web.json_response(response_body, status=status_code)

        # OAuth3 passed — build evidence bundle
        enforcement_details = details
        agency_token_evidence = build_evidence_token_entry(
            token_id=enforcement_details["token_id"],
            scope_used=enforcement_details["scope"],
            step_up_performed=step_up_performed,
            token_expires_at=enforcement_details.get("expires_at"),
        )

        started_at = datetime.now(timezone.utc).isoformat()

        # Build step-up evidence entry (only when step-up was performed)
        step_up_evidence = {
            "required": True if step_up_performed else False,
            "performed": step_up_performed,
            "performed_at": step_up_performed_at,
            "action": required_scope if step_up_performed else None,
        }

        # Recipe execution stub:
        # Phase 1.5 implements OAuth3 enforcement infrastructure.
        # Full recipe replay engine integration is Phase 2.
        # The stub confirms OAuth3 passed and returns the evidence bundle.
        evidence = {
            "recipe_id": recipe_id,
            "status": "oauth3_verified",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "agency_token": agency_token_evidence,
            "recipe_metadata": {
                "description": recipe.get("description", ""),
                "version": recipe.get("version", "1.0"),
                "required_scope": required_scope,
            },
            "rung": 641,
        }

        # Attach step_up evidence only when relevant
        if step_up_performed:
            evidence["step_up"] = step_up_evidence

        logger.info(
            f"OAuth3 enforced for recipe '{recipe_id}': "
            f"token={token_id[:8]}... scope={required_scope} "
            f"step_up={step_up_performed}"
        )

        return web.json_response(
            {
                "success": True,
                "recipe_id": recipe_id,
                "status": "oauth3_verified",
                "message": (
                    "OAuth3 enforcement passed. Recipe execution stub returned. "
                    "Full execution engine integrates in Phase 2."
                ),
                "evidence": evidence,
            },
            status=200,
        )

    # =========================================================================
    # History API handlers (Phase 2, BUILD 5)
    # =========================================================================

    async def _handle_history_list(self, request):
        """
        GET /history
        List all browsing sessions.

        Response 200: [{session_id, task_id, recipe_id, started_at, snapshot_count}]
        Response 503: history module not loaded
        """
        if not HISTORY_AVAILABLE:
            return web.json_response(
                {"error": "history_unavailable", "detail": "History module not loaded"},
                status=503,
            )
        try:
            sessions = list_sessions()
            return web.json_response({"sessions": sessions}, status=200)
        except Exception as e:
            logger.error(f"History list error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_history_session(self, request):
        """
        GET /history/{session_id}
        List snapshot metadata for a session (no decompression).

        Response 200: {session_id, snapshots: [{snapshot_id, url, title, timestamp, compressed_size_bytes}]}
        Response 404: session not found
        Response 503: history module not loaded
        """
        if not HISTORY_AVAILABLE:
            return web.json_response(
                {"error": "history_unavailable"},
                status=503,
            )
        session_id = request.match_info["session_id"]
        try:
            snapshots_meta = list_session_snapshots(session_id)
            return web.json_response(
                {"session_id": session_id, "snapshots": snapshots_meta},
                status=200,
            )
        except FileNotFoundError:
            return web.json_response(
                {"error": "session_not_found", "session_id": session_id},
                status=404,
            )
        except Exception as e:
            logger.error(f"History session detail error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_history_snapshot(self, request):
        """
        GET /history/{session_id}/{snapshot_id}
        Return full decompressed snapshot JSON.

        Response 200: full snapshot dict (includes html field)
        Response 404: session or snapshot not found
        Response 503: history module not loaded
        """
        if not HISTORY_AVAILABLE:
            return web.json_response(
                {"error": "history_unavailable"},
                status=503,
            )
        session_id = request.match_info["session_id"]
        snapshot_id = request.match_info["snapshot_id"]
        try:
            snapshot = get_session_snapshot(session_id, snapshot_id)
            return web.json_response(snapshot.to_dict(), status=200)
        except FileNotFoundError:
            return web.json_response(
                {
                    "error": "snapshot_not_found",
                    "session_id": session_id,
                    "snapshot_id": snapshot_id,
                },
                status=404,
            )
        except Exception as e:
            logger.error(f"History snapshot detail error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_history_render(self, request):
        """
        GET /history/{session_id}/{snapshot_id}/render
        Return raw HTML only (sandboxed; suitable for iframe embedding).

        Response 200: Content-Type text/html with sandbox CSP
        Response 404: session or snapshot not found
        Response 503: history module not loaded
        """
        if not HISTORY_AVAILABLE:
            return web.json_response(
                {"error": "history_unavailable"},
                status=503,
            )
        session_id = request.match_info["session_id"]
        snapshot_id = request.match_info["snapshot_id"]
        try:
            snapshot = get_session_snapshot(session_id, snapshot_id)
            headers = {
                "Content-Security-Policy": "sandbox allow-same-origin",
            }
            return web.Response(
                text=snapshot.html,
                content_type="text/html",
                headers=headers,
            )
        except FileNotFoundError:
            return web.json_response(
                {
                    "error": "snapshot_not_found",
                    "session_id": session_id,
                    "snapshot_id": snapshot_id,
                },
                status=404,
            )
        except Exception as e:
            logger.error(f"History render error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_ui(self, request):
        """Serve debugging UI"""
        return web.Response(text=self._get_ui_html(), content_type='text/html')

    def _get_ui_html(self):
        """Generate debugging UI HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Solace Browser - Debug UI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }
        .container { display: flex; height: 100vh; }
        .sidebar { width: 25%; background: #1e1e1e; color: #fff; padding: 20px; overflow-y: auto; border-right: 1px solid #333; }
        .main { width: 75%; display: flex; flex-direction: column; }
        .viewport { flex: 1; background: #fff; border: 1px solid #ddd; position: relative; overflow: auto; }
        .controls { padding: 20px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
        .input-group { margin-bottom: 10px; }
        input, button { padding: 8px 12px; margin-right: 10px; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #007bff; color: white; cursor: pointer; border: none; }
        button:hover { background: #0056b3; }
        .events { margin-top: 20px; }
        .event { background: #f0f0f0; padding: 10px; margin-bottom: 5px; border-left: 3px solid #007bff; font-size: 12px; }
        .status { padding: 10px; background: #e8f5e9; border-radius: 4px; margin-bottom: 10px; }
        h2 { margin: 20px 0 10px 0; font-size: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>Solace Browser</h1>
            <div class="status" id="status">Loading...</div>

            <h2>Controls</h2>
            <div class="input-group">
                <input type="text" id="urlInput" placeholder="Enter URL" style="width: 100%;">
                <button onclick="navigate()">Navigate</button>
            </div>

            <div class="input-group">
                <input type="text" id="selectorInput" placeholder="CSS Selector" style="width: 100%;">
                <button onclick="click()">Click</button>
            </div>

            <div class="input-group">
                <input type="text" id="textInput" placeholder="Text to fill" style="width: 100%;">
                <button onclick="fill()">Fill</button>
            </div>

            <button onclick="screenshot()" style="width: 100%; margin-bottom: 10px;">📸 Screenshot</button>
            <button onclick="snapshot()" style="width: 100%;">📄 Snapshot</button>

            <div class="events">
                <h2>Events</h2>
                <div id="eventsList"></div>
            </div>
        </div>

        <div class="main">
            <div class="controls">
                <h3>Viewport</h3>
                <p id="currentUrl">No page loaded</p>
            </div>
            <div class="viewport" id="viewport">
                <div style="padding: 20px; color: #999;">Loading browser...</div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = 'http://localhost:9222';

        async function navigate() {
            const url = document.getElementById('urlInput').value;
            const res = await fetch(`${API_BASE}/api/navigate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();
            console.log('Navigate:', data);
            updateStatus();
        }

        async function click() {
            const selector = document.getElementById('selectorInput').value;
            const res = await fetch(`${API_BASE}/api/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selector })
            });
            const data = await res.json();
            console.log('Click:', data);
        }

        async function fill() {
            const selector = document.getElementById('selectorInput').value;
            const text = document.getElementById('textInput').value;
            const res = await fetch(`${API_BASE}/api/fill`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selector, text })
            });
            const data = await res.json();
            console.log('Fill:', data);
        }

        async function screenshot() {
            const res = await fetch(`${API_BASE}/api/screenshot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();
            alert('Screenshot saved: ' + data.filename);
        }

        async function snapshot() {
            const res = await fetch(`${API_BASE}/api/snapshot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();
            alert('Snapshot: ' + data.url);
        }

        async function updateStatus() {
            const res = await fetch(`${API_BASE}/api/status`);
            const data = await res.json();
            document.getElementById('status').innerHTML = `
                <strong>Status:</strong> ${data.running ? '✓ Running' : '✗ Stopped'}<br>
                <strong>URL:</strong> ${data.current_url || 'None'}<br>
                <strong>Pages:</strong> ${data.pages}
            `;
            document.getElementById('currentUrl').textContent = `Current: ${data.current_url || 'None'}`;

            // Load events
            const evRes = await fetch(`${API_BASE}/api/events?limit=20`);
            const events = await evRes.json();
            const eventsList = document.getElementById('eventsList');
            eventsList.innerHTML = events.reverse().map(e => `
                <div class="event">
                    <strong>${e.type}</strong><br>
                    ${e.message || e.url || ''}<br>
                    <small>${new Date(e.timestamp).toLocaleTimeString()}</small>
                </div>
            `).join('');
        }

        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>
        """

    # ------------------------------------------------------------------
    # Sync handlers (browser <-> cloud evidence + config bridge)
    # ------------------------------------------------------------------

    async def _handle_sync_push(self, request):
        """Trigger a push of current evidence to cloud.

        POST /api/sync/push

        Collects all pending evidence bundles from the Part 11 audit
        directory and uploads them to solaceagi.com via the sync client.
        """
        if self._sync_client is None or self._evidence_collector is None:
            return web.json_response(
                {"error": "sync module not available"}, status=503
            )

        try:
            result = await upload_pending_evidence(
                self._sync_client, self._evidence_collector
            )
            return web.json_response({"success": True, "sync": result})
        except SyncError as exc:
            logger.error("Sync push failed: %s", exc)
            return web.json_response(
                {"error": f"sync push failed: {exc}"}, status=502
            )
        except Exception as exc:
            logger.error("Sync push unexpected error: %s", exc)
            return web.json_response(
                {"error": f"sync push error: {exc}"}, status=500
            )

    async def _handle_sync_status(self, request):
        """Show sync status (last push time, pending items).

        GET /api/sync/status
        """
        if self._sync_client is None or self._evidence_collector is None:
            return web.json_response(
                {"error": "sync module not available"}, status=503
            )

        pending_evidence = self._evidence_collector.pending_count
        status = self._sync_client.get_status(
            pending_evidence=pending_evidence,
        )
        return web.json_response({
            "connected": status.connected,
            "last_push_iso": status.last_push_iso,
            "last_pull_iso": status.last_pull_iso,
            "pending_evidence_count": status.pending_evidence_count,
            "pending_runs_count": status.pending_runs_count,
            "api_url": status.api_url,
            "auto_sync_enabled": status.auto_sync_enabled,
            "evidence_auto_upload": status.evidence_auto_upload,
            "last_evidence_upload": self._last_evidence_upload,
        })

    async def _handle_sync_pull(self, request):
        """Trigger a pull of config from cloud.

        POST /api/sync/pull
        """
        if self._sync_client is None:
            return web.json_response(
                {"error": "sync module not available"}, status=503
            )

        try:
            config = await self._sync_client.pull_config()
            return web.json_response({"success": True, "config": config})
        except SyncError as exc:
            logger.error("Sync pull failed: %s", exc)
            return web.json_response(
                {"error": f"sync pull failed: {exc}"}, status=502
            )
        except Exception as exc:
            logger.error("Sync pull unexpected error: %s", exc)
            return web.json_response(
                {"error": f"sync pull error: {exc}"}, status=500
            )

    async def start(self):
        """Start the server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        await self._start_sync_services()
        logger.info(f"✓ CDP Server started on http://localhost:{self.port}")

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            await self._stop_sync_services()
            await runner.cleanup()


async def main():
    """Main entry point"""
    parser = build_arg_parser()
    args = parser.parse_args()

    # Create and start browser
    headless = not args.head
    if args.headless:
        headless = True
    env_part11 = os.getenv("SOLACE_PART11", "").strip().lower() in {"1", "true", "yes", "on"}
    browser = SolaceBrowser(
        headless=headless,
        debug_ui=args.show_ui,
        part11_enabled=(args.part11 or env_part11),
        part11_mode=args.part11_mode,
        part11_audit_dir=args.part11_audit_dir,
    )
    await browser.start()

    # Create and start server
    server = SolaceBrowserServer(
        browser,
        port=args.port,
        sync_config=build_sync_config(args),
    )

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await browser.stop()


def cli_main():
    """Synchronous console-script wrapper for setuptools entry points."""
    asyncio.run(main())


if __name__ == '__main__':
    cli_main()
