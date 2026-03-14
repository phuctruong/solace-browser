// Diagram: 02-dashboard-login
'use strict';

const SI_API = '/api/v1/storage';

function getToken() {
  return localStorage.getItem('solace_token') || '';
}

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

function setStatus(msg) {
  const el = document.getElementById('si-status');
  if (el) el.textContent = msg;
}

function renderSummary(summary) {
  const container = document.getElementById('si-summary');
  if (!container) return;
  const entries = Object.entries(summary || {});
  if (entries.length === 0) {
    container.innerHTML = '<p class="si-empty">No storage data.</p>';
    return;
  }
  container.innerHTML = entries.map(([type, stats]) => `
    <div class="si-type-row">
      <span class="si-type-name">${type}</span>
      <div class="si-type-stats">
        <span>Events: ${stats.event_count}</span>
        <span>Size: ${stats.total_size_bytes} bytes</span>
      </div>
    </div>
  `).join('');
}

async function loadSummary() {
  const res = await fetch(SI_API + '/summary');
  const data = await res.json();
  renderSummary(data.summary || {});
}

document.getElementById('btn-si-summary').addEventListener('click', loadSummary);

document.getElementById('btn-si-by-domain').addEventListener('click', async () => {
  const res = await fetch(SI_API + '/by-domain');
  const data = await res.json();
  setStatus('Domains: ' + data.total_domains);
});

document.getElementById('btn-si-clear').addEventListener('click', async () => {
  if (!confirm('Clear all storage events?')) return;
  const res = await fetch(SI_API + '/clear', { method: 'DELETE', headers: authHeaders() });
  const data = await res.json();
  if (data.status === 'cleared') {
    setStatus('Cleared ' + data.removed + ' events.');
    await loadSummary();
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
});

loadSummary();
