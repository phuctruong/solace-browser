'use strict';
const TOKEN = localStorage.getItem('solace_token') || '';
const APP_STATE_KEY = (appId) => `app:${appId}:state`;
let _currentSetupAppId = null;

function apiFetch(path, opts = {}) {
  return fetch(path, { headers: { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json', ...opts.headers }, ...opts });
}

function saveAppState(appId, state) {
  localStorage.setItem(APP_STATE_KEY(appId), state);
  updateAppCardVisual(appId, state);
}

function updateAppCardVisual(appId, state) {
  const card = document.querySelector(`[data-app-id="${appId}"]`);
  if (!card) return;
  card.className = card.className.replace(/app-state--\w+/g, '').trim();
  card.classList.add(`app-state--${state}`);
  const statusEl = card.querySelector('.app-card__status');
  const statusMap = { installed: 'Needs setup', setup: 'Setting up...', activated: 'Ready', running: 'Running' };
  if (statusEl) statusEl.textContent = statusMap[state] || state;
  // Swap setup/run button
  const setupBtn = card.querySelector('.app-card__setup-btn');
  const runBtn = card.querySelector('.app-card__run-btn');
  if (state === 'activated' || state === 'running') {
    if (setupBtn) { setupBtn.style.display = 'none'; }
    if (runBtn) { runBtn.style.display = 'block'; }
  } else {
    if (setupBtn) { setupBtn.style.display = 'block'; }
    if (runBtn) { runBtn.style.display = 'none'; }
  }
}

function loadAppStates() {
  apiFetch('/api/v1/apps/lifecycle').then(r => r.json()).then(data => {
    const apps = data.apps || data;
    renderAppsGrid(apps);
    apps.forEach(app => {
      const localState = localStorage.getItem(APP_STATE_KEY(app.app_id));
      const state = localState || app.state;
      saveAppState(app.app_id, state);
    });
    updateSetupBanner(apps);
  }).catch(() => {});
}

function renderAppsGrid(apps) {
  const grid = document.getElementById('apps-grid');
  if (!apps.length) { grid.innerHTML = '<p style="color:var(--hub-text-muted)">No apps installed.</p>'; return; }
  grid.innerHTML = apps.map(app => {
    const localState = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
    const isReady = localState === 'activated' || localState === 'running';
    return `
    <div class="app-card app-state--${localState}" data-app-id="${app.app_id}">
      <span class="app-card__icon">${app.icon || '\u{1F4E6}'}</span>
      <div class="app-card__name">${app.name}</div>
      <div class="app-card__status">${isReady ? 'Ready' : 'Needs setup'}</div>
      ${isReady
        ? `<button class="app-card__run-btn" onclick="runApp('${app.app_id}')">Run</button>`
        : `<button class="app-card__setup-btn" onclick="openSetupDrawer('${app.app_id}', '${app.name}')">Set up</button>`}
    </div>`;
  }).join('');
}

function updateSetupBanner(apps) {
  const needSetup = apps.filter(a => {
    const state = localStorage.getItem(APP_STATE_KEY(a.app_id)) || a.state;
    return state === 'installed' || state === 'setup';
  });
  const banner = document.getElementById('setup-banner');
  banner.hidden = needSetup.length === 0;
  document.getElementById('setup-count').textContent = needSetup.length;
}

function openSetupDrawer(appId, appName) {
  _currentSetupAppId = appId;
  document.getElementById('setup-drawer-title').textContent = `Set up ${appName}`;
  document.getElementById('setup-drawer').hidden = false;
  // Load fields
  apiFetch(`/api/v1/apps/${appId}/setup-requirements`).then(r => r.json()).then(data => {
    const form = document.getElementById('setup-form');
    const fields = data.fields || [];
    form.innerHTML = fields.length
      ? fields.map(f => `
          <div>
            <label for="field-${f.name}">${f.description || f.name}${f.required ? ' *' : ''}</label>
            <input id="field-${f.name}" name="${f.name}" type="${f.type === 'oauth' ? 'password' : 'text'}" placeholder="${f.placeholder || ''}" ${f.required ? 'required' : ''}>
          </div>`).join('')
      : '<p style="color:var(--hub-text-muted)">No configuration needed for this app.</p>';
  }).catch(() => {
    document.getElementById('setup-form').innerHTML = '<p style="color:var(--hub-text-muted)">Could not load setup requirements.</p>';
  });
  saveAppState(appId, 'setup');
}

document.getElementById('setup-drawer-close').addEventListener('click', () => {
  document.getElementById('setup-drawer').hidden = true;
});
document.getElementById('cancel-setup-btn').addEventListener('click', () => {
  document.getElementById('setup-drawer').hidden = true;
});

document.getElementById('setup-form').addEventListener('submit', (e) => {
  e.preventDefault();
  if (!_currentSetupAppId) return;
  const formData = new FormData(e.target);
  const config = {};
  formData.forEach((v, k) => { config[k] = v; });
  apiFetch(`/api/v1/apps/${_currentSetupAppId}/activate`, {
    method: 'POST',
    body: JSON.stringify({ config })
  }).then(r => r.json()).then(data => {
    if (data.activated || data.state === 'activated') {
      saveAppState(_currentSetupAppId, 'activated');
      document.getElementById('setup-drawer').hidden = true;
      loadAppStates();
    }
  }).catch(() => {});
});

function runApp(appId) {
  saveAppState(appId, 'running');
  // In production: POST /api/v1/apps/{app_id}/run
}

// State class map (app-state--installed | app-state--setup | app-state--activated | app-state--running)
const _STATE_CLASSES = ['app-state--installed', 'app-state--setup', 'app-state--activated', 'app-state--running'];

// Init
loadAppStates();
