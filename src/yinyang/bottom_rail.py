"""Bottom Rail -- 36->300px expandable chat panel with FSM-aware behavior.

Auto-expands when state is PREVIEW_READY, BLOCKED, or FAILED.
Shows preview text + approve/reject buttons for PREVIEW_READY.
Shows block reason for BLOCKED.
Shows error details for FAILED.
Collapses automatically on DONE or SEALED_ABORT.

Anti-Clippy law: approve/reject buttons require explicit user action.
No auto-approval. No silent degradation. Fail loudly.

Channel [7] -- Context + Tools.  Rung: 65537.
"""
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

    var COLLAPSED_HEIGHT = '36px';
    var EXPANDED_HEIGHT = '300px';
    var expanded = false;
    var ws = null;
    var WS_URL = '__WS_URL__';

    // States that trigger auto-expand
    var AUTO_EXPAND = ['PREVIEW_READY', 'BLOCKED', 'FAILED'];
    // States that trigger auto-collapse
    var AUTO_COLLAPSE = ['DONE', 'SEALED_ABORT'];

    // Create rail container
    var rail = document.createElement('div');
    rail.id = 'solace-bottom-rail';
    rail.style.cssText = 'position:fixed;bottom:0;left:0;right:0;height:' + COLLAPSED_HEIGHT + ';background:#1a1a2e;color:#fff;font-family:system-ui;font-size:13px;z-index:99998;transition:height 0.3s ease;display:flex;flex-direction:column;box-shadow:0 -2px 8px rgba(0,0,0,0.3);';

    // Header bar (always visible)
    var header = document.createElement('div');
    header.style.cssText = 'display:flex;align-items:center;padding:0 12px;height:36px;min-height:36px;cursor:pointer;border-bottom:1px solid #333;';
    header.innerHTML = '<span style="font-weight:600;">Yinyang</span><span style="margin-left:8px;opacity:0.6;font-size:11px;" id="solace-credits-summary"></span><span style="margin-left:auto;font-size:16px;" id="solace-toggle-btn">&#9650;</span>';
    header.onclick = toggleRail;

    // Chat area
    var chatArea = document.createElement('div');
    chatArea.id = 'solace-chat-area';
    chatArea.style.cssText = 'flex:1;overflow-y:auto;padding:8px 12px;display:none;';

    // FSM action area (preview text + approve/reject buttons)
    var fsmArea = document.createElement('div');
    fsmArea.id = 'solace-fsm-area';
    fsmArea.style.cssText = 'display:none;padding:8px 12px;border-top:1px solid #333;';

    // Input area
    var inputArea = document.createElement('div');
    inputArea.id = 'solace-input-area';
    inputArea.style.cssText = 'display:none;padding:8px 12px;border-top:1px solid #333;';
    inputArea.innerHTML = '<div style="display:flex;gap:8px;"><input id="solace-chat-input" type="text" placeholder="Ask Yinyang..." style="flex:1;background:#2a2a3e;border:1px solid #444;border-radius:6px;padding:6px 10px;color:#fff;font-size:13px;outline:none;" /><button id="solace-send-btn" style="background:#4a9eff;color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:13px;">Send</button></div>';

    rail.appendChild(header);
    rail.appendChild(chatArea);
    rail.appendChild(fsmArea);
    rail.appendChild(inputArea);
    document.documentElement.appendChild(rail);

    function toggleRail() {
        expanded = !expanded;
        applyExpanded();
    }

    function applyExpanded() {
        rail.style.height = expanded ? EXPANDED_HEIGHT : COLLAPSED_HEIGHT;
        chatArea.style.display = expanded ? 'block' : 'none';
        inputArea.style.display = expanded ? 'block' : 'none';
        fsmArea.style.display = expanded ? fsmArea.dataset.hasContent === 'true' ? 'block' : 'none' : 'none';
        document.getElementById('solace-toggle-btn').innerHTML = expanded ? '&#9660;' : '&#9650;';
        if (expanded && !ws) connectWS();
    }

    function autoExpand() {
        if (!expanded) {
            expanded = true;
            applyExpanded();
        }
    }

    function autoCollapse() {
        if (expanded) {
            expanded = false;
            applyExpanded();
        }
    }

    // Listen for FSM state updates from StateBridge via postMessage
    window.addEventListener('message', function(e) {
        if (!e.data) return;

        // Handle bottom_rail_update messages from the state bridge
        if (e.data.type === 'yinyang_bottom_rail') {
            handleBottomRailUpdate(e.data);
            return;
        }

        // Handle general state updates for auto-expand/collapse
        if (e.data.type === 'yinyang_state') {
            var state = e.data.state || '';
            if (AUTO_EXPAND.indexOf(state) >= 0) {
                autoExpand();
            } else if (AUTO_COLLAPSE.indexOf(state) >= 0) {
                autoCollapse();
                clearFsmArea();
            }
        }
    });

    function handleBottomRailUpdate(data) {
        var payload = data.payload || {};
        var state = payload.state || '';

        if (payload.auto_expand) {
            autoExpand();
        }
        if (payload.auto_collapse) {
            autoCollapse();
            clearFsmArea();
            return;
        }

        if (payload.show_approve_reject && payload.preview_text) {
            showPreviewPanel(payload);
        } else if (state === 'BLOCKED' && payload.block_reason) {
            showBlockPanel(payload);
        } else if (state === 'FAILED' && payload.error_detail) {
            showErrorPanel(payload);
        } else {
            clearFsmArea();
        }
    }

    function showPreviewPanel(payload) {
        fsmArea.dataset.hasContent = 'true';
        fsmArea.style.display = expanded ? 'block' : 'none';
        fsmArea.innerHTML = [
            '<div style="margin-bottom:8px;">',
            '  <div style="font-weight:600;color:#f5a623;margin-bottom:4px;">Preview Ready</div>',
            '  <div style="background:#2a2a3e;padding:8px 12px;border-radius:6px;border-left:3px solid #f5a623;white-space:pre-wrap;max-height:120px;overflow-y:auto;" id="solace-preview-text"></div>',
            '</div>',
            '<div style="display:flex;gap:8px;">',
            '  <button id="solace-approve-btn" style="background:#27ae60;color:#fff;border:none;border-radius:6px;padding:8px 20px;cursor:pointer;font-size:13px;font-weight:600;">Approve</button>',
            '  <button id="solace-reject-btn" style="background:#e74c3c;color:#fff;border:none;border-radius:6px;padding:8px 20px;cursor:pointer;font-size:13px;font-weight:600;">Reject</button>',
            '</div>'
        ].join('\\n');

        var previewEl = document.getElementById('solace-preview-text');
        if (previewEl) previewEl.textContent = payload.preview_text;

        var approveBtn = document.getElementById('solace-approve-btn');
        var rejectBtn = document.getElementById('solace-reject-btn');
        var runId = payload.run_id || '';

        if (approveBtn) {
            approveBtn.onclick = function() {
                sendAction('approve', runId);
                clearFsmArea();
            };
        }
        if (rejectBtn) {
            rejectBtn.onclick = function() {
                sendAction('reject', runId);
                clearFsmArea();
            };
        }
    }

    function showBlockPanel(payload) {
        fsmArea.dataset.hasContent = 'true';
        fsmArea.style.display = expanded ? 'block' : 'none';
        fsmArea.innerHTML = [
            '<div style="font-weight:600;color:#e74c3c;margin-bottom:4px;">Blocked</div>',
            '<div style="background:#2a2a3e;padding:8px 12px;border-radius:6px;border-left:3px solid #e74c3c;" id="solace-block-reason"></div>'
        ].join('\\n');
        var reasonEl = document.getElementById('solace-block-reason');
        if (reasonEl) reasonEl.textContent = payload.block_reason;
    }

    function showErrorPanel(payload) {
        fsmArea.dataset.hasContent = 'true';
        fsmArea.style.display = expanded ? 'block' : 'none';
        fsmArea.innerHTML = [
            '<div style="font-weight:600;color:#e74c3c;margin-bottom:4px;">Failed</div>',
            '<div style="background:#2a2a3e;padding:8px 12px;border-radius:6px;border-left:3px solid #e74c3c;" id="solace-error-detail"></div>'
        ].join('\\n');
        var errorEl = document.getElementById('solace-error-detail');
        if (errorEl) errorEl.textContent = payload.error_detail;
    }

    function clearFsmArea() {
        fsmArea.innerHTML = '';
        fsmArea.dataset.hasContent = 'false';
        fsmArea.style.display = 'none';
    }

    function sendAction(action, runId) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'fsm_action',
                payload: { action: action, run_id: runId }
            }));
        }
        addMessage('system', action === 'approve' ? 'Approved. Executing...' : 'Rejected.');
    }

    function connectWS() {
        try {
            ws = new WebSocket(WS_URL);
            ws.onmessage = function(e) {
                try {
                    var msg = JSON.parse(e.data);
                    if (msg.type === 'chat') addMessage('assistant', msg.payload.content || '');
                    if (msg.type === 'state_update') {
                        window.postMessage({type: 'yinyang_state', state: msg.payload.state, app_name: msg.payload.app_name || ''}, '*');
                    }
                    if (msg.type === 'bottom_rail_update') {
                        window.postMessage({type: 'yinyang_bottom_rail', payload: msg.payload}, '*');
                    }
                    if (msg.type === 'credits_update') updateCredits(msg.payload);
                } catch(err) { console.warn('YY parse error:', err); }
            };
            ws.onclose = function() { ws = null; };
        } catch(err) { console.warn('YY WS error:', err); }
    }

    function addMessage(role, content) {
        var div = document.createElement('div');
        var roleStyles = {
            user: 'background:#2a3a5e;margin-left:auto;',
            assistant: 'background:#2a2a3e;',
            system: 'background:transparent;opacity:0.7;font-style:italic;text-align:center;'
        };
        div.style.cssText = 'margin-bottom:8px;padding:6px 10px;border-radius:8px;max-width:85%;' + (roleStyles[role] || roleStyles.assistant);
        div.textContent = content;
        chatArea.appendChild(div);
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function updateCredits(data) {
        var el = document.getElementById('solace-credits-summary');
        if (el && data) el.textContent = '$' + (data.balance || 0).toFixed(2) + ' credits';
    }

    function sendMessage() {
        var input = document.getElementById('solace-chat-input');
        var text = (input.value || '').trim();
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
        var btn = document.getElementById('solace-send-btn');
        var input = document.getElementById('solace-chat-input');
        if (btn) btn.onclick = sendMessage;
        if (input) input.onkeydown = function(e) { if (e.key === 'Enter') sendMessage(); };
    }, 100);
})();
"""
