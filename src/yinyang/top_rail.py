"""Top Rail — 32px status bar injected into every page."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("solace-browser.yinyang")

TOP_RAIL_JS = (Path(__file__).parent.parent.parent / "static" / "top_rail.js").resolve()

async def inject_top_rail(page: Any) -> None:
    """Inject top rail status bar into a Playwright page."""
    try:
        if TOP_RAIL_JS.exists():
            js_code = TOP_RAIL_JS.read_text(encoding="utf-8")
        else:
            js_code = _INLINE_TOP_RAIL_JS
        await page.add_init_script(js_code)
        logger.debug("Top rail injected")
    except Exception as exc:
        logger.warning(f"Failed to inject top rail: {exc}")

_INLINE_TOP_RAIL_JS = """
(function() {
    if (document.getElementById('solace-top-rail')) return;
    const rail = document.createElement('div');
    rail.id = 'solace-top-rail';
    rail.style.cssText = 'position:fixed;top:0;left:0;right:0;height:32px;background:#1a1a2e;color:#fff;display:flex;align-items:center;padding:0 12px;font-family:system-ui;font-size:12px;z-index:99999;box-shadow:0 1px 3px rgba(0,0,0,0.3);';
    rail.innerHTML = '<span style="margin-right:8px;width:8px;height:8px;border-radius:50%;background:#666;" id="solace-state-dot"></span><span id="solace-state-text">IDLE</span><span style="margin-left:auto;opacity:0.6;" id="solace-page-url"></span>';
    document.documentElement.appendChild(rail);
    document.body.style.marginTop = '32px';

    // Update URL display
    const urlEl = document.getElementById('solace-page-url');
    if (urlEl) urlEl.textContent = location.hostname + location.pathname;

    // Listen for state updates
    window.addEventListener('message', function(e) {
        if (e.data && e.data.type === 'yinyang_state') {
            const dot = document.getElementById('solace-state-dot');
            const text = document.getElementById('solace-state-text');
            if (dot && text) {
                text.textContent = e.data.state || 'IDLE';
                const colors = {idle:'#666',listening:'#4a9eff',processing:'#4a9eff',preview_ready:'#f5a623',executing:'#27ae60',done:'#27ae60',error:'#e74c3c',blocked:'#e74c3c'};
                dot.style.background = colors[e.data.state] || '#666';
                if (e.data.state === 'processing') dot.style.animation = 'pulse 1s infinite';
                else dot.style.animation = 'none';
            }
        }
    });
})();
"""
