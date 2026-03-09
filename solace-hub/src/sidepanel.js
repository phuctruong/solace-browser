const API_BASE = 'http://localhost:8888';
const TIERS = ['free', 'starter', 'pro', 'team', 'enterprise'];
const UPGRADE_URL = 'https://solaceagi.com/upgrade';

let userTierState = { tier: 'free', can_sync: false, can_submit: false };

window.switchTab = function switchTab(tabName) {
  document.querySelectorAll('.yy-tab').forEach((tab) => tab.classList.remove('active'));
  document.querySelectorAll('.yy-panel').forEach((panel) => {
    panel.classList.remove('active');
    panel.setAttribute('aria-hidden', 'true');
  });

  const tab = document.getElementById(`tab-${tabName}`);
  const panel = document.getElementById(`panel-${tabName}`);
  if (tab) {
    tab.classList.add('active');
  }
  if (panel) {
    panel.classList.add('active');
    panel.removeAttribute('aria-hidden');
  }
};

function getAuthHeaders() {
  const token = window.SOLACE_SESSION_TOKEN_SHA256 || window.SOLACE_SESSION_TOKEN || '';
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function getCurrentDomain() {
  if (window.SOLACE_CURRENT_DOMAIN && typeof window.SOLACE_CURRENT_DOMAIN === 'string') {
    return window.SOLACE_CURRENT_DOMAIN;
  }
  if (document.body.dataset.currentDomain) {
    return document.body.dataset.currentDomain;
  }
  return window.location.hostname || '';
}

function userCanInstall(tier) {
  return TIERS.indexOf(userTierState.tier || 'free') >= TIERS.indexOf(tier || 'free');
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

async function apiRequest(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...getAuthHeaders(),
  };
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const payload = await response.json();
  if (!response.ok) {
    throw payload;
  }
  return payload;
}

async function loadUserTier() {
  try {
    userTierState = await apiRequest('/api/v1/user/tier');
  } catch (_error) {
    userTierState = { tier: 'free', can_sync: false, can_submit: false };
  }

  const submitButton = document.getElementById('submit-to-store-btn');
  if (!submitButton) {
    return;
  }
  submitButton.disabled = !userTierState.can_submit;
  submitButton.title = userTierState.can_submit ? 'Submit custom apps to the store' : 'Pro tier required';
}

function renderDomainApps(response) {
  const list = document.getElementById('domain-apps-list');
  const badge = document.getElementById('domain-apps-count');
  if (!list || !badge) {
    return;
  }

  const apps = Array.isArray(response.apps) ? response.apps : [];
  badge.textContent = String(response.total || apps.length || 0);

  if (apps.length === 0) {
    list.innerHTML = '<p class="yy-empty">No matching apps yet.</p>';
    return;
  }

  list.innerHTML = apps.map((app) => {
    const installLabel = app.installed ? 'Installed ✓' : 'Install';
    const disabled = app.installed ? 'disabled' : '';
    const gated = !userCanInstall(app.tier_required) ? 'data-upgrade-required="true"' : '';
    return `
      <div class="app-card" data-app-id="${escapeHtml(app.app_id)}">
        <div class="app-info">
          <div>
            <span class="app-name">${escapeHtml(app.display_name)}</span>
            <span class="app-tier">${escapeHtml(app.tier_required)}</span>
          </div>
        </div>
        <button class="btn-install" type="button" data-app="${escapeHtml(app.app_id)}" ${disabled} ${gated}>${installLabel}</button>
      </div>
    `;
  }).join('');

  list.querySelectorAll('.btn-install').forEach((button) => {
    button.addEventListener('click', handleInstallClick);
  });
}

async function loadDomainApps() {
  const domain = getCurrentDomain();
  const domainLabel = document.getElementById('current-domain-label');
  if (domainLabel) {
    domainLabel.textContent = domain || 'No domain available';
  }
  if (!domain) {
    renderDomainApps({ total: 0, apps: [] });
    return;
  }
  const response = await apiRequest(`/api/v1/apps/by-domain?domain=${encodeURIComponent(domain)}`);
  renderDomainApps(response);
}

async function handleInstallClick(event) {
  const button = event.currentTarget;
  const appId = button.dataset.app || '';
  if (!appId) {
    return;
  }
  if (button.dataset.upgradeRequired === 'true') {
    window.open(UPGRADE_URL, '_blank', 'noopener');
    return;
  }
  button.disabled = true;
  try {
    await apiRequest('/api/v1/apps/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id: appId }),
    });
    button.textContent = 'Installed ✓';
  } catch (_error) {
    button.disabled = false;
  }
}

async function createCustomApp() {
  const domain = getCurrentDomain();
  const name = window.prompt(`App name for ${domain}?`);
  if (!name) {
    return;
  }
  const description = `Custom app for ${domain}`;
  const response = await apiRequest('/api/v1/apps/custom/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain, name, description }),
  });
  window.alert(`Custom app created! Edit ${response.session_rules_path} to configure.`);
  await loadDomainApps();
}

async function submitToStore() {
  if (!userTierState.can_submit) {
    window.open(UPGRADE_URL, '_blank', 'noopener');
    return;
  }
  const response = await apiRequest('/api/v1/apps/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  window.alert(`Synced ${response.total || 0} custom apps for store submission.`);
}

document.addEventListener('DOMContentLoaded', async () => {
  const createButton = document.getElementById('create-custom-app-btn');
  const submitButton = document.getElementById('submit-to-store-btn');

  if (createButton) {
    createButton.addEventListener('click', () => {
      createCustomApp().catch(() => {});
    });
  }
  if (submitButton) {
    submitButton.addEventListener('click', () => {
      submitToStore().catch(() => {});
    });
  }

  await loadUserTier();
  await loadDomainApps();
});
