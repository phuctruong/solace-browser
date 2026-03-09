'use strict';

const NI_API = '/api/v1/network';

function getToken() {
  return localStorage.getItem('solace_token') || '';
}

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

function setStatus(msg) {
  const el = document.getElementById('ni-status');
  if (el) el.textContent = msg;
}

async function loadRequests() {
  const res = await fetch(NI_API + '/requests', { headers: authHeaders() });
  const data = await res.json();
  renderRequests(data.requests || []);
}

function renderRequests(requests) {
  const list = document.getElementById('ni-list');
  if (!list) return;
  if (requests.length === 0) {
    list.innerHTML = '<p class="ni-empty">No requests captured yet.</p>';
    return;
  }
  list.innerHTML = requests.map(r => `
    <div class="ni-request${r.blocked ? ' ni-blocked' : ''}">
      <span class="ni-method ni-method-${r.method.toLowerCase()}">${r.method}</span>
      <span class="ni-hash" title="${r.url_hash}">${r.url_hash.slice(0, 12)}...</span>
      <span class="ni-status-code">${r.status_code !== null ? r.status_code : '—'}</span>
      <span class="ni-duration">${r.duration_ms !== null ? r.duration_ms + 'ms' : '—'}</span>
      <span class="ni-type">${r.request_type}</span>
      ${r.blocked ? '<span class="ni-badge-blocked">BLOCKED</span>' : ''}
    </div>
  `).join('');
}

async function loadStats() {
  const res = await fetch(NI_API + '/stats');
  const data = await res.json();
  const panel = document.getElementById('ni-stats-panel');
  if (!panel) return;
  panel.hidden = false;
  panel.innerHTML = `<strong>Stats:</strong> Total: ${data.total} | Blocked: ${data.blocked}`;
}

async function loadBlocked() {
  const res = await fetch(NI_API + '/blocked');
  const data = await res.json();
  renderRequests(data.requests || []);
  setStatus('Showing blocked requests: ' + data.total);
}

async function clearAll() {
  if (!confirm('Clear all captured requests?')) return;
  const res = await fetch(NI_API + '/requests', { method: 'DELETE', headers: authHeaders() });
  const data = await res.json();
  if (data.status === 'cleared') {
    setStatus('Cleared ' + data.removed + ' requests.');
    await loadRequests();
  }
}

document.getElementById('btn-ni-refresh').addEventListener('click', loadRequests);
document.getElementById('btn-ni-stats').addEventListener('click', loadStats);
document.getElementById('btn-ni-blocked').addEventListener('click', loadBlocked);
document.getElementById('btn-ni-clear').addEventListener('click', clearAll);

loadRequests();
