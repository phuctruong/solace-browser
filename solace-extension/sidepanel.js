/**
 * Yinyang Side Panel — Main logic
 * Handles tabs, WebSocket connection, app display, and chat.
 */

const SOLACE_API = 'http://localhost:9222';
let availableModels = [];
let selectedModels = {}; // app_id -> model_id
let ws = null;
let reconnectTimer = null;

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

// --- WebSocket Connection ---

function connectWebSocket() {
  const wsUrl = SOLACE_API.replace('http', 'ws') + '/ws/yinyang';
  setConnectionStatus('connecting');

  try {
    ws = new WebSocket(wsUrl);
  } catch (err) {
    setConnectionStatus('disconnected');
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    setConnectionStatus('connected');
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
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
  if (!reconnectTimer) {
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectWebSocket();
    }, 5000);
  }
}

function setConnectionStatus(state) {
  const dot = document.querySelector('.yy-dot');
  dot.className = 'yy-dot';
  if (state === 'connected') dot.classList.add('connected');
  if (state === 'connecting') dot.classList.add('connecting');
}

function handleWsMessage(msg) {
  if (msg.type === 'chat') {
    const content = msg.payload && msg.payload.content ? msg.payload.content : '';
    if (content) {
      addChatBubble(content, msg.payload.role || 'assistant');
    }
  } else if (msg.type === 'run_update') {
    updateRunsList(msg.data);
  } else if (msg.type === 'approval_request') {
    addApprovalRequest(msg.data);
  }
}

// --- API Health Check (fallback when WS unavailable) ---

async function checkApiHealth() {
  try {
    const resp = await fetch(`${SOLACE_API}/api/health`);
    if (resp.ok) {
      setConnectionStatus('connected');
      const data = await resp.json();
      document.getElementById('stat-api').textContent = 'Connected';
      return true;
    }
  } catch {
    // API not reachable
  }
  setConnectionStatus('disconnected');
  document.getElementById('stat-api').textContent = 'Offline';
  return false;
}

// --- App Detection ---

async function updateCurrentPage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  const urlEl = document.getElementById('page-url');
  try {
    const url = new URL(tab.url);
    urlEl.textContent = url.hostname + url.pathname;
  } catch {
    urlEl.textContent = tab.url || '—';
  }

  // Ask service worker for matched apps
  chrome.runtime.sendMessage(
    { type: 'GET_MATCHED_APPS', tabId: tab.id },
    (response) => {
      if (response && response.apps && response.apps.length > 0) {
        loadMatchedApps(response.apps);
      }
    }
  );
}

async function loadMatchedApps(appIds) {
  try {
    const resp = await fetch(`${SOLACE_API}/api/apps`);
    if (!resp.ok) return;
    const allApps = await resp.json();
    const matched = allApps.filter(a => appIds.includes(a.id));
    renderAppCards(matched);
  } catch {
    // API offline — show empty state
  }
}

function renderAppCards(apps) {
  const container = document.getElementById('matched-apps');
  if (apps.length === 0) {
    container.innerHTML = `
      <div class="yy-empty-state">
        <p>No apps match this page</p>
        <p class="yy-hint">Navigate to a supported site to see available automations</p>
      </div>`;
    return;
  }

  container.innerHTML = apps.map(app => `
    <div class="yy-app-card" data-app-id="${app.id}">
      <div class="yy-app-name">${escapeHtml(app.name)}</div>
      <div class="yy-app-desc">${escapeHtml(app.description || '')}</div>
      <div class="yy-model-picker">
        <label class="yy-picker-label">Model:</label>
        <select class="yy-model-select" data-app="${app.id}" aria-label="Select model for ${escapeHtml(app.name)}">
          ${availableModels.map(m => `<option value="${m.id}" ${m.uplift ? 'class="yy-uplift"' : ''}>${escapeHtml(m.name)}</option>`).join('')}
        </select>
      </div>
      <div class="yy-benchmark-row" id="bench-${app.id}"></div>
      <div class="yy-app-actions">
        <button class="yy-btn yy-btn-primary" data-action="run" data-app="${app.id}">Run Now</button>
        <button class="yy-btn yy-btn-secondary" data-action="benchmark" data-app="${app.id}">Benchmarks</button>
      </div>
    </div>
  `).join('');

  // Wire up buttons
  container.querySelectorAll('[data-action="run"]').forEach(btn => {
    btn.addEventListener('click', () => runApp(btn.dataset.app));
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

// --- Run / Schedule ---

async function runApp(appId) {
  try {
    const resp = await fetch(`${SOLACE_API}/api/apps/${appId}/run`, { method: 'POST' });
    if (resp.ok) {
      showToast(`Started: ${appId}`);
      // Switch to Runs tab
      document.querySelector('[data-tab="runs"]').click();
    } else {
      showToast(`Failed to start ${appId}`, 'error');
    }
  } catch {
    showToast('API offline', 'error');
  }
}

async function scheduleApp(appId) {
  showToast(`Schedule: ${appId} (coming soon)`);
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
      <span class="yy-list-item-icon">${run.status === 'success' ? '✓' : '⟳'}</span>
      <div class="yy-list-item-content">
        <div class="yy-list-item-title">${escapeHtml(run.app_id)}</div>
        <div class="yy-list-item-sub">${run.status} — ${run.duration || '—'}</div>
      </div>
    </div>
  `).join('');
}

function addApprovalRequest(approval) {
  const container = document.getElementById('approval-queue');
  const emptyState = container.querySelector('.yy-empty-state');
  if (emptyState) emptyState.remove();

  const item = document.createElement('div');
  item.className = 'yy-list-item';
  item.innerHTML = `
    <span class="yy-list-item-icon">⚠</span>
    <div class="yy-list-item-content">
      <div class="yy-list-item-title">${escapeHtml(approval.action)}</div>
      <div class="yy-list-item-sub">${escapeHtml(approval.description || '')}</div>
    </div>
    <div class="yy-app-actions">
      <button class="yy-btn yy-btn-primary yy-btn-sm" data-approve="${approval.id}">Approve</button>
      <button class="yy-btn yy-btn-secondary yy-btn-sm" data-reject="${approval.id}">Reject</button>
    </div>
  `;
  container.prepend(item);
}

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

  // Send via WebSocket if connected
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'chat', payload: { content: text } }));
  } else {
    addChatBubble('I\'m not connected to the Solace API. Check that the browser server is running.', 'assistant');
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

// --- Utils ---

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function showToast(message, type = 'info') {
  // Simple toast — will upgrade later
  console.log(`[Yinyang Toast] ${type}: ${message}`);
}

// --- Stats ---

async function loadStats() {
  try {
    const resp = await fetch(`${SOLACE_API}/api/apps`);
    if (resp.ok) {
      const apps = await resp.json();
      document.getElementById('stat-apps').textContent = apps.length;
    }
  } catch {
    document.getElementById('stat-apps').textContent = '—';
  }
}

async function loadModels() {
  try {
    const resp = await fetch(`${SOLACE_API}/api/models`);
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
    const resp = await fetch(`${SOLACE_API}/api/apps/${appId}/benchmarks`);
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
  await checkApiHealth();
  connectWebSocket();
  updateCurrentPage();
  loadStats();

  // Refresh current page on tab activation
  chrome.tabs.onActivated.addListener(() => updateCurrentPage());
  chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url) updateCurrentPage();
  });
}

init();
