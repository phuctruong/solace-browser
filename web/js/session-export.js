// Diagram: 02-dashboard-login
'use strict';

const SE_API = '/api/v1/export';

function getToken() {
  return localStorage.getItem('solace_token') || '';
}

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

function setStatus(msg) {
  const el = document.getElementById('se-status');
  if (el) el.textContent = msg;
}

function renderJobs(jobs) {
  const list = document.getElementById('se-list');
  if (!list) return;
  if (!jobs || jobs.length === 0) {
    list.innerHTML = '<p class="se-empty">No export jobs yet.</p>';
    return;
  }
  list.innerHTML = jobs.map(j => `
    <div class="se-job" data-id="${j.job_id}">
      <div class="se-job-header">
        <span class="se-job-id">${j.job_id}</span>
        <button class="se-btn se-btn-danger se-btn-delete" data-id="${j.job_id}">Delete</button>
      </div>
      <div class="se-job-meta">
        <span>Format: ${j.format}</span>
        <span>Scope: ${j.scope}</span>
        <span class="se-job-status">${j.status}</span>
        <span>Rows: ${j.row_count}</span>
        <span>Size: ${j.file_size_bytes} bytes</span>
      </div>
      <div class="se-job-date">${j.created_at}</div>
    </div>
  `).join('');

  list.querySelectorAll('.se-btn-delete').forEach(btn => {
    btn.addEventListener('click', () => deleteJob(btn.dataset.id));
  });
}

async function loadJobs() {
  const res = await fetch(SE_API + '/jobs');
  const data = await res.json();
  renderJobs(data.jobs || []);
}

async function deleteJob(id) {
  if (!confirm('Delete this export job?')) return;
  const res = await fetch(SE_API + '/jobs/' + id, { method: 'DELETE', headers: authHeaders() });
  const data = await res.json();
  if (data.status === 'deleted') {
    setStatus('Job deleted.');
    await loadJobs();
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
}

document.getElementById('btn-se-create').addEventListener('click', async () => {
  const format = prompt('Format (json/csv/html/pdf):', 'json') || 'json';
  const scope = prompt('Scope (history/bookmarks/notes/all):', 'all') || 'all';

  const res = await fetch(SE_API + '/jobs', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ format, scope }),
  });
  const data = await res.json();
  if (data.status === 'created') {
    setStatus('Job created: ' + data.job_id);
    await loadJobs();
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
});

document.getElementById('btn-se-formats').addEventListener('click', async () => {
  const res = await fetch(SE_API + '/formats');
  const data = await res.json();
  setStatus('Formats: ' + (data.formats || []).join(', '));
});

loadJobs();
