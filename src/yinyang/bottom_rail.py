"""Bottom Rail — 36->300px expandable chat panel."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("solace-browser.yinyang")

BOTTOM_RAIL_JS = (Path(__file__).parent.parent.parent / "static" / "bottom_rail.js").resolve()

async def inject_bottom_rail(page: Any, ws_url: str = "ws://localhost:9222/ws/yinyang") -> None:
    """Inject bottom rail chat panel into a Playwright page."""
    try:
        if BOTTOM_RAIL_JS.exists():
            js_code = BOTTOM_RAIL_JS.read_text(encoding="utf-8")
        else:
            js_code = _INLINE_BOTTOM_RAIL_JS
        js_code = js_code.replace("__WS_URL__", ws_url)
        await page.add_init_script(js_code)
        logger.debug("Bottom rail injected")
    except Exception as exc:
        logger.warning(f"Failed to inject bottom rail: {exc}")

_INLINE_BOTTOM_RAIL_JS = """
(function() {
    if (document.getElementById('solace-bottom-rail')) return;

    const COLLAPSED_HEIGHT = '36px';
    const EXPANDED_HEIGHT = '300px';
    let expanded = false;
    let ws = null;
    const WS_URL = '__WS_URL__';

    // Create rail container
    const rail = document.createElement('div');
    rail.id = 'solace-bottom-rail';
    rail.style.cssText = 'position:fixed;bottom:0;left:0;right:0;height:' + COLLAPSED_HEIGHT + ';background:#1a1a2e;color:#fff;font-family:system-ui;font-size:13px;z-index:99998;transition:height 0.3s ease;display:flex;flex-direction:column;box-shadow:0 -2px 8px rgba(0,0,0,0.3);';

    // Header bar (always visible)
    const header = document.createElement('div');
    header.style.cssText = 'display:flex;align-items:center;padding:0 12px;height:36px;min-height:36px;cursor:pointer;border-bottom:1px solid #333;';
    header.innerHTML = '<span style="font-weight:600;">Yinyang</span><span style="margin-left:8px;opacity:0.6;font-size:11px;" id="solace-credits-summary"></span><span style="margin-left:auto;font-size:16px;" id="solace-toggle-btn">&#9650;</span>';
    header.onclick = toggleRail;

    // Chat area
    const chatArea = document.createElement('div');
    chatArea.id = 'solace-chat-area';
    chatArea.style.cssText = 'flex:1;overflow-y:auto;padding:8px 12px;display:none;';

    // Input area
    const inputArea = document.createElement('div');
    inputArea.id = 'solace-input-area';
    inputArea.style.cssText = 'display:none;padding:8px 12px;border-top:1px solid #333;';
    inputArea.innerHTML = '<div style="display:flex;gap:8px;"><input id="solace-chat-input" type="text" placeholder="Ask Yinyang..." style="flex:1;background:#2a2a3e;border:1px solid #444;border-radius:6px;padding:6px 10px;color:#fff;font-size:13px;outline:none;" /><button id="solace-send-btn" style="background:#4a9eff;color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:13px;">Send</button></div>';

    rail.appendChild(header);
    rail.appendChild(chatArea);
    rail.appendChild(inputArea);
    document.documentElement.appendChild(rail);

    function toggleRail() {
        expanded = !expanded;
        rail.style.height = expanded ? EXPANDED_HEIGHT : COLLAPSED_HEIGHT;
        chatArea.style.display = expanded ? 'block' : 'none';
        inputArea.style.display = expanded ? 'block' : 'none';
        document.getElementById('solace-toggle-btn').innerHTML = expanded ? '&#9660;' : '&#9650;';
        if (expanded && !ws) connectWS();
    }

    function connectWS() {
        try {
            ws = new WebSocket(WS_URL);
            ws.onmessage = function(e) {
                try {
                    const msg = JSON.parse(e.data);
                    if (msg.type === 'chat') addMessage('assistant', msg.payload.content || '');
                    if (msg.type === 'state_update') window.postMessage({type: 'yinyang_state', state: msg.payload.state}, '*');
                    if (msg.type === 'credits_update') updateCredits(msg.payload);
                } catch(err) { console.warn('YY parse error:', err); }
            };
            ws.onclose = function() { ws = null; };
        } catch(err) { console.warn('YY WS error:', err); }
    }

    function addMessage(role, content) {
        const div = document.createElement('div');
        div.style.cssText = 'margin-bottom:8px;padding:6px 10px;border-radius:8px;max-width:85%;' +
            (role === 'user' ? 'background:#2a3a5e;margin-left:auto;' : 'background:#2a2a3e;');
        div.textContent = content;
        chatArea.appendChild(div);
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function updateCredits(data) {
        const el = document.getElementById('solace-credits-summary');
        if (el && data) el.textContent = '$' + (data.balance || 0).toFixed(2) + ' credits';
    }

    function sendMessage() {
        const input = document.getElementById('solace-chat-input');
        const text = (input.value || '').trim();
        if (!text) return;
        addMessage('user', text);
        input.value = '';
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({type: 'chat', payload: {content: text}}));
        } else {
            addMessage('assistant', 'Not connected. Reconnecting...');
            connectWS();
        }
    }

    // Wire send button and enter key
    setTimeout(function() {
        const btn = document.getElementById('solace-send-btn');
        const input = document.getElementById('solace-chat-input');
        if (btn) btn.onclick = sendMessage;
        if (input) input.onkeydown = function(e) { if (e.key === 'Enter') sendMessage(); };
    }, 100);
})();
"""
