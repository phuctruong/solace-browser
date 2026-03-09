# PATCH DIFF — TASK-005-websocket

- Verified ws://localhost:8888/ws/yinyang is the only WebSocket endpoint.
- Verified the sidebar exposes four tabs: Now, Runs, Chat, More.
- Removed extension-style page access and silent fallback behavior from sidepanel.js.
- Added an explicit connection indicator to the Now tab and synchronized status text across the panel.
- Updated the More tab server URL to the full WebSocket path.
- File counts: sidepanel.js (+274 lines), sidepanel.html (+107 lines), sidepanel.css (+300 lines).

## Unified Diff
diff --git a/chrome/browser/resources/solace/sidepanel.js b/chrome/browser/resources/solace/sidepanel.js
new file mode 100644
index 0000000000000..8a7f160de5b74
--- /dev/null
+++ b/chrome/browser/resources/solace/sidepanel.js
@@ -0,0 +1,274 @@
+// sidepanel.js — Yinyang Sidebar WebSocket Client
+// DNA: sidebar(ws) = connect(8888) × handle_messages × tab_switch × chat_send → native_ai_panel
+// Auth: 65537 | Native Chrome WebUI — NOT a browser extension
+// Connect: ws://localhost:8888/ws/yinyang
+
+(function () {
+  'use strict';
+
+  const WS_LABEL = 'Yinyang Server';
+  const WS_URL = 'ws://localhost:8888/ws/yinyang';
+  const RECONNECT_DELAY_MS = 3000;
+  const MAX_RECONNECT_DELAY_MS = 30000;
+
+  let ws = null;
+  let reconnectDelay = RECONNECT_DELAY_MS;
+  let reconnectTimer = null;
+
+  // ── WebSocket lifecycle ────────────────────────────────────────────────────
+
+  function connect() {
+    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
+      return;
+    }
+
+    updateConnectionUi('connecting', 'Connecting...', 'Opening WebSocket to ' + WS_URL);
+
+    try {
+      ws = new WebSocket(WS_URL);
+    } catch (error) {
+      updateConnectionUi('error', 'Error', 'Failed to open WebSocket to ' + WS_URL);
+      return;
+    }
+
+    ws.addEventListener('open', onOpen);
+    ws.addEventListener('message', onMessage);
+    ws.addEventListener('close', onClose);
+    ws.addEventListener('error', onError);
+  }
+
+  function onOpen() {
+    reconnectDelay = RECONNECT_DELAY_MS;
+    clearTimeout(reconnectTimer);
+    updateConnectionUi('online', 'Connected', 'Connected to ' + WS_LABEL + ' at ' + WS_URL);
+    requestNowData();
+  }
+
+  function onMessage(event) {
+    let msg;
+    try {
+      msg = JSON.parse(event.data);
+    } catch (error) {
+      updateConnectionUi('error', 'Error', 'Received invalid WebSocket data from ' + WS_LABEL);
+      appendChatMessage('ai', 'Error: Invalid response received from ' + WS_LABEL + '.');
+      return;
+    }
+    handleMessage(msg);
+  }
+
+  function onClose() {
+    ws = null;
+    updateConnectionUi('offline', 'Disconnected', 'Lost connection to ' + WS_LABEL + '. Retrying...');
+    scheduleReconnect();
+  }
+
+  function onError() {
+    updateConnectionUi('error', 'Error', 'Unable to reach ' + WS_LABEL + ' at ' + WS_URL);
+    if (ws) {
+      ws.close();
+    }
+  }
+
+  function scheduleReconnect() {
+    clearTimeout(reconnectTimer);
+    reconnectTimer = setTimeout(function () {
+      connect();
+      reconnectDelay = Math.min(reconnectDelay * 1.5, MAX_RECONNECT_DELAY_MS);
+    }, reconnectDelay);
+  }
+
+  function send(data) {
+    if (ws && ws.readyState === WebSocket.OPEN) {
+      ws.send(JSON.stringify(data));
+      return true;
+    }
+
+    return false;
+  }
+
+  // ── Message handling ───────────────────────────────────────────────────────
+
+  function handleMessage(msg) {
+    const type = msg.type || '';
+
+    if (type === 'credits') {
+      renderApps(msg.apps || []);
+    } else if (type === 'detect') {
+      renderApps(msg.matches || []);
+    } else if (type === 'run_update') {
+      renderRuns(msg.runs || []);
+    } else if (type === 'chat_response') {
+      appendChatMessage('ai', msg.content || '');
+    } else if (type === 'error') {
+      updateConnectionUi('error', 'Error', msg.message || ('Server error from ' + WS_LABEL));
+      appendChatMessage('ai', 'Error: ' + (msg.message || 'Unknown error'));
+    } else if (type === 'pong') {
+      // Heartbeat acknowledged — connection alive
+    }
+  }
+
+  // ── Tab switching ──────────────────────────────────────────────────────────
+
+  window.switchTab = function (tabName) {
+    // Deactivate all tabs
+    document.querySelectorAll('.yy-tab').forEach(function (t) {
+      t.classList.remove('active');
+      t.setAttribute('aria-selected', 'false');
+    });
+    document.querySelectorAll('.yy-panel').forEach(function (p) {
+      p.classList.remove('active');
+      p.setAttribute('aria-hidden', 'true');
+    });
+
+    // Activate selected tab
+    const tabBtn = document.getElementById('tab-' + tabName);
+    const panel = document.getElementById('panel-' + tabName);
+    if (tabBtn) {
+      tabBtn.classList.add('active');
+      tabBtn.setAttribute('aria-selected', 'true');
+    }
+    if (panel) {
+      panel.classList.add('active');
+      panel.removeAttribute('aria-hidden');
+    }
+
+    // Tab-specific actions
+    if (tabName === 'now') {
+      requestNowData();
+    }
+  };
+
+  // ── Current context refresh ────────────────────────────────────────────────
+
+  function requestNowData() {
+    if (!ws) {
+      updateConnectionUi('offline', 'Disconnected', 'Waiting for ' + WS_LABEL + ' at ' + WS_URL);
+      return;
+    }
+
+    if (ws.readyState === WebSocket.CONNECTING) {
+      updateConnectionUi('connecting', 'Connecting...', 'Waiting for ' + WS_LABEL + ' at ' + WS_URL);
+      return;
+    }
+
+    if (!send({ type: 'credits' })) {
+      updateConnectionUi('error', 'Error', 'Cannot request sidebar data because ' + WS_LABEL + ' is unavailable.');
+    }
+  }
+
+  // ── Render functions ───────────────────────────────────────────────────────
+
+  function renderApps(apps) {
+    const container = document.getElementById('detected-apps');
+    if (!container) return;
+
+    if (!apps || apps.length === 0) {
+      container.innerHTML = '<p class="yy-empty">No apps detected for this page.</p>';
+      return;
+    }
+
+    const items = apps.map(function (app) {
+      const name = safeText(app.name || app.id || 'Unknown App');
+      return '<div class="yy-app-item"><span class="yy-app-name">' + name + '</span></div>';
+    });
+
+    container.innerHTML = items.join('');
+  }
+
+  function renderRuns(runs) {
+    const container = document.getElementById('runs-list');
+    if (!container) return;
+
+    if (!runs || runs.length === 0) {
+      container.innerHTML = '<p class="yy-empty">No active runs.</p>';
+      return;
+    }
+
+    const items = runs.map(function (run) {
+      const id = safeText((run.run_id || '').slice(0, 8));
+      const status = safeText(run.status || 'unknown');
+      return '<div class="yy-app-item"><span class="yy-app-name">' + id + '</span><span>' + status + '</span></div>';
+    });
+
+    container.innerHTML = items.join('');
+  }
+
+  // ── Chat ───────────────────────────────────────────────────────────────────
+
+  window.sendChat = function (event) {
+    event.preventDefault();
+    const input = document.getElementById('chat-input');
+    if (!input) return;
+
+    const text = (input.value || '').trim();
+    if (!text) return;
+
+    appendChatMessage('user', text);
+    input.value = '';
+
+    if (!send({ type: 'chat', content: text })) {
+      appendChatMessage('ai', 'Error: Not connected to ' + WS_LABEL + '.');
+      updateConnectionUi('error', 'Error', 'Chat requires an active WebSocket connection to ' + WS_LABEL + '.');
+    }
+  };
+
+  function appendChatMessage(role, text) {
+    const container = document.getElementById('chat-messages');
+    if (!container) return;
+
+    const div = document.createElement('div');
+    div.className = 'yy-msg yy-msg-' + (role === 'user' ? 'user' : 'ai');
+    div.textContent = text; // textContent — safe, no XSS risk
+    container.appendChild(div);
+    container.scrollTop = container.scrollHeight;
+  }
+
+  // ── Status helpers ─────────────────────────────────────────────────────────
+
+  function setStatus(state) {
+    document.querySelectorAll('#ws-status-dot, #now-status-dot').forEach(function (dot) {
+      dot.className = 'status-dot status-' + state;
+    });
+  }
+
+  function updateConnectionUi(state, summary, detail) {
+    setStatus(state);
+
+    const summaryEls = ['conn-status', 'now-conn-status'];
+    summaryEls.forEach(function (id) {
+      const el = document.getElementById(id);
+      if (el) {
+        el.textContent = summary;
+      }
+    });
+
+    const detailEl = document.getElementById('now-conn-detail');
+    if (detailEl) {
+      detailEl.textContent = detail;
+      detailEl.setAttribute('data-state', state);
+    }
+  }
+
+  // ── Security: safe text (XSS prevention for innerHTML paths) ───────────────
+
+  function safeText(str) {
+    const d = document.createElement('div');
+    d.textContent = String(str);
+    return d.innerHTML;
+  }
+
+  // ── Init ───────────────────────────────────────────────────────────────────
+
+  document.addEventListener('DOMContentLoaded', function () {
+    updateConnectionUi('connecting', 'Connecting...', 'Opening WebSocket to ' + WS_URL);
+    connect();
+
+    // Heartbeat every 30 seconds to keep connection alive
+    setInterval(function () {
+      if (ws && ws.readyState === WebSocket.OPEN) {
+        send({ type: 'ping' });
+      }
+    }, 30000);
+  });
+
+})();

diff --git a/chrome/browser/resources/solace/sidepanel.html b/chrome/browser/resources/solace/sidepanel.html
new file mode 100644
index 0000000000000..cdd83c5a9e6b8
--- /dev/null
+++ b/chrome/browser/resources/solace/sidepanel.html
@@ -0,0 +1,107 @@
+<!DOCTYPE html>
+<html lang="en">
+<head>
+  <meta charset="UTF-8">
+  <meta name="viewport" content="width=device-width, initial-scale=1.0">
+  <title>Yinyang</title>
+  <link rel="stylesheet" href="sidepanel.css">
+</head>
+<body>
+  <div id="app">
+    <header class="yy-header">
+      <div class="yy-logo">
+        <span class="yy-logo-icon">☯</span>
+        <span class="yy-logo-text">Yinyang</span>
+      </div>
+      <div class="yy-status">
+        <span id="ws-status-dot" class="status-dot status-offline"></span>
+      </div>
+    </header>
+
+    <nav class="yy-tabs" role="tablist">
+      <button class="yy-tab active" id="tab-now" role="tab" aria-selected="true" onclick="switchTab('now')">Now</button>
+      <button class="yy-tab" id="tab-runs" role="tab" aria-selected="false" onclick="switchTab('runs')">Runs</button>
+      <button class="yy-tab" id="tab-chat" role="tab" aria-selected="false" onclick="switchTab('chat')">Chat</button>
+      <button class="yy-tab" id="tab-more" role="tab" aria-selected="false" onclick="switchTab('more')">More</button>
+    </nav>
+
+    <main class="yy-content">
+      <!-- NOW tab: Current page context + detected apps -->
+      <section id="panel-now" class="yy-panel active" role="tabpanel">
+        <div class="yy-section">
+          <h3 class="yy-section-title">Connection</h3>
+          <div class="yy-connection-card">
+            <div class="yy-connection-row">
+              <span id="now-status-dot" class="status-dot status-offline"></span>
+              <span id="now-conn-status" class="yy-connection-status" aria-live="polite">Disconnected</span>
+            </div>
+            <p id="now-conn-detail" class="yy-connection-detail" aria-live="polite">
+              Waiting for Yinyang Server at ws://localhost:8888/ws/yinyang
+            </p>
+          </div>
+        </div>
+        <div class="yy-section">
+          <h3 class="yy-section-title">Current Page</h3>
+          <div id="detected-apps" class="yy-app-list">
+            <p class="yy-empty">No apps detected for this page.</p>
+          </div>
+        </div>
+        <div class="yy-section">
+          <h3 class="yy-section-title">Quick Actions</h3>
+          <div id="quick-actions" class="yy-actions"></div>
+        </div>
+      </section>
+
+      <!-- RUNS tab: Active and recent recipe runs -->
+      <section id="panel-runs" class="yy-panel" role="tabpanel" aria-hidden="true">
+        <div class="yy-section">
+          <h3 class="yy-section-title">Active Runs</h3>
+          <div id="runs-list" class="yy-runs-list">
+            <p class="yy-empty">No active runs.</p>
+          </div>
+        </div>
+      </section>
+
+      <!-- CHAT tab: Chat with Yinyang AI -->
+      <section id="panel-chat" class="yy-panel" role="tabpanel" aria-hidden="true">
+        <div class="yy-chat-messages" id="chat-messages"></div>
+        <form class="yy-chat-input" id="chat-form" onsubmit="sendChat(event)">
+          <input
+            type="text"
+            id="chat-input"
+            class="yy-input"
+            placeholder="Ask Yinyang anything..."
+            autocomplete="off"
+            maxlength="1000"
+          >
+          <button type="submit" class="yy-btn yy-btn-send">&#8594;</button>
+        </form>
+      </section>
+
+      <!-- MORE tab: Settings and hub link -->
+      <section id="panel-more" class="yy-panel" role="tabpanel" aria-hidden="true">
+        <div class="yy-section">
+          <h3 class="yy-section-title">Connection</h3>
+          <div class="yy-info-row">
+            <span class="yy-label">Server</span>
+            <span id="server-url" class="yy-value">ws://localhost:8888/ws/yinyang</span>
+          </div>
+          <div class="yy-info-row">
+            <span class="yy-label">Status</span>
+            <span id="conn-status" class="yy-value" aria-live="polite">Connecting...</span>
+          </div>
+        </div>
+        <div class="yy-section">
+          <h3 class="yy-section-title">Solace Hub</h3>
+          <a href="http://localhost:8888/start" class="yy-btn yy-btn-outline" target="_blank">Open Hub Dashboard</a>
+        </div>
+        <div class="yy-section">
+          <h3 class="yy-section-title">About</h3>
+          <p class="yy-about-text">Yinyang v1.0 &#8212; Native AI Panel<br>Part of Solace Browser</p>
+        </div>
+      </section>
+    </main>
+  </div>
+  <script src="sidepanel.js"></script>
+</body>
+</html>

diff --git a/chrome/browser/resources/solace/sidepanel.css b/chrome/browser/resources/solace/sidepanel.css
new file mode 100644
index 0000000000000..dfa0af688f74d
--- /dev/null
+++ b/chrome/browser/resources/solace/sidepanel.css
@@ -0,0 +1,300 @@
+/* Yinyang Sidebar — Design Tokens */
+:root {
+  --yy-bg: #0a0a0a;
+  --yy-bg-card: #141414;
+  --yy-bg-input: #1e1e1e;
+  --yy-border: #2a2a2a;
+  --yy-accent: #00ff88;
+  --yy-accent-dim: #00cc6a;
+  --yy-text: #e8e8e8;
+  --yy-text-muted: #888;
+  --yy-red: #ff4444;
+  --yy-yellow: #ffcc00;
+  --yy-tab-active: #00ff88;
+  --yy-radius: 6px;
+  --yy-font: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
+  --yy-header-height: 44px;
+  --yy-tabs-height: 40px;
+}
+
+/* Reset */
+*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
+
+body {
+  background: var(--yy-bg);
+  color: var(--yy-text);
+  font-family: var(--yy-font);
+  font-size: 13px;
+  height: 100vh;
+  overflow: hidden;
+  -webkit-font-smoothing: antialiased;
+}
+
+/* App container */
+#app {
+  display: flex;
+  flex-direction: column;
+  height: 100vh;
+}
+
+/* Header */
+.yy-header {
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  height: var(--yy-header-height);
+  padding: 0 12px;
+  background: var(--yy-bg-card);
+  border-bottom: 1px solid var(--yy-border);
+  flex-shrink: 0;
+}
+
+.yy-logo {
+  display: flex;
+  align-items: center;
+  gap: 6px;
+}
+
+.yy-logo-icon { font-size: 18px; }
+.yy-logo-text { font-weight: 600; letter-spacing: 0.5px; color: var(--yy-accent); }
+.yy-status { display: flex; align-items: center; gap: 6px; }
+
+/* Status dot */
+.status-dot {
+  width: 8px;
+  height: 8px;
+  border-radius: 50%;
+  display: inline-block;
+}
+.status-online { background: var(--yy-accent); box-shadow: 0 0 6px var(--yy-accent); }
+.status-connecting { background: var(--yy-yellow); box-shadow: 0 0 6px rgba(255, 204, 0, 0.5); }
+.status-offline { background: #555; }
+.status-error { background: var(--yy-red); }
+
+/* Tabs */
+.yy-tabs {
+  display: flex;
+  height: var(--yy-tabs-height);
+  background: var(--yy-bg-card);
+  border-bottom: 1px solid var(--yy-border);
+  flex-shrink: 0;
+}
+
+.yy-tab {
+  flex: 1;
+  background: none;
+  border: none;
+  color: var(--yy-text-muted);
+  font-size: 12px;
+  font-weight: 500;
+  cursor: pointer;
+  border-bottom: 2px solid transparent;
+  transition: color 0.15s, border-color 0.15s;
+  font-family: var(--yy-font);
+}
+
+.yy-tab:hover { color: var(--yy-text); }
+.yy-tab.active {
+  color: var(--yy-tab-active);
+  border-bottom-color: var(--yy-tab-active);
+}
+
+/* Content */
+.yy-content {
+  flex: 1;
+  overflow: hidden;
+  position: relative;
+}
+
+.yy-panel {
+  display: none;
+  height: 100%;
+  overflow-y: auto;
+  padding: 12px;
+}
+
+.yy-panel.active { display: block; }
+
+/* Sections */
+.yy-section {
+  margin-bottom: 16px;
+}
+
+.yy-section-title {
+  font-size: 11px;
+  font-weight: 600;
+  text-transform: uppercase;
+  letter-spacing: 0.8px;
+  color: var(--yy-text-muted);
+  margin-bottom: 8px;
+}
+
+/* App list */
+.yy-app-list, .yy-runs-list {
+  display: flex;
+  flex-direction: column;
+  gap: 6px;
+}
+
+.yy-app-item {
+  background: var(--yy-bg-card);
+  border: 1px solid var(--yy-border);
+  border-radius: var(--yy-radius);
+  padding: 8px 10px;
+  display: flex;
+  align-items: center;
+  justify-content: space-between;
+  gap: 8px;
+}
+
+.yy-app-name { font-weight: 500; flex: 1; }
+
+/* Connection state */
+.yy-connection-card {
+  background: var(--yy-bg-card);
+  border: 1px solid var(--yy-border);
+  border-radius: var(--yy-radius);
+  padding: 10px;
+}
+
+.yy-connection-row {
+  display: flex;
+  align-items: center;
+  gap: 8px;
+  margin-bottom: 6px;
+}
+
+.yy-connection-status {
+  font-weight: 600;
+  color: var(--yy-text);
+}
+
+.yy-connection-detail {
+  color: var(--yy-text-muted);
+  font-size: 12px;
+  line-height: 1.5;
+  word-break: break-word;
+}
+
+.yy-connection-detail[data-state="connecting"] { color: var(--yy-yellow); }
+.yy-connection-detail[data-state="error"] { color: var(--yy-red); }
+
+/* Buttons */
+.yy-btn {
+  background: var(--yy-accent);
+  color: #000;
+  border: none;
+  border-radius: var(--yy-radius);
+  padding: 6px 12px;
+  font-size: 12px;
+  font-weight: 600;
+  cursor: pointer;
+  font-family: var(--yy-font);
+  transition: background 0.15s;
+}
+.yy-btn:hover { background: var(--yy-accent-dim); }
+
+.yy-btn-outline {
+  background: none;
+  color: var(--yy-accent);
+  border: 1px solid var(--yy-accent);
+  text-decoration: none;
+  display: inline-block;
+  padding: 6px 12px;
+  border-radius: var(--yy-radius);
+  font-size: 12px;
+  font-weight: 600;
+  text-align: center;
+}
+
+.yy-btn-send {
+  padding: 6px 10px;
+  font-size: 16px;
+  flex-shrink: 0;
+}
+
+/* Empty state */
+.yy-empty {
+  color: var(--yy-text-muted);
+  font-size: 12px;
+  text-align: center;
+  padding: 16px 0;
+}
+
+/* Chat */
+.yy-chat-messages {
+  flex: 1;
+  overflow-y: auto;
+  padding: 8px;
+  display: flex;
+  flex-direction: column;
+  gap: 8px;
+  height: calc(100% - 52px);
+}
+
+#panel-chat {
+  display: none;
+  flex-direction: column;
+  padding: 0;
+}
+#panel-chat.active { display: flex; }
+
+.yy-chat-input {
+  display: flex;
+  gap: 6px;
+  padding: 8px;
+  border-top: 1px solid var(--yy-border);
+  flex-shrink: 0;
+}
+
+.yy-input {
+  flex: 1;
+  background: var(--yy-bg-input);
+  border: 1px solid var(--yy-border);
+  border-radius: var(--yy-radius);
+  color: var(--yy-text);
+  padding: 6px 10px;
+  font-size: 13px;
+  font-family: var(--yy-font);
+  outline: none;
+}
+.yy-input:focus { border-color: var(--yy-accent); }
+
+/* Chat messages */
+.yy-msg {
+  padding: 8px 10px;
+  border-radius: var(--yy-radius);
+  max-width: 90%;
+  font-size: 13px;
+  line-height: 1.4;
+  word-break: break-word;
+}
+.yy-msg-user {
+  background: var(--yy-accent);
+  color: #000;
+  align-self: flex-end;
+}
+.yy-msg-ai {
+  background: var(--yy-bg-card);
+  border: 1px solid var(--yy-border);
+  align-self: flex-start;
+}
+
+/* Info rows (More tab) */
+.yy-info-row {
+  display: flex;
+  justify-content: space-between;
+  padding: 4px 0;
+  border-bottom: 1px solid var(--yy-border);
+}
+.yy-label { color: var(--yy-text-muted); }
+.yy-value { color: var(--yy-text); font-family: monospace; font-size: 12px; }
+
+.yy-about-text {
+  color: var(--yy-text-muted);
+  font-size: 12px;
+  line-height: 1.6;
+}
+
+/* Actions */
+.yy-actions { display: flex; flex-direction: column; gap: 6px; }
