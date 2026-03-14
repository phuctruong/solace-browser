// Diagram: 02-dashboard-login
'use strict';

const API = '/api/v1/vault';

function getToken() {
  return localStorage.getItem('solace_token') || '';
}

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

function setStatus(msg) {
  const el = document.getElementById('pv-status');
  if (el) el.textContent = msg;
}

async function loadEntries() {
  const res = await fetch(API + '/entries', { headers: authHeaders() });
  const data = await res.json();
  const list = document.getElementById('pv-list');
  if (!list) return;
  if (!data.entries || data.entries.length === 0) {
    list.innerHTML = '<p class="pv-empty">No vault entries yet.</p>';
    return;
  }
  list.innerHTML = data.entries.map(e => `
    <div class="pv-entry" data-id="${e.entry_id}">
      <span class="pv-entry-title">${e.title}</span>
      <span class="pv-entry-category pv-cat-${e.category}">${e.category}</span>
      <span class="pv-entry-user">${e.username || ''}</span>
      <button class="pv-btn pv-btn-copy" data-id="${e.entry_id}">Copy (${e.copy_count})</button>
      <button class="pv-btn pv-btn-danger pv-btn-delete" data-id="${e.entry_id}">Delete</button>
    </div>
  `).join('');

  list.querySelectorAll('.pv-btn-copy').forEach(btn => {
    btn.addEventListener('click', () => copyEntry(btn.dataset.id));
  });
  list.querySelectorAll('.pv-btn-delete').forEach(btn => {
    btn.addEventListener('click', () => deleteEntry(btn.dataset.id));
  });
}

async function loadStats() {
  const res = await fetch(API + '/stats', { headers: authHeaders() });
  const data = await res.json();
  const el = document.getElementById('pv-stats');
  if (!el) return;
  el.textContent = `Total: ${data.total} | Copies: ${data.total_copies}`;
}

async function copyEntry(entryId) {
  const res = await fetch(API + '/entries/' + entryId + '/copy', {
    method: 'POST',
    headers: authHeaders(),
  });
  const data = await res.json();
  if (data.status === 'copied') {
    setStatus('Copied! Count: ' + data.copy_count);
    await loadEntries();
  }
}

async function deleteEntry(entryId) {
  if (!confirm('Delete this vault entry?')) return;
  const res = await fetch(API + '/entries/' + entryId, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  const data = await res.json();
  if (data.status === 'deleted') {
    setStatus('Entry deleted.');
    await loadEntries();
    await loadStats();
  }
}

document.getElementById('btn-add-entry').addEventListener('click', async () => {
  const title = prompt('Title:');
  if (!title) return;
  const category = prompt('Category (login/api-key/wifi/bank/note/other):', 'login');
  const username = prompt('Username:') || '';
  const password = prompt('Password:') || '';
  const domain = prompt('Domain (e.g. example.com):') || '';

  const res = await fetch(API + '/entries', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ title, category, username, password, domain }),
  });
  const data = await res.json();
  if (data.status === 'added') {
    setStatus('Entry added: ' + data.entry_id);
    await loadEntries();
    await loadStats();
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
});

loadEntries();
loadStats();
