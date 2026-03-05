"""Highlighter — CDP Overlay.highlightNode + JS fallback for element highlighting."""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("solace-browser.yinyang")


class YinyangHighlighter:
    """Highlights page elements using CDP or JS fallback."""

    HIGHLIGHT_COLOR = {"r": 74, "g": 158, "b": 255, "a": 0.3}  # #4a9eff @ 30%
    OUTLINE_COLOR = {"r": 74, "g": 158, "b": 255, "a": 0.8}

    def __init__(self, page: Any):
        self._page = page
        self._cdp: Optional[Any] = None
        self._highlighted_selector: Optional[str] = None

    async def _get_cdp(self) -> Optional[Any]:
        """Get CDP session, caching the result."""
        if self._cdp is None:
            try:
                self._cdp = await self._page.context.new_cdp_session(self._page)
                logger.debug("[Highlighter] CDP session established")
            except (RuntimeError, OSError, AttributeError) as exc:
                logger.debug(f"[Highlighter] CDP unavailable, using JS fallback: {exc}")
        return self._cdp

    async def highlight(self, selector: str) -> bool:
        """Highlight an element by CSS selector. Returns True if successful."""
        await self.clear()
        self._highlighted_selector = selector

        cdp = await self._get_cdp()
        if cdp:
            return await self._highlight_cdp(cdp, selector)
        return await self._highlight_js(selector)

    async def _highlight_cdp(self, cdp: Any, selector: str) -> bool:
        """Highlight using CDP Overlay.highlightNode."""
        try:
            # Find the node
            doc = await cdp.send("DOM.getDocument")
            node = await cdp.send("DOM.querySelector", {
                "nodeId": doc["root"]["nodeId"],
                "selector": selector,
            })
            if not node or not node.get("nodeId"):
                logger.debug(f"[Highlighter] Selector not found: {selector}")
                return False

            await cdp.send("Overlay.highlightNode", {
                "highlightConfig": {
                    "contentColor": self.HIGHLIGHT_COLOR,
                    "borderColor": self.OUTLINE_COLOR,
                    "showInfo": True,
                },
                "nodeId": node["nodeId"],
            })
            logger.debug(f"[Highlighter] CDP highlight on: {selector}")
            return True
        except (RuntimeError, OSError, KeyError) as exc:
            logger.debug(f"[Highlighter] CDP highlight failed: {exc}")
            return await self._highlight_js(selector)

    async def _highlight_js(self, selector: str) -> bool:
        """Highlight using JS injection (fallback)."""
        try:
            result = await self._page.evaluate(f"""
                (() => {{
                    const el = document.querySelector({repr(selector)});
                    if (!el) return false;
                    el.dataset.solaceHighlighted = 'true';
                    el.style.outline = '3px solid rgba(74, 158, 255, 0.8)';
                    el.style.outlineOffset = '2px';
                    el.style.boxShadow = '0 0 12px rgba(74, 158, 255, 0.3)';
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    return true;
                }})()
            """)
            if result:
                logger.debug(f"[Highlighter] JS highlight on: {selector}")
            return bool(result)
        except (RuntimeError, OSError) as exc:
            logger.warning(f"[Highlighter] JS highlight failed: {exc}")
            return False

    async def clear(self) -> None:
        """Remove any active highlight."""
        cdp = await self._get_cdp()
        if cdp:
            try:
                await cdp.send("Overlay.hideHighlight")
            except (RuntimeError, OSError) as e:
                logger.debug(f"CDP highlight clear failed: {e}")

        if self._highlighted_selector:
            try:
                await self._page.evaluate("""
                    (() => {
                        document.querySelectorAll('[data-solace-highlighted]').forEach(el => {
                            el.style.outline = '';
                            el.style.outlineOffset = '';
                            el.style.boxShadow = '';
                            delete el.dataset.solaceHighlighted;
                        });
                    })()
                """)
            except (RuntimeError, OSError) as e:
                logger.debug(f"DOM highlight cleanup failed: {e}")
        self._highlighted_selector = None
