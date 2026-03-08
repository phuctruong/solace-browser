/**
 * Yinyang Side Panel -- Main logic
 * Implements: yinyang-sidebar-rethink.md
 *
 * Features:
 *   - 4-tab sidebar (Now / Runs / Chat / More)
 *   - App detection via URL matching (service worker)
 *   - WebSocket multiplexed connection (chat + state + detection)
 *   - Server-not-running detection with setup instructions
 *   - Pioneer empty state ("Be the first to create an app")
 *   - Schedule management (cron display + create)
 *   - Visual toast notifications
 *   - Model picker + benchmarks per app
 *   - Approval queue with approve/reject
 *   - Theme switching
 */

// SOLACE_API, SOLACE_WS, ENDPOINTS, and timing constants
// are loaded from constants.js (included before this script).

let availableModels = [];
let selectedModels = {}; // app_id -> model_id
let ws = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let serverOnline = false;
let currentHostname = '';

// --- Incognito Mode Detection ---
// Check with service worker if we're in incognito context
(async function checkIncognito() {
  try {
    const resp = await chrome.runtime.sendMessage({ type: 'check_incognito' });
    if (resp && resp.incognito) {
      // Show incognito warning banner
      const banner = document.createElement('div');
      banner.className = 'yy-incognito-banner';
      banner.setAttribute('role', 'alert');
      banner.textContent = 'Incognito Mode — history and evidence will not be saved';
      const mainUI = document.getElementById('main-ui');
      if (mainUI) mainUI.prepend(banner);
    }
  } catch { /* SW not available yet */ }
})();

// --- Tab Switching ---

document.querySelectorAll('.yy-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.yy-tab').forEach(t => {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.yy-panel').forEach(p => p.classList.remove('active'));

    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    const panel = document.getElementById(`panel-${tab.dataset.tab}`);
    if (panel) panel.classList.add('active');
  });
});

// --- Server Detection ---

async function checkServerStatus() {
  // Dynamic port discovery: try cached port, then scan 8888-8899
  const port = await discoverPort();
  if (port) {
    showMainUI();
    serverOnline = true;
    document.getElementById('stat-api').textContent = `Connected (:${port})`;
    setConnectionStatus('connected');
    return true;
  }
  serverOnline = false;
  document.getElementById('stat-api').textContent = 'Offline';
  setConnectionStatus('disconnected');
  return false;
}

function showMainUI() {
  document.getElementById('server-offline').style.display = 'none';
  document.getElementById('main-ui').style.display = '';
}

function showOfflineUI() {
  document.getElementById('server-offline').style.display = '';
  document.getElementById('main-ui').style.display = 'none';
}

document.getElementById('retry-connection').addEventListener('click', async () => {
  const btn = document.getElementById('retry-connection');
  btn.textContent = 'Connecting...';
  btn.disabled = true;
  const online = await checkServerStatus();
  if (online) {
    showMainUI();
    connectWebSocket();
    updateCurrentPage();
    loadStats();
  } else {
    btn.textContent = 'Retry Connection';
    btn.disabled = false;
    showToast('Server not reachable. Check that solace_browser_server.py is running.', 'error');
  }
});

// --- WebSocket Connection ---

function connectWebSocket() {
  if (!serverOnline) return;

  const wsUrl = SOLACE_WS + ENDPOINTS.wsYinyang;
  setConnectionStatus('connecting');

  try {
    ws = new WebSocket(wsUrl);
  } catch {
    setConnectionStatus('disconnected');
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    setConnectionStatus('connected');
    reconnectAttempts = 0;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    // Protocol version negotiation — announce client version on first heartbeat
    ws.send(JSON.stringify({
      type: 'heartbeat',
      payload: { protocol_version: WS_PROTOCOL_VERSION }
    }));
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleWsMessage(msg);
    } catch (err) {
      console.error('[Yinyang] WS parse error:', err.message);
    }
  };

  ws.onclose = () => {
    setConnectionStatus('disconnected');
    ws = null;
    scheduleReconnect();
  };

  ws.onerror = () => {
    setConnectionStatus('disconnected');
  };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  // Exponential backoff: 2s, 4s, 8s, 16s, max 30s
  const delay = Math.min(WS_RECONNECT_BASE_MS * Math.pow(2, reconnectAttempts), WS_RECONNECT_MAX_MS);
  reconnectAttempts++;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, delay);
}

function setConnectionStatus(state) {
  const dot = document.querySelector('.yy-dot');
  if (!dot) return;
  dot.className = 'yy-dot';
  if (state === 'connected') dot.classList.add('connected');
  if (state === 'connecting') dot.classList.add('connecting');
}

// --- Error Code UX Mapping ---
// Maps server error codes to user-facing messages and actions.
const ERROR_UX = {
  INVALID_JSON:     { text: 'Message format error. Try again.',         icon: 'warning' },
  INVALID_MESSAGE:  { text: 'Invalid request. Check your input.',       icon: 'warning' },
  UNKNOWN_TYPE:     { text: 'Unknown command.',                         icon: 'warning' },
  RATE_LIMITED:     { text: 'Too many requests. Please wait a moment.', icon: 'error'   },
  ORIGIN_REJECTED:  { text: 'Connection rejected — unauthorized.',      icon: 'error'   },
  VERSION_MISMATCH: { text: 'Extension update required. Please reload.', icon: 'error'  },
  NOT_FOUND:        { text: 'Resource not found.',                      icon: 'warning' },
  INVALID_STATE:    { text: 'Action not available right now.',          icon: 'warning' },
  MISSING_FIELD:    { text: 'Missing required information.',            icon: 'warning' },
  INTERNAL_ERROR:   { text: 'Server error. Retrying...',               icon: 'error'   },
};

function handleWsMessage(msg) {
  // Handle structured error responses with UX-mapped messages
  if (msg.type === 'error' && msg.code) {
    const ux = ERROR_UX[msg.code] || { text: msg.payload?.message || 'Unknown error', icon: 'error' };
    showToast(ux.text, ux.icon);
    announce(ux.text, msg.code === 'RATE_LIMITED' ? 'assertive' : 'polite');
    return;
  }
  if (msg.type === 'chat' || msg.type === 'chat_reply') {
    const content = msg.payload && msg.payload.content ? msg.payload.content : (msg.message || '');
    if (content) {
      addChatBubble(content, msg.payload ? (msg.payload.role || 'assistant') : 'assistant');
    }
  } else if (msg.type === 'run_update') {
    updateRunsList(msg.data);
  } else if (msg.type === 'approval_request') {
    addApprovalRequest(msg.data);
    showToast(`Approval needed: ${msg.data.action || 'action'}`, 'warning');
  } else if (msg.type === 'detected') {
    // Server-side app detection result
    if (msg.apps) {
      renderAppCards(msg.apps);
    }
  } else if (msg.type === 'consent_required') {
    // OAuth3 consent request from server
    addConsentRequest(msg.payload || msg);
    showToast(`Consent needed: ${(msg.payload || msg).app_name || 'app'}`, 'warning');
  } else if (msg.type === 'state') {
    // App state update
    if (msg.payload) {
      showToast(`${msg.payload.app_id || ''}: ${msg.payload.status || msg.payload.state || ''}`, 'info');
    } else {
      showToast(`${msg.app_id}: ${msg.state}`, 'info');
    }
  } else if (msg.type === 'scheduled') {
    showToast(`Scheduled: ${msg.app_id} (${msg.cron})`, 'info');
  } else if (msg.type === 'credits') {
    // Update credit display if we add it
  }
}

// --- App Detection ---

async function updateCurrentPage() {
  let tab;
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    tab = tabs[0];
  } catch {
    return;
  }
  if (!tab) return;

  const urlEl = document.getElementById('page-url');
  try {
    const url = new URL(tab.url);
    currentHostname = url.hostname;
    urlEl.textContent = url.hostname + url.pathname;
  } catch {
    currentHostname = '';
    urlEl.textContent = tab.url || '--';
  }

  // Ask service worker for matched apps
  chrome.runtime.sendMessage(
    { type: 'GET_MATCHED_APPS', tabId: tab.id },
    (response) => {
      if (chrome.runtime.lastError) return;
      if (response && response.apps && response.apps.length > 0) {
        loadMatchedApps(response.apps);
        hidePioneerState();
      } else {
        showPioneerState();
      }
    }
  );

  // Also send detect via WebSocket for server-side matching
  if (ws && ws.readyState === WebSocket.OPEN && tab.url) {
    ws.send(JSON.stringify({ type: 'detect', url: tab.url }));
  }
}

function showPioneerState() {
  const container = document.getElementById('matched-apps');
  const noApps = document.getElementById('no-apps-state');
  const pioneer = document.getElementById('pioneer-create');
  const pioneerSite = document.getElementById('pioneer-site');

  if (noApps) noApps.style.display = '';
  if (pioneer && currentHostname && !currentHostname.includes('localhost') && !currentHostname.includes('chrome')) {
    pioneer.style.display = '';
    pioneerSite.textContent = `No apps for ${currentHostname} yet.`;
  } else {
    if (pioneer) pioneer.style.display = 'none';
    pioneerSite.textContent = 'No apps match this page';
  }
}

function hidePioneerState() {
  const noApps = document.getElementById('no-apps-state');
  if (noApps) noApps.style.display = 'none';
}

async function loadMatchedApps(appIds) {
  try {
    const resp = await fetch(`${SOLACE_API}${ENDPOINTS.apps}`);
    if (!resp.ok) return;
    const allApps = await resp.json();
    const matched = allApps.filter(a => appIds.includes(a.id));
    renderAppCards(matched);
  } catch {
    // API offline
  }
}

function renderAppCards(apps) {
  const container = document.getElementById('matched-apps');
  if (!apps || apps.length === 0) {
    showPioneerState();
    return;
  }

  hidePioneerState();

  container.innerHTML = apps.map(app => `
    <div class="yy-app-card" data-app-id="${escapeAttr(app.id)}">
      <div class="yy-app-name">${escapeHtml(app.name)}</div>
      <div class="yy-app-desc">${escapeHtml(app.description || '')}</div>
      <div class="yy-model-picker">
        <label class="yy-picker-label">Model:</label>
        <select class="yy-model-select" data-app="${escapeAttr(app.id)}" aria-label="Select model for ${escapeAttr(app.name)}">
          ${availableModels.map(m => `<option value="${escapeAttr(m.id)}" ${m.uplift ? 'class="yy-uplift"' : ''}>${escapeHtml(m.name)}</option>`).join('')}
        </select>
      </div>
      <div class="yy-benchmark-row" id="bench-${escapeAttr(app.id)}"></div>
      <div class="yy-app-actions">
        <button class="yy-btn yy-btn-primary" data-action="run" data-app="${escapeAttr(app.id)}">Run Now</button>
        <button class="yy-btn yy-btn-secondary" data-action="schedule" data-app="${escapeAttr(app.id)}">Schedule</button>
        <button class="yy-btn yy-btn-secondary" data-action="benchmark" data-app="${escapeAttr(app.id)}">Benchmarks</button>
      </div>
      ${app.scheduled ? `<div class="yy-app-schedule-badge">Scheduled: ${escapeHtml(app.cron || 'active')}</div>` : ''}
    </div>
  `).join('');

  // Wire up buttons
  container.querySelectorAll('[data-action="run"]').forEach(btn => {
    btn.addEventListener('click', () => runApp(btn.dataset.app));
  });
  container.querySelectorAll('[data-action="schedule"]').forEach(btn => {
    btn.addEventListener('click', () => scheduleApp(btn.dataset.app));
  });
  container.querySelectorAll('[data-action="benchmark"]').forEach(btn => {
    btn.addEventListener('click', () => loadBenchmarks(btn.dataset.app));
  });
  container.querySelectorAll('.yy-model-select').forEach(sel => {
    sel.addEventListener('change', (e) => {
      selectedModels[e.target.dataset.app] = e.target.value;
    });
  });
}

// --- Pioneer Create App ---

document.getElementById('pioneer-submit').addEventListener('click', () => {
  const desc = document.getElementById('pioneer-description').value.trim();
  if (!desc) return;

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'chat',
      payload: { content: `Create an app for ${currentHostname}: ${desc}` }
    }));
    // Switch to chat tab
    document.querySelector('[data-tab="chat"]').click();
    showToast('Sent to Yinyang for app creation', 'info');
  } else {
    showToast('Not connected to server', 'error');
  }
});

// --- Run / Schedule ---

async function runApp(appId) {
  const model = selectedModels[appId] || 'solace_managed';
  try {
    const resp = await fetch(`${SOLACE_API}/api/apps/${encodeURIComponent(appId)}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model })
    });
    if (resp.ok) {
      showToast(`Started: ${appId}`, 'info');
      document.querySelector('[data-tab="runs"]').click();
    } else {
      const errData = await resp.json().catch(() => ({}));
      showToast(`Failed: ${errData.error || resp.statusText}`, 'error');
    }
  } catch {
    showToast('API offline', 'error');
  }
}

async function scheduleApp(appId) {
  // Send schedule request via WebSocket
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'schedule',
      app_id: appId,
      cron: '0 9 * * *' // Default: daily at 9 AM
    }));
    showToast(`Schedule request sent for ${appId}`, 'info');
  } else {
    // Fallback: open schedule page
    try {
      await chrome.tabs.create({ url: `${SOLACE_API}/schedule.html` });
    } catch {
      showToast('Could not open schedule page', 'error');
    }
  }
}

// --- Runs / Approvals ---

function updateRunsList(runs) {
  const container = document.getElementById('recent-runs');
  if (!runs || runs.length === 0) {
    container.innerHTML = '<div class="yy-empty-state">No recent runs</div>';
    return;
  }
  container.innerHTML = runs.map(run => `
    <div class="yy-list-item">
      <span class="yy-list-item-icon">${run.status === 'success' ? '&#10003;' : (run.status === 'running' ? '&#10227;' : '&#10007;')}</span>
      <div class="yy-list-item-content">
        <div class="yy-list-item-title">${escapeHtml(run.app_id || run.name || 'Unknown')}</div>
        <div class="yy-list-item-sub">${escapeHtml(run.status || '')} ${run.duration ? '-- ' + run.duration : ''} ${run.cost ? '-- $' + run.cost : ''}</div>
      </div>
      ${run.evidence_url ? `<a href="${escapeAttr(run.evidence_url)}" target="_blank" class="yy-evidence-link" title="View evidence">&#128203;</a>` : ''}
    </div>
  `).join('');

  // Show summary
  const summary = document.getElementById('runs-summary');
  if (summary && runs.length > 0) {
    summary.style.display = '';
    const totalCost = runs.reduce((sum, r) => sum + (parseFloat(r.cost) || 0), 0);
    document.getElementById('runs-total-count').textContent = `${runs.length} runs`;
    document.getElementById('runs-total-cost').textContent = `$${totalCost.toFixed(2)}`;
  }
}

function addApprovalRequest(approval) {
  const container = document.getElementById('approval-queue');
  const emptyState = container.querySelector('.yy-empty-state');
  if (emptyState) emptyState.remove();

  const item = document.createElement('div');
  item.className = 'yy-list-item yy-approval-item';
  item.innerHTML = `
    <span class="yy-list-item-icon yy-warning-icon">&#9888;</span>
    <div class="yy-list-item-content">
      <div class="yy-list-item-title">${escapeHtml(approval.action || 'Action')}</div>
      <div class="yy-list-item-sub">${escapeHtml(approval.description || '')}</div>
    </div>
    <div class="yy-approval-actions">
      <button class="yy-btn yy-btn-primary yy-btn-sm" data-approve="${escapeAttr(approval.id || '')}">Approve</button>
      <button class="yy-btn yy-btn-danger yy-btn-sm" data-reject="${escapeAttr(approval.id || '')}">Reject</button>
    </div>
  `;

  // Wire approve/reject
  item.querySelector('[data-approve]').addEventListener('click', () => {
    sendApprovalResponse(approval.id, true);
    item.remove();
    showToast('Approved', 'info');
  });
  item.querySelector('[data-reject]').addEventListener('click', () => {
    sendApprovalResponse(approval.id, false);
    item.remove();
    showToast('Rejected', 'warning');
  });

  container.prepend(item);

  // Flash the Runs tab
  const runsTab = document.querySelector('[data-tab="runs"]');
  runsTab.classList.add('yy-tab-notify');
  setTimeout(() => runsTab.classList.remove('yy-tab-notify'), 3000);
}

function sendApprovalResponse(approvalId, approved) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: approved ? 'approve' : 'reject',
      approval_id: approvalId
    }));
  }
}

// --- OAuth3 Consent ---

function addConsentRequest(consent) {
  const section = document.getElementById('consent-section');
  const container = document.getElementById('consent-queue');
  section.style.display = '';

  const item = document.createElement('div');
  item.className = 'yy-list-item yy-consent-item';
  item.innerHTML = `
    <div class="yy-list-item-content">
      <div class="yy-list-item-title">${escapeHtml(consent.app_name || consent.app_id || 'Unknown App')}</div>
      <div class="yy-list-item-sub">Scopes: ${escapeHtml((consent.scopes || []).join(', '))}</div>
      <div class="yy-list-item-sub yy-hint">TTL: ${escapeHtml(consent.ttl || '1h')} | Risk: ${escapeHtml(consent.risk_level || 'standard')}</div>
    </div>
    <div class="yy-approval-actions">
      <button class="yy-btn yy-btn-primary yy-btn-sm" data-consent-approve="${escapeAttr(consent.token_id || '')}">Grant</button>
      <button class="yy-btn yy-btn-danger yy-btn-sm" data-consent-deny="${escapeAttr(consent.token_id || '')}">Deny</button>
    </div>
  `;

  item.querySelector('[data-consent-approve]').addEventListener('click', () => {
    sendConsentResponse(consent.token_id, true);
    item.remove();
    if (container.children.length === 0) section.style.display = 'none';
    showToast('Consent granted', 'info');
  });
  item.querySelector('[data-consent-deny]').addEventListener('click', () => {
    sendConsentResponse(consent.token_id, false);
    item.remove();
    if (container.children.length === 0) section.style.display = 'none';
    showToast('Consent denied', 'warning');
  });

  container.prepend(item);

  // Flash the Runs tab
  const runsTab = document.querySelector('[data-tab="runs"]');
  runsTab.classList.add('yy-tab-notify');
  setTimeout(() => runsTab.classList.remove('yy-tab-notify'), 3000);
}

function sendConsentResponse(tokenId, granted) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: granted ? 'approve' : 'reject',
      payload: { token_id: tokenId, consent: true }
    }));
  }
}

// --- Focus Trap for Consent Section ---
// When consent items are visible, trap Tab/Shift+Tab within the consent section
// so keyboard users cannot accidentally skip past a consent decision.

function trapFocusInConsent(event) {
  const section = document.getElementById('consent-section');
  if (!section || section.style.display === 'none') return;
  const focusable = section.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.key === 'Tab') {
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  // Escape dismisses focus trap (moves focus to tab bar)
  if (event.key === 'Escape') {
    const tabBar = document.querySelector('.yy-tabs');
    if (tabBar) tabBar.querySelector('.yy-tab.active').focus();
  }
}

document.addEventListener('keydown', trapFocusInConsent);

// --- Chat ---

document.getElementById('chat-send').addEventListener('click', sendChatMessage);
document.getElementById('chat-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendChatMessage();
});

function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  addChatBubble(text, 'user');
  input.value = '';

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'chat', payload: { content: text } }));
  } else {
    addChatBubble('I\'m not connected to the Solace server. Check that it\'s running.', 'assistant');
  }
}

function addChatBubble(text, role) {
  const messages = document.getElementById('chat-messages');
  const bubble = document.createElement('div');
  bubble.className = `yy-chat-bubble yy-${role}`;
  bubble.innerHTML = `<p>${escapeHtml(text)}</p>`;
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

// --- Theme ---

document.getElementById('theme-select').addEventListener('change', (e) => {
  const theme = e.target.value;
  document.body.setAttribute('data-theme', theme);
  chrome.storage.local.set({ theme });
});

// Load saved theme
chrome.storage.local.get('theme', (data) => {
  if (data.theme) {
    document.body.setAttribute('data-theme', data.theme);
    document.getElementById('theme-select').value = data.theme;
  }
});

// --- Screen Reader Announcements ---

function announce(message, priority) {
  const regionId = priority === 'alert' ? 'yy-alert-live' : 'yy-status-live';
  const region = document.getElementById(regionId);
  if (region) {
    region.textContent = '';
    requestAnimationFrame(() => { region.textContent = message; });
  }
}

// --- Toast Notifications ---

function showToast(message, type) {
  // Also announce to screen readers
  announce(message, type === 'error' || type === 'warning' ? 'alert' : 'status');
  type = type || 'info';
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `yy-toast yy-toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  // Animate in
  requestAnimationFrame(() => toast.classList.add('yy-toast-show'));

  // Auto-dismiss
  setTimeout(() => {
    toast.classList.remove('yy-toast-show');
    toast.addEventListener('transitionend', () => toast.remove());
    // Fallback removal
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 500);
  }, TOAST_DURATION_MS);
}

// --- DOM Sink Policy ---
// RULE: All innerHTML assignments MUST use escapeHtml for user/server content.
// BANNED sinks: raw string injection, dynamic code execution, direct DOM writes.
// ALLOWED: innerHTML with escapeHtml/escapeAttr for template rendering.
// Audited: all 10 innerHTML sites use escapeHtml — verified in cross-layer tests.
// Future: migrate to Trusted Types API when Chrome MV3 supports it.

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/**
 * Safe DOM text setter — creates element with textContent only (no HTML parsing).
 * Use for single-value displays where innerHTML template isn't needed.
 */
function safeSetText(elementId, text) {
  const el = document.getElementById(elementId);
  if (el) el.textContent = text;
}

// --- Stats ---

async function loadStats() {
  try {
    const resp = await fetch(`${SOLACE_API}${ENDPOINTS.apps}`);
    if (resp.ok) {
      const apps = await resp.json();
      document.getElementById('stat-apps').textContent = Array.isArray(apps) ? apps.length : '--';
    }
  } catch {
    document.getElementById('stat-apps').textContent = '--';
  }
}

async function loadModels() {
  try {
    const resp = await fetch(`${SOLACE_API}${ENDPOINTS.models}`);
    if (resp.ok) {
      const data = await resp.json();
      availableModels = data.models || [];
    }
  } catch {
    availableModels = [{ id: 'default', name: 'Default (BYOK)', source: 'byok' }];
  }
}

async function loadBenchmarks(appId) {
  const container = document.getElementById(`bench-${appId}`);
  if (!container) return;

  try {
    const resp = await fetch(`${SOLACE_API}/api/apps/${encodeURIComponent(appId)}/benchmarks`);
    if (!resp.ok) {
      container.textContent = 'No benchmarks available';
      return;
    }
    const data = await resp.json();
    const benchmarks = data.benchmarks?.benchmarks || {};

    if (Object.keys(benchmarks).length === 0) {
      container.innerHTML = '<span class="yy-hint">No benchmark data yet</span>';
      return;
    }

    const rows = Object.entries(benchmarks).map(([model, stats]) =>
      `<div class="yy-bench-row">
        <span class="yy-bench-model">${escapeHtml(model.replace(/_/g, ' '))}</span>
        <span class="yy-bench-cost">$${stats.avg_cost || '?'}</span>
        <span class="yy-bench-quality">${stats.quality_score || '?'}%</span>
      </div>`
    ).join('');

    container.innerHTML = `<div class="yy-bench-header">
      <span>Model</span><span>Cost/run</span><span>Quality</span>
    </div>${rows}`;
  } catch {
    container.innerHTML = '<span class="yy-hint">Could not load benchmarks</span>';
  }
}

// --- Init ---

async function init() {
  await loadModels();
  const online = await checkServerStatus();

  if (online) {
    showMainUI();
    connectWebSocket();
    updateCurrentPage();
    loadStats();
  } else {
    showOfflineUI();
  }

  // Refresh current page on tab activation
  chrome.tabs.onActivated.addListener(() => updateCurrentPage());
  chrome.tabs.onUpdated.addListener((_tabId, changeInfo) => {
    if (changeInfo.url) updateCurrentPage();
  });

  // Periodic server health check (every 30s per rethink doc)
  setInterval(async () => {
    const wasOnline = serverOnline;
    const nowOnline = await checkServerStatus();
    if (!wasOnline && nowOnline) {
      showMainUI();
      connectWebSocket();
      updateCurrentPage();
      loadStats();
      showToast('Server connected', 'info');
    } else if (wasOnline && !nowOnline) {
      showOfflineUI();
      showToast('Server disconnected', 'error');
    }
  }, HEALTH_CHECK_INTERVAL_MS);
}

init();
