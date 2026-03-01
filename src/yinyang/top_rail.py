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

    var logo = document.createElement('img');
    logo.src = 'data:image/png;base64,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';
    logo.style.cssText = 'width:20px;height:20px;margin-right:8px;';
    rail.appendChild(logo);

    var dot = document.createElement('span');
    dot.id = 'solace-state-dot';
    dot.style.cssText = 'margin-right:8px;width:8px;height:8px;border-radius:50%;background:#666;display:inline-block;';
    rail.appendChild(dot);

    var stateText = document.createElement('span');
    stateText.id = 'solace-state-text';
    stateText.style.cssText = 'font-weight:600;';
    stateText.textContent = 'IDLE';
    rail.appendChild(stateText);

    var appLabel = document.createElement('span');
    appLabel.id = 'solace-app-label';
    appLabel.style.cssText = 'margin-left:8px;opacity:0.7;font-size:11px;';
    rail.appendChild(appLabel);

    var urlSpan = document.createElement('span');
    urlSpan.id = 'solace-page-url';
    urlSpan.style.cssText = 'margin-left:auto;opacity:0.6;';
    rail.appendChild(urlSpan);
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
