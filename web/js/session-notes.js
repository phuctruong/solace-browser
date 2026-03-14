// Diagram: 02-dashboard-login
'use strict';

const SN_API = '/api/v1/notes';

function getToken() {
  return localStorage.getItem('solace_token') || '';
}

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

function setStatus(msg) {
  const el = document.getElementById('sn-status');
  if (el) el.textContent = msg;
}

function renderNotes(notes) {
  const list = document.getElementById('sn-list');
  if (!list) return;
  if (!notes || notes.length === 0) {
    list.innerHTML = '<p class="sn-empty">No notes yet.</p>';
    return;
  }
  list.innerHTML = notes.map(n => `
    <div class="sn-note" data-id="${n.note_id}">
      <div class="sn-note-header">
        <span class="sn-note-title">${n.title}</span>
        <button class="sn-btn sn-btn-danger sn-btn-delete" data-id="${n.note_id}">Delete</button>
      </div>
      <div class="sn-note-body">${n.body}</div>
      ${n.tags.length ? '<div class="sn-note-tags">' + n.tags.map(t => `<span class="sn-tag">${t}</span>`).join('') + '</div>' : ''}
      <div class="sn-note-date">${n.created_at}</div>
    </div>
  `).join('');

  list.querySelectorAll('.sn-btn-delete').forEach(btn => {
    btn.addEventListener('click', () => deleteNote(btn.dataset.id));
  });
}

async function loadNotes() {
  const res = await fetch(SN_API);
  const data = await res.json();
  renderNotes(data.notes || []);
}

async function searchNotes(q) {
  if (!q) { return loadNotes(); }
  const res = await fetch(SN_API + '/search?q=' + encodeURIComponent(q));
  const data = await res.json();
  renderNotes(data.notes || []);
  setStatus('Found: ' + data.total);
}

async function deleteNote(noteId) {
  if (!confirm('Delete this note?')) return;
  const res = await fetch(SN_API + '/' + noteId, { method: 'DELETE', headers: authHeaders() });
  const data = await res.json();
  if (data.status === 'deleted') {
    setStatus('Note deleted.');
    await loadNotes();
  }
}

document.getElementById('btn-sn-add').addEventListener('click', async () => {
  const title = prompt('Note title:');
  if (!title) return;
  const body = prompt('Note body (max 20000 chars):') || '';
  const tagsInput = prompt('Tags (comma-separated, max 10):') || '';
  const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(Boolean) : [];

  const res = await fetch(SN_API, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ title, body, tags }),
  });
  const data = await res.json();
  if (data.status === 'added') {
    setStatus('Note added: ' + data.note_id);
    await loadNotes();
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
});

let searchTimeout;
document.getElementById('sn-search').addEventListener('input', e => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => searchNotes(e.target.value.trim()), 300);
});

loadNotes();
