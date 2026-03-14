// Diagram: 02-dashboard-login
'use strict';

const TC_API = '/api/v1/theme/customizer';

function getToken() {
  return localStorage.getItem('solace_token') || '';
}

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

function setStatus(msg) {
  const el = document.getElementById('tc-status');
  if (el) el.textContent = msg;
}

function renderPresets(presets) {
  const container = document.getElementById('tc-presets');
  if (!container) return;
  container.innerHTML = presets.map(p => `
    <div class="tc-preset" data-id="${p.preset_id}">
      <div class="tc-preset-name">${p.name}</div>
      <div class="tc-preset-meta">${p.font_size}${p.is_default ? ' — default' : ''}</div>
    </div>
  `).join('');

  container.querySelectorAll('.tc-preset').forEach(el => {
    el.addEventListener('click', () => applyPreset(el.dataset.id));
  });
}

async function loadPresets() {
  const res = await fetch(TC_API + '/presets');
  const data = await res.json();
  renderPresets(data.presets || []);
}

async function applyPreset(presetId) {
  const res = await fetch(TC_API + '/preset/' + presetId, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({}),
  });
  const data = await res.json();
  if (data.status === 'applied') {
    setStatus('Preset applied: ' + presetId);
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
}

document.getElementById('btn-tc-apply').addEventListener('click', async () => {
  const accentEl = document.getElementById('tc-accent');
  const fontSizeEl = document.getElementById('tc-font-size');
  const payload = {};
  if (accentEl) payload.accent_color = accentEl.value;
  if (fontSizeEl) payload.font_size = fontSizeEl.value;

  const res = await fetch(TC_API, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (data.status === 'updated') {
    setStatus('Theme updated.');
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
});

document.getElementById('btn-tc-reset').addEventListener('click', async () => {
  if (!confirm('Reset theme to default?')) return;
  const res = await fetch(TC_API, { method: 'DELETE', headers: authHeaders() });
  const data = await res.json();
  if (data.status === 'reset') {
    setStatus('Theme reset to default.');
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
});

loadPresets();
