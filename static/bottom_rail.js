(function() {
    if (document.getElementById('solace-bottom-rail')) return;

    var _i18n = window.YINYANG_I18N || {};
    function i(key, fallback) {
        var val = _i18n[key];
        return typeof val === 'string' && val.length ? val : fallback;
    }

    var COLLAPSED = '36px';
    var EXPANDED = '300px';
    var expanded = false;
    var ws = null;
    var WS_URL = '__WS_URL__';

    // CSP-safe: all DOM construction via createElement, never innerHTML
    var rail = document.createElement('div');
    rail.id = 'solace-bottom-rail';
    rail.style.cssText = 'position:fixed;bottom:0;left:0;right:0;height:'+COLLAPSED+';background:#081019;color:#eef3ff;font-family:system-ui,sans-serif;font-size:13px;z-index:2147483647;transition:height 0.25s ease;display:flex;flex-direction:column;box-shadow:0 -3px 12px rgba(0,0,0,0.5);border-top:1px solid #1e3048;';

    // Header bar (always visible 36px)
    var header = document.createElement('div');
    header.style.cssText = 'display:flex;align-items:center;padding:0 14px;height:36px;min-height:36px;cursor:pointer;gap:8px;flex-shrink:0;';

    var logo = document.createElement('span');
    logo.style.cssText = 'font-size:16px;line-height:1;';
    logo.textContent = '\u262F';

    var brandName = document.createElement('span');
    brandName.style.cssText = 'font-weight:700;font-size:12px;color:#64c4ff;letter-spacing:0.04em;';
    brandName.textContent = i('title', 'Yinyang');

    var credits = document.createElement('span');
    credits.id = 'solace-credits';
    credits.style.cssText = 'font-size:11px;color:#6b8aad;';

    var stateEl = document.createElement('span');
    stateEl.id = 'solace-state';
    stateEl.style.cssText = 'font-size:11px;color:#4ecb8f;margin-left:4px;';
    stateEl.textContent = i('idle', 'IDLE');

    var toggle = document.createElement('span');
    toggle.id = 'solace-toggle';
    toggle.style.cssText = 'margin-left:auto;font-size:11px;color:#6b8aad;user-select:none;';
    toggle.textContent = '\u25B2';

    header.appendChild(logo);
    header.appendChild(brandName);
    header.appendChild(credits);
    header.appendChild(stateEl);
    header.appendChild(toggle);
    header.addEventListener('click', toggleRail);
    rail.appendChild(header);

    // Chat area (hidden when collapsed)
    var chat = document.createElement('div');
    chat.id = 'solace-chat';
    chat.style.cssText = 'flex:1;overflow-y:auto;padding:10px 14px;display:none;background:#050d18;';
    rail.appendChild(chat);

    // Input area
    var inputArea = document.createElement('div');
    inputArea.style.cssText = 'display:none;padding:8px 14px;border-top:1px solid #1e3048;background:#081019;flex-shrink:0;';

    var inputRow = document.createElement('div');
    inputRow.style.cssText = 'display:flex;gap:8px;';

    var input = document.createElement('input');
    input.id = 'solace-input';
    input.type = 'text';
    input.placeholder = i('chat_placeholder', '');
    input.style.cssText = 'flex:1;background:#0f1825;border:1px solid #1e3048;border-radius:6px;padding:6px 10px;color:#eef3ff;font-size:13px;outline:none;';

    var sendBtn = document.createElement('button');
    sendBtn.style.cssText = 'background:#64c4ff;color:#050d18;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:12px;font-weight:700;';
    sendBtn.textContent = i('send', '');
    sendBtn.addEventListener('click', sendMsg);

    input.addEventListener('keydown', function(e) { if (e.key === 'Enter') sendMsg(); });

    inputRow.appendChild(input);
    inputRow.appendChild(sendBtn);
    inputArea.appendChild(inputRow);
    rail.appendChild(inputArea);

    document.documentElement.appendChild(rail);

    function toggleRail() {
        expanded = !expanded;
        rail.style.height = expanded ? EXPANDED : COLLAPSED;
        chat.style.display = expanded ? 'block' : 'none';
        inputArea.style.display = expanded ? 'block' : 'none';
        toggle.textContent = expanded ? '\u25BC' : '\u25B2';
        if (expanded && !ws) connectWS();
    }

    function connectWS() {
        try {
            ws = new WebSocket(WS_URL);
            ws.onmessage = function(e) {
                try {
                    var msg = JSON.parse(e.data);
                    if (msg.type === 'chat') addMsg('assistant', msg.payload.content || '');
                    if (msg.type === 'state_update') updateState(msg.payload.state || '');
                    if (msg.type === 'credits_update') {
                        credits.textContent = ' \u00B7 $' + (msg.payload.balance || 0).toFixed(2);
                    }
                } catch(err) {}
            };
            ws.onclose = function() { ws = null; updateState('IDLE'); };
            ws.onerror = function() { ws = null; };
        } catch(err) {}
    }

    function updateState(s) {
        var upper = String(s || '').toUpperCase();
        if (upper === 'PREVIEW_READY') stateEl.textContent = i('preview_ready', upper);
        else if (upper === 'BLOCKED') stateEl.textContent = i('blocked', upper);
        else if (upper === 'FAILED') stateEl.textContent = i('failed', upper);
        else if (upper === 'IDLE') stateEl.textContent = i('idle', upper);
        else stateEl.textContent = upper;
        stateEl.style.color = s === 'DONE' ? '#4ecb8f' : (s === 'BLOCKED' || s === 'FAILED' ? '#ff6b35' : '#64c4ff');
        if (s === 'PREVIEW_READY' || s === 'BLOCKED' || s === 'FAILED') {
            if (!expanded) toggleRail();
        }
        if (s === 'DONE' || s === 'SEALED_ABORT') {
            if (expanded) toggleRail();
        }
    }

    function addMsg(role, text) {
        var div = document.createElement('div');
        div.style.cssText = 'margin-bottom:8px;padding:8px 12px;border-radius:8px;font-size:12px;line-height:1.5;' +
            (role === 'user' ? 'background:#172335;margin-left:20%;color:#c8d8e8;' : 'background:#0f1e30;color:#eef3ff;');
        var label = document.createElement('div');
        label.style.cssText = 'font-size:10px;font-weight:700;color:#64c4ff;margin-bottom:4px;';
        label.textContent = role === 'user' ? '\u2022' : '\u262F';
        var body = document.createElement('div');
        body.textContent = text;
        div.appendChild(label);
        div.appendChild(body);
        chat.appendChild(div);
        chat.scrollTop = chat.scrollHeight;
    }

    function sendMsg() {
        var text = (input.value || '').trim();
        if (!text) return;
        addMsg('user', text);
        input.value = '';
        if (ws && ws.readyState === 1) {
            ws.send(JSON.stringify({type:'chat', payload:{content:text}}));
        } else {
            addMsg('assistant', '\u2026');
            connectWS();
        }
    }

    // Auto-connect WebSocket
    connectWS();
})();
