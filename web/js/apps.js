'use strict';

const TOKEN = localStorage.getItem('solace_token') || '';
const APP_STATE_KEY = (appId) => `app:${appId}:state`;
const STATE_CLASSES = ['app-state--installed', 'app-state--setup', 'app-state--activated', 'app-state--running'];

let currentSetupAppId = null;
let currentApps = [];

function apiFetch(path, options = {}) {
  return fetch(path, {
    ...options,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
}

function statusLabelForState(state) {
  const statusMap = {
    installed: 'Needs setup',
    setup: 'Setting up...',
    activated: 'Ready',
    running: 'Running',
  };
  return statusMap[state] || state;
}

function saveAppState(appId, state) {
  localStorage.setItem(APP_STATE_KEY(appId), state);
  updateAppCardVisual(appId, state);
  updateSetupBanner(currentApps);
}

function applyStateClass(card, state) {
  STATE_CLASSES.forEach((className) => card.classList.remove(className));
  card.classList.add(`app-state--${state}`);
}

function updateAppCardVisual(appId, state) {
  const card = document.querySelector(`[data-app-id="${appId}"]`);
  if (!card) {
    return;
  }

  applyStateClass(card, state);

  const statusElement = card.querySelector('.app-card__status');
  if (statusElement) {
    statusElement.textContent = statusLabelForState(state);
  }

  const setupButton = card.querySelector('.app-card__setup-btn');
  const runButton = card.querySelector('.app-card__run-btn');
  const isReady = state === 'activated' || state === 'running';

  if (setupButton) {
    setupButton.hidden = isReady;
  }
  if (runButton) {
    runButton.hidden = !isReady;
  }
}

function renderEmptyState() {
  const grid = document.getElementById('apps-grid');
  grid.innerHTML = '<p class="apps-empty-state">No apps installed.</p>';
}

function renderAppsGrid(apps) {
  const grid = document.getElementById('apps-grid');
  if (!apps.length) {
    renderEmptyState();
    return;
  }

  grid.innerHTML = apps.map((app) => {
    const state = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
    const isReady = state === 'activated' || state === 'running';
    return `
      <div class="app-card app-state--${state}" data-app-id="${app.app_id}">
        <span class="app-card__icon">${app.icon || '📦'}</span>
        <div class="app-card__name">${app.name}</div>
        <div class="app-card__status">${statusLabelForState(state)}</div>
        <button class="app-card__setup-btn" data-action="setup" data-app-id="${app.app_id}" data-app-name="${app.name}"${isReady ? ' hidden' : ''}>Set up</button>
        <button class="app-card__run-btn" data-action="run" data-app-id="${app.app_id}" data-app-name="${app.name}"${isReady ? '' : ' hidden'}>Run</button>
      </div>
    `;
  }).join('');
}

function updateSetupBanner(apps) {
  const pendingApps = apps.filter((app) => {
    const state = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
    return state === 'installed' || state === 'setup';
  });

  const banner = document.getElementById('setup-banner');
  banner.hidden = pendingApps.length === 0;
  document.getElementById('setup-count').textContent = String(pendingApps.length);
}

function renderSetupMessage(message, modifier = '') {
  return `<p class="setup-form__message${modifier ? ` setup-form__message--${modifier}` : ''}">${message}</p>`;
}

function renderSetupFields(fields) {
  if (!fields.length) {
    return renderSetupMessage('No configuration needed for this app.');
  }

  return fields.map((field) => `
    <div class="setup-form__field">
      <label for="field-${field.name}">${field.description || field.name}${field.required ? ' *' : ''}</label>
      <input id="field-${field.name}" name="${field.name}" type="${field.type === 'oauth' ? 'password' : 'text'}" placeholder="${field.placeholder || ''}"${field.required ? ' required' : ''}>
    </div>
  `).join('');
}

function closeSetupDrawer() {
  document.getElementById('setup-drawer').hidden = true;
}

function openSetupDrawer(appId, appName) {
  currentSetupAppId = appId;
  document.getElementById('setup-drawer-title').textContent = `Set up ${appName}`;
  document.getElementById('setup-drawer').hidden = false;
  saveAppState(appId, 'setup');

  apiFetch(`/api/v1/apps/${appId}/setup-requirements`)
    .then((response) => response.json())
    .then((data) => {
      const form = document.getElementById('setup-form');
      const fields = Array.isArray(data.fields) ? data.fields : [];
      form.innerHTML = renderSetupFields(fields);
    })
    .catch(() => {
      document.getElementById('setup-form').innerHTML = renderSetupMessage('Could not load setup requirements.', 'error');
    });
}

function applyServerState(data, appId, fallbackState) {
  const localStorageUpdate = data.local_storage || {
    key: APP_STATE_KEY(appId),
    value: fallbackState,
  };
  localStorage.setItem(localStorageUpdate.key, localStorageUpdate.value);
  updateAppCardVisual(appId, localStorageUpdate.value);
  updateSetupBanner(currentApps);
}

function loadAppStates() {
  apiFetch('/api/v1/apps/lifecycle')
    .then((response) => response.json())
    .then((data) => {
      currentApps = Array.isArray(data.apps) ? data.apps : [];
      renderAppsGrid(currentApps);
      currentApps.forEach((app) => {
        const state = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
        saveAppState(app.app_id, state);
      });
      updateSetupBanner(currentApps);
    })
    .catch(() => {
      currentApps = [];
      renderEmptyState();
      updateSetupBanner(currentApps);
    });
}

function runApp(appId) {
  saveAppState(appId, 'running');
}

document.getElementById('apps-grid').addEventListener('click', (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button) {
    return;
  }

  const appId = button.dataset.appId || '';
  const appName = button.dataset.appName || appId;
  if (button.dataset.action === 'setup') {
    openSetupDrawer(appId, appName);
    return;
  }
  if (button.dataset.action === 'run') {
    runApp(appId);
  }
});

document.getElementById('setup-all-btn').addEventListener('click', () => {
  const firstPendingApp = currentApps.find((app) => {
    const state = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
    return state === 'installed' || state === 'setup';
  });
  if (firstPendingApp) {
    openSetupDrawer(firstPendingApp.app_id, firstPendingApp.name);
  }
});

document.getElementById('setup-drawer-close').addEventListener('click', closeSetupDrawer);
document.getElementById('cancel-setup-btn').addEventListener('click', closeSetupDrawer);

document.getElementById('setup-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (!currentSetupAppId) {
    return;
  }

  const formData = new FormData(event.target);
  const config = {};
  formData.forEach((value, key) => {
    config[key] = value;
  });

  apiFetch(`/api/v1/apps/${currentSetupAppId}/activate`, {
    method: 'POST',
    body: JSON.stringify({ config }),
  })
    .then(async (response) => ({ ok: response.ok, data: await response.json() }))
    .then(({ ok, data }) => {
      if (!ok) {
        document.getElementById('setup-form').insertAdjacentHTML(
          'afterbegin',
          renderSetupMessage(data.error || 'Activation failed.', 'error'),
        );
        return;
      }
      applyServerState(data, currentSetupAppId, 'activated');
      closeSetupDrawer();
      loadAppStates();
    })
    .catch(() => {
      document.getElementById('setup-form').insertAdjacentHTML(
        'afterbegin',
        renderSetupMessage('Activation failed.', 'error'),
      );
    });
});

loadAppStates();
