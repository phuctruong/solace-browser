"""Top Rail -- 32px status bar injected into every page.

Shows compact state indicator: "{app_name}: {state}" with color coding:
  green  = DONE, EVIDENCE_SEAL
  yellow = PREVIEW_READY, COOLDOWN
  red    = BLOCKED, FAILED, REJECTED, TIMEOUT, SEALED_ABORT
  blue   = EXECUTING, PREVIEW, BUDGET_CHECK, TRIGGER, INTENT, APPROVED, SEALED, E_SIGN

Channel [7] -- Context + Tools.  Rung: 65537.
"""
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

    var rail = document.createElement('div');
    rail.id = 'solace-top-rail';
    rail.style.cssText = 'position:fixed;top:0;left:0;right:0;height:32px;background:#1a1a2e;color:#fff;display:flex;align-items:center;padding:0 12px;font-family:system-ui;font-size:12px;z-index:99999;box-shadow:0 1px 3px rgba(0,0,0,0.3);';

    rail.innerHTML = [
        '<span style="margin-right:8px;width:8px;height:8px;border-radius:50%;background:#666;display:inline-block;" id="solace-state-dot"></span>',
        '<span id="solace-state-text" style="font-weight:600;">IDLE</span>',
        '<span id="solace-app-label" style="margin-left:8px;opacity:0.7;font-size:11px;"></span>',
        '<span style="margin-left:auto;opacity:0.6;" id="solace-page-url"></span>'
    ].join('');
    document.documentElement.appendChild(rail);
    document.body.style.marginTop = '32px';

    var urlEl = document.getElementById('solace-page-url');
    if (urlEl) urlEl.textContent = location.hostname + location.pathname;

    var COLOR_MAP = {
        TRIGGER: '#4a9eff',
        INTENT: '#4a9eff',
        BUDGET_CHECK: '#4a9eff',
        PREVIEW: '#4a9eff',
        PREVIEW_READY: '#f5a623',
        APPROVED: '#4a9eff',
        REJECTED: '#e74c3c',
        TIMEOUT: '#e74c3c',
        COOLDOWN: '#f5a623',
        E_SIGN: '#4a9eff',
        SEALED: '#4a9eff',
        EXECUTING: '#4a9eff',
        DONE: '#27ae60',
        FAILED: '#e74c3c',
        BLOCKED: '#e74c3c',
        SEALED_ABORT: '#e74c3c',
        EVIDENCE_SEAL: '#27ae60',
        idle: '#666666',
        listening: '#4a9eff',
        processing: '#4a9eff',
        intent_classified: '#4a9eff',
        preview_generating: '#f5a623',
        preview_ready: '#f5a623',
        cooldown: '#f5a623',
        approved: '#27ae60',
        sealed: '#27ae60',
        executing: '#27ae60',
        done: '#27ae60',
        blocked: '#e74c3c',
        error: '#e74c3c'
    };

    var PULSE_STATES = ['EXECUTING', 'PREVIEW', 'BUDGET_CHECK', 'processing', 'preview_generating'];

    window.addEventListener('message', function(e) {
        if (!e.data || e.data.type !== 'yinyang_state') return;

        var dot = document.getElementById('solace-state-dot');
        var text = document.getElementById('solace-state-text');
        var appLabel = document.getElementById('solace-app-label');

        if (!dot || !text) return;

        var state = e.data.state || 'IDLE';
        var appName = e.data.app_name || '';

        // Top rail shows "{app_name}: {state}" when app_name is present
        if (appName) {
            text.textContent = state;
            appLabel.textContent = appName;
        } else {
            text.textContent = state;
            appLabel.textContent = '';
        }

        dot.style.background = COLOR_MAP[state] || '#666';

        if (PULSE_STATES.indexOf(state) >= 0) {
            dot.style.animation = 'solace-pulse 1s infinite';
        } else {
            dot.style.animation = 'none';
        }
    });

    // Inject pulse animation keyframes
    var style = document.createElement('style');
    style.textContent = '@keyframes solace-pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }';
    document.head.appendChild(style);
})();
"""
