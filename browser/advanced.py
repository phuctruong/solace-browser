#!/usr/bin/env python3

"""
Advanced browser module - Page observation, network monitoring, ref mapping

This layer adds critical missing pieces for LLM-driven automation:
- AriaRefMapper: Map ARIA element references to clickable locators
- PageObserver: Monitor console messages and page errors
- NetworkMonitor: Track HTTP requests/responses
- Enhanced LLM-friendly snapshots
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger('solace-browser')


# ============================================================================
# CRITICAL: ARIA Reference Mapper
# ============================================================================

class AriaRefMapper:
    """
    Maps ARIA element references (n1, n2, n3...) to Playwright locators
    This is THE KEY MISSING PIECE that enables LLM-driven interactions
    """

    def __init__(self):
        self.ref_to_locator = {}  # "n42" → Playwright locator
        self.ref_to_aria_node = {}  # "n42" → AriaNode data
        self.ref_to_selector = {}  # "n42" → CSS selector (fallback)

    async def build_map(self, page, aria_nodes: List[Dict[str, Any]]):
        """
        Build mapping from ARIA refs to Playwright locators
        Uses role + name for stable element identification
        """
        logger.info(f"Building ARIA ref map for {len(aria_nodes)} nodes")

        for node in aria_nodes:
            ref = node.get("ref")
            role = node.get("role")
            name = node.get("name")

            if not ref:
                continue

            self.ref_to_aria_node[ref] = node

            # Strategy 1: Use role + name (most stable)
            if role and name:
                try:
                    locator = page.get_by_role(role, name=name)
                    self.ref_to_locator[ref] = locator
                    logger.debug(f"Mapped {ref} via role={role} name={name}")
                    continue
                except Exception as e:
                    logger.debug(f"Role+name mapping failed for {ref}: {e}")

            # Strategy 2: Use aria-label
            aria_label = node.get("ariaLabel")
            if aria_label:
                try:
                    locator = page.locator(f"[aria-label='{aria_label}']")
                    self.ref_to_locator[ref] = locator
                    self.ref_to_selector[ref] = f"[aria-label='{aria_label}']"
                    logger.debug(f"Mapped {ref} via aria-label={aria_label}")
                    continue
                except Exception as e:
                    logger.debug(f"Aria-label mapping failed for {ref}: {e}")

            # Strategy 3: Use text content (for links/buttons)
            text = node.get("text")
            if text and role in ["button", "link"]:
                try:
                    locator = page.get_by_role(role, name=text)
                    self.ref_to_locator[ref] = locator
                    logger.debug(f"Mapped {ref} via role={role} text={text}")
                    continue
                except Exception as e:
                    logger.debug(f"Text mapping failed for {ref}: {e}")

        logger.info(f"Mapped {len(self.ref_to_locator)} element references")

    def get_locator(self, ref: str):
        """Get Playwright locator for a given ref"""
        return self.ref_to_locator.get(ref)

    def get_aria_node(self, ref: str):
        """Get ARIA node data for a given ref"""
        return self.ref_to_aria_node.get(ref)

    def get_selector(self, ref: str):
        """Get CSS selector for a given ref (if available)"""
        return self.ref_to_selector.get(ref)


# ============================================================================
# CRITICAL: Page Observer (Console & Errors)
# ============================================================================

class PageObserver:
    """
    Monitor page console messages and errors
    Critical for debugging "why didn't my action work?"
    """

    def __init__(self, page):
        self.page = page
        self.console_messages = []
        self.page_errors = []
        self.max_messages = 100  # Keep last 100 messages

        # Setup listeners
        page.on("console", self._on_console)
        page.on("pageerror", self._on_page_error)

    def _on_console(self, msg):
        """Capture console messages"""
        entry = {
            "type": msg.type,  # "log", "warning", "error", etc.
            "text": msg.text,
            "timestamp": datetime.now().isoformat(),
            "location": {
                "url": msg.location.get("url", "") if msg.location else "",
                "line": msg.location.get("lineNumber", 0) if msg.location else 0
            }
        }
        self.console_messages.append(entry)

        # Keep only last N messages
        if len(self.console_messages) > self.max_messages:
            self.console_messages.pop(0)

        # Log errors prominently
        if msg.type in ["error", "warning"]:
            logger.warning(f"Console {msg.type}: {msg.text}")

    def _on_page_error(self, error):
        """Capture page errors (JavaScript exceptions)"""
        entry = {
            "message": str(error),
            "timestamp": datetime.now().isoformat()
        }
        self.page_errors.append(entry)
        logger.error(f"Page error: {error}")

    def get_recent_console(self, count: int = 10):
        """Get recent console messages"""
        return self.console_messages[-count:]

    def get_errors(self):
        """Get all page errors"""
        return self.page_errors

    def has_errors(self):
        """Check if any errors occurred"""
        return len(self.page_errors) > 0 or any(
            msg["type"] == "error" for msg in self.console_messages
        )

    def clear(self):
        """Clear all captured messages"""
        self.console_messages.clear()
        self.page_errors.clear()


# ============================================================================
# CRITICAL: Network Monitor
# ============================================================================

class NetworkMonitor:
    """
    Track HTTP requests and responses
    Critical for verifying API calls succeeded
    """

    def __init__(self, page):
        self.page = page
        self.requests = []
        self.responses = []
        self.max_entries = 100  # Keep last 100 requests

        # Setup listeners
        page.on("request", self._on_request)
        page.on("response", self._on_response)

    def _on_request(self, request):
        """Capture HTTP requests"""
        entry = {
            "type": "request",
            "url": request.url,
            "method": request.method,
            "resourceType": request.resource_type,
            "timestamp": datetime.now().isoformat()
        }
        self.requests.append(entry)

        # Keep only last N entries
        if len(self.requests) > self.max_entries:
            self.requests.pop(0)

    def _on_response(self, response):
        """Capture HTTP responses"""
        entry = {
            "type": "response",
            "url": response.url,
            "status": response.status,
            "statusText": response.status_text,
            "ok": response.ok,
            "timestamp": datetime.now().isoformat()
        }
        self.responses.append(entry)

        # Keep only last N entries
        if len(self.responses) > self.max_entries:
            self.responses.pop(0)

        # Log failed requests
        if not response.ok:
            logger.warning(f"HTTP {response.status}: {response.url}")

    def get_recent_requests(self, count: int = 10):
        """Get recent requests"""
        return self.requests[-count:]

    def get_recent_responses(self, count: int = 10):
        """Get recent responses"""
        return self.responses[-count:]

    def get_failed_requests(self):
        """Get all failed requests (status >= 400)"""
        return [r for r in self.responses if not r.get("ok", True)]

    def clear(self):
        """Clear all captured network activity"""
        self.requests.clear()
        self.responses.clear()


# ============================================================================
# ENHANCED: LLM-Friendly Page Snapshot
# ============================================================================

async def get_llm_snapshot(
    page,
    aria_tree: List[Dict[str, Any]],
    dom_tree: List[Dict[str, Any]],
    observer: Optional[PageObserver] = None,
    network_monitor: Optional[NetworkMonitor] = None
) -> Dict[str, Any]:
    """
    Get comprehensive page snapshot optimized for LLM understanding
    Combines ARIA + DOM + console + network + state
    """
    try:
        # Get page metadata
        url = page.url
        title = await page.title()

        # Get storage state
        try:
            local_storage = await page.evaluate("() => Object.entries(localStorage)")
            session_storage = await page.evaluate("() => Object.entries(sessionStorage)")
        except Exception as e:
            logger.warning(f"Could not get storage: {e}")
            local_storage = []
            session_storage = []

        # Build comprehensive snapshot
        snapshot = {
            # Structured element references (CRITICAL for LLM)
            "aria": aria_tree,

            # DOM structure (fallback for complex scenarios)
            "dom": dom_tree,

            # Page metadata
            "url": url,
            "title": title,

            # Observability (CRITICAL for debugging)
            "console": observer.get_recent_console(20) if observer else [],
            "errors": observer.get_errors() if observer else [],
            "hasErrors": observer.has_errors() if observer else False,

            # Network activity (CRITICAL for verification)
            "network": {
                "requests": network_monitor.get_recent_requests(10) if network_monitor else [],
                "responses": network_monitor.get_recent_responses(10) if network_monitor else [],
                "failures": network_monitor.get_failed_requests() if network_monitor else []
            },

            # State
            "storage": {
                "localStorage": dict(local_storage),
                "sessionStorage": dict(session_storage)
            },

            # Timestamp
            "timestamp": datetime.now().isoformat()
        }

        # Calculate summary stats
        snapshot["stats"] = {
            "ariaNodes": len(aria_tree),
            "domNodes": len(dom_tree),
            "consoleMessages": len(observer.console_messages) if observer else 0,
            "pageErrors": len(observer.page_errors) if observer else 0,
            "networkRequests": len(network_monitor.requests) if network_monitor else 0
        }

        return snapshot

    except Exception as e:
        logger.error(f"Error creating LLM snapshot: {e}")
        return {
            "error": str(e),
            "url": page.url if page else "unknown",
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# ENHANCED: Click Action with Ref Resolution
# ============================================================================

async def execute_click_via_ref(
    page,
    ref: str,
    ref_mapper: AriaRefMapper,
    double_click: bool = False,
    button: Literal["left", "right", "middle"] = "left",
    modifiers: Optional[List[str]] = None,
    delay_ms: int = 0,
    timeout_ms: int = 5000
) -> Dict[str, Any]:
    """
    Execute click action using ARIA ref
    CRITICAL: This is what enables "Click n42" style interactions
    """
    try:
        # Get locator from ref mapper
        locator = ref_mapper.get_locator(ref)

        if not locator:
            # Fallback: try to use ref as CSS selector
            logger.warning(f"No locator for {ref}, trying as selector")
            locator = page.locator(ref)

        # Wait for element to be available
        await locator.wait_for(timeout=timeout_ms)

        # Apply delay if specified
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

        # Prepare click options
        click_options = {
            "button": button,
            "timeout": timeout_ms
        }

        if modifiers:
            click_options["modifiers"] = modifiers

        # Execute click
        if double_click:
            await locator.dblclick(**click_options)
            logger.info(f"Double-clicked {ref}")
        else:
            await locator.click(**click_options)
            logger.info(f"Clicked {ref}")

        return {
            "success": True,
            "action": "click",
            "ref": ref,
            "aria_node": ref_mapper.get_aria_node(ref),
            "url": page.url
        }

    except Exception as e:
        logger.error(f"Click failed for {ref}: {e}")
        return {
            "success": False,
            "error": str(e),
            "ref": ref
        }


# ============================================================================
# ENHANCED: Type Action with Ref Resolution
# ============================================================================

async def execute_type_via_ref(
    page,
    ref: str,
    text: str,
    ref_mapper: AriaRefMapper,
    slowly: bool = False,
    delay_ms: int = 50,
    submit: bool = False,
    timeout_ms: int = 5000
) -> Dict[str, Any]:
    """
    Execute type action using ARIA ref
    Supports human-like slow typing
    """
    try:
        # Get locator from ref mapper
        locator = ref_mapper.get_locator(ref)

        if not locator:
            logger.warning(f"No locator for {ref}, trying as selector")
            locator = page.locator(ref)

        # Wait for element
        await locator.wait_for(timeout=timeout_ms)

        if slowly:
            # Type character by character (human-like)
            logger.info(f"Typing slowly into {ref}: '{text}'")
            await locator.click()  # Focus the element
            await locator.fill("")  # Clear existing text

            for char in text:
                await locator.type(char)
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000)
        else:
            # Fast fill
            await locator.fill(text)
            logger.info(f"Typed into {ref}: '{text}'")

        if submit:
            await locator.press("Enter")
            logger.info(f"Submitted by pressing Enter")

        return {
            "success": True,
            "action": "type",
            "ref": ref,
            "text": text,
            "slowly": slowly,
            "aria_node": ref_mapper.get_aria_node(ref),
            "url": page.url
        }

    except Exception as e:
        logger.error(f"Type failed for {ref}: {e}")
        return {
            "success": False,
            "error": str(e),
            "ref": ref
        }
