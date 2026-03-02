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

from src.i18n import js_bundle, get_locale

logger = logging.getLogger("solace-browser.yinyang")

BOTTOM_RAIL_JS = (Path(__file__).parent.parent.parent / "static" / "bottom_rail.js").resolve()


async def inject_bottom_rail(
    page: Any,
    ws_url: str = "ws://localhost:9222/ws/yinyang",
    locale: str | None = None,
) -> None:
    """Inject bottom rail chat panel into a Playwright page.

    Injects window.YINYANG_I18N first so JS can read locale strings.
    """
    try:
        # 1. Inject i18n bundle so JS can read translations
        await page.add_init_script(js_bundle(locale or get_locale()))

        # 2. Inject bottom rail JS
        if BOTTOM_RAIL_JS.exists():
            js_code = BOTTOM_RAIL_JS.read_text(encoding="utf-8")
        else:
            js_code = _INLINE_BOTTOM_RAIL_JS
        js_code = js_code.replace("__WS_URL__", ws_url)
        await page.add_init_script(js_code)
        logger.debug("Bottom rail injected (locale: %s)", locale or get_locale())
    except Exception as exc:
        logger.warning(f"Failed to inject bottom rail: {exc}")


_INLINE_BOTTOM_RAIL_JS = """
(function() {
    if (document.getElementById('solace-bottom-rail')) return;

    // i18n helper — reads from window.YINYANG_I18N injected by Python
    var _i18n = window.YINYANG_I18N || {};
    function i(key, fallback) { return _i18n[key] || fallback; }

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
    var yyLogo = document.createElement('img');
    yyLogo.src = 'data:image/png;base64,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';
    yyLogo.style.cssText = 'width:24px;height:24px;margin-right:8px;';
    header.appendChild(yyLogo);
    var yyTitle = document.createElement('span');
    yyTitle.style.cssText = 'font-weight:600;';
    yyTitle.textContent = i('title', 'Yinyang');
    header.appendChild(yyTitle);
    var creditsSummary = document.createElement('span');
    creditsSummary.id = 'solace-credits-summary';
    creditsSummary.style.cssText = 'margin-left:8px;opacity:0.6;font-size:11px;';
    header.appendChild(creditsSummary);
    var toggleBtn = document.createElement('span');
    toggleBtn.id = 'solace-toggle-btn';
    toggleBtn.style.cssText = 'margin-left:auto;font-size:16px;';
    toggleBtn.textContent = '\\u25B2';
    header.appendChild(toggleBtn);
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
    var inputRow = document.createElement('div');
    inputRow.style.cssText = 'display:flex;gap:8px;';
    var chatInput = document.createElement('input');
    chatInput.id = 'solace-chat-input';
    chatInput.type = 'text';
    chatInput.placeholder = i('chat_placeholder', 'Ask Yinyang...');
    chatInput.style.cssText = 'flex:1;background:#2a2a3e;border:1px solid #444;border-radius:6px;padding:6px 10px;color:#fff;font-size:13px;outline:none;';
    inputRow.appendChild(chatInput);
    var sendBtn = document.createElement('button');
    sendBtn.id = 'solace-send-btn';
    sendBtn.style.cssText = 'background:#4a9eff;color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:13px;';
    sendBtn.textContent = i('send', 'Send');
    inputRow.appendChild(sendBtn);
    inputArea.appendChild(inputRow);

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
        document.getElementById('solace-toggle-btn').textContent = expanded ? '\\u25BC' : '\\u25B2';
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
        clearFsmArea();
        fsmArea.dataset.hasContent = 'true';
        fsmArea.style.display = expanded ? 'block' : 'none';

        var wrapper = document.createElement('div');
        wrapper.style.cssText = 'margin-bottom:8px;';
        var label = document.createElement('div');
        label.style.cssText = 'font-weight:600;color:#f5a623;margin-bottom:4px;';
        label.textContent = i('preview_ready', 'Preview Ready');
        wrapper.appendChild(label);
        var previewEl = document.createElement('div');
        previewEl.id = 'solace-preview-text';
        previewEl.style.cssText = 'background:#2a2a3e;padding:8px 12px;border-radius:6px;border-left:3px solid #f5a623;white-space:pre-wrap;max-height:120px;overflow-y:auto;';
        previewEl.textContent = payload.preview_text || '';
        wrapper.appendChild(previewEl);
        fsmArea.appendChild(wrapper);

        var btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:8px;';
        var approveBtn = document.createElement('button');
        approveBtn.id = 'solace-approve-btn';
        approveBtn.style.cssText = 'background:#27ae60;color:#fff;border:none;border-radius:6px;padding:8px 20px;cursor:pointer;font-size:13px;font-weight:600;';
        approveBtn.textContent = i('approve', 'Approve');
        var rejectBtn = document.createElement('button');
        rejectBtn.id = 'solace-reject-btn';
        rejectBtn.style.cssText = 'background:#e74c3c;color:#fff;border:none;border-radius:6px;padding:8px 20px;cursor:pointer;font-size:13px;font-weight:600;';
        rejectBtn.textContent = i('reject', 'Reject');
        btnRow.appendChild(approveBtn);
        btnRow.appendChild(rejectBtn);
        fsmArea.appendChild(btnRow);

        var runId = payload.run_id || '';
        approveBtn.onclick = function() { sendAction('approve', runId); clearFsmArea(); };
        rejectBtn.onclick = function() { sendAction('reject', runId); clearFsmArea(); };
    }

    function showBlockPanel(payload) {
        clearFsmArea();
        fsmArea.dataset.hasContent = 'true';
        fsmArea.style.display = expanded ? 'block' : 'none';
        var label = document.createElement('div');
        label.style.cssText = 'font-weight:600;color:#e74c3c;margin-bottom:4px;';
        label.textContent = i('blocked', 'Blocked');
        fsmArea.appendChild(label);
        var reasonEl = document.createElement('div');
        reasonEl.style.cssText = 'background:#2a2a3e;padding:8px 12px;border-radius:6px;border-left:3px solid #e74c3c;';
        reasonEl.textContent = payload.block_reason || '';
        fsmArea.appendChild(reasonEl);
    }

    function showErrorPanel(payload) {
        clearFsmArea();
        fsmArea.dataset.hasContent = 'true';
        fsmArea.style.display = expanded ? 'block' : 'none';
        var label = document.createElement('div');
        label.style.cssText = 'font-weight:600;color:#e74c3c;margin-bottom:4px;';
        label.textContent = i('failed', 'Failed');
        fsmArea.appendChild(label);
        var errorEl = document.createElement('div');
        errorEl.style.cssText = 'background:#2a2a3e;padding:8px 12px;border-radius:6px;border-left:3px solid #e74c3c;';
        errorEl.textContent = payload.error_detail || '';
        fsmArea.appendChild(errorEl);
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
        addMessage('system', action === 'approve' ? i('approved_executing', 'Approved. Executing...') : i('rejected', 'Rejected.'));
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
            addMessage('assistant', i('not_connected', 'Not connected. Reconnecting...'));
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
