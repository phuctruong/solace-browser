// Diagram: 02-dashboard-login
'use strict';

const PS_API = '/api/v1/screenshots';

function getToken() {
  return localStorage.getItem('solace_token') || '';
}

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

function setStatus(msg) {
  const el = document.getElementById('ps-status');
  if (el) el.textContent = msg;
}

function renderScreenshots(screenshots) {
  const list = document.getElementById('ps-list');
  if (!list) return;
  if (!screenshots || screenshots.length === 0) {
    list.innerHTML = '<p class="ps-empty">No screenshots yet.</p>';
    return;
  }
  list.innerHTML = screenshots.map(s => `
    <div class="ps-item" data-id="${s.screenshot_id}">
      <div class="ps-item-header">
        <span class="ps-item-id">${s.screenshot_id}</span>
        <button class="ps-btn ps-btn-danger ps-btn-delete" data-id="${s.screenshot_id}">Delete</button>
      </div>
      <div class="ps-item-meta">
        <span>Format: ${s.format}</span>
        <span>Quality: ${s.quality}</span>
        <span>Size: ${s.width}x${s.height}</span>
        <span>File: ${s.file_size_bytes} bytes</span>
        ${s.title ? '<span>Title: ' + s.title + '</span>' : ''}
      </div>
      <div class="ps-item-date">${s.captured_at}</div>
    </div>
  `).join('');

  list.querySelectorAll('.ps-btn-delete').forEach(btn => {
    btn.addEventListener('click', () => deleteScreenshot(btn.dataset.id));
  });
}

async function loadScreenshots() {
  const res = await fetch(PS_API);
  const data = await res.json();
  renderScreenshots(data.screenshots || []);
}

async function deleteScreenshot(id) {
  if (!confirm('Delete this screenshot?')) return;
  const res = await fetch(PS_API + '/' + id, { method: 'DELETE', headers: authHeaders() });
  const data = await res.json();
  if (data.status === 'deleted') {
    setStatus('Screenshot deleted.');
    await loadScreenshots();
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
}

document.getElementById('btn-ps-capture').addEventListener('click', async () => {
  const url = prompt('URL to screenshot:');
  if (!url) return;
  const format = prompt('Format (png/jpeg/webp):', 'png') || 'png';
  const quality = prompt('Quality (low/medium/high/lossless):', 'medium') || 'medium';

  const res = await fetch(PS_API + '/capture', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ url, format, quality, width: 1280, height: 720 }),
  });
  const data = await res.json();
  if (data.status === 'captured') {
    setStatus('Captured: ' + data.screenshot_id);
    await loadScreenshots();
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
});

document.getElementById('btn-ps-stats').addEventListener('click', async () => {
  const res = await fetch(PS_API + '/stats');
  const data = await res.json();
  setStatus('Total: ' + data.total + ' | Size: ' + data.total_size_bytes + ' bytes');
});

loadScreenshots();
