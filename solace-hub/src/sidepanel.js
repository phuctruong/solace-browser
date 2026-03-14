// Diagram: 04-hub-lifecycle
/**
 * Yinyang Sidebar — Domain-First UX (GLOW 453)
 * Tabs: Domains | Chat | Events
 * Registration gate blocks locked features until auth_state === "logged_in"
 */

const API_BASE = 'http://localhost:8888';
const HUB_BASE = 'http://localhost:8888';
const REGISTER_URL = 'https://solaceagi.com/register';

let _isLoggedIn = false;
let _eventsTimer = null;

// ── Helpers ──────────────────────────────────────────────────────────────────

function getAuthHeaders() {
  const token = window.SOLACE_SESSION_TOKEN_SHA256 || window.SOLACE_SESSION_TOKEN || '';
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function getCurrentDomain() {
  if (window.SOLACE_CURRENT_DOMAIN && typeof window.SOLACE_CURRENT_DOMAIN === 'string') {
    return window.SOLACE_CURRENT_DOMAIN.trim();
  }
  if (document.body.dataset.currentDomain) {
    return document.body.dataset.currentDomain.trim();
  }
  return window.location.hostname || '';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function relativeTime(ts) {
  if (!ts) return '';
  const diff = Math.floor((Date.now() / 1000) - Number(ts));
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}), ...getAuthHeaders() };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const payload = await res.json();
  if (!res.ok) throw payload;
  return payload;
}

// ── Tab switching ─────────────────────────────────────────────────────────────

window.switchTab = function switchTab(tabName) {
  document.querySelectorAll('.yy-tab').forEach((t) => t.classList.remove('active'));
  document.querySelectorAll('.yy-panel').forEach((p) => {
    p.classList.remove('active');
    p.setAttribute('aria-hidden', 'true');
  });
  const tab = document.getElementById(`tab-${tabName}`);
  const panel = document.getElementById(`panel-${tabName}`);
  if (tab) tab.classList.add('active');
  if (panel) { panel.classList.add('active'); panel.removeAttribute('aria-hidden'); }

  // Lazy-load tab content
  if (tabName === 'events') loadEvents();
  if (tabName === 'chat' && !_isLoggedIn) showChatLocked();
};

// ── Registration gate ─────────────────────────────────────────────────────────

async function checkRegistration() {
  try {
    const status = await apiFetch('/api/v1/onboarding/status');
    _isLoggedIn = status.auth_state === 'logged_in';
  } catch (_err) {
    _isLoggedIn = false;
  }
  const overlay = document.getElementById('gate-overlay');
  if (overlay) {
    if (_isLoggedIn) overlay.classList.remove('visible');
    else overlay.classList.add('visible');
  }
}

// ── DOMAINS tab ──────────────────────────────────────────────────────────────

function navigateToDomain(domainId) {
  const url = `${HUB_BASE}/domains/${encodeURIComponent(domainId)}`;
  // SOLACE_NAVIGATE_MAIN is injected by the Chromium WebUI host when available
  if (typeof window.SOLACE_NAVIGATE_MAIN === 'function') {
    window.SOLACE_NAVIGATE_MAIN(url);
  } else {
    window.open(url, '_blank', 'noopener');
  }
}

function renderDomainCard(domain) {
  const id = escapeHtml(domain.domain_id || domain.id || domain.domain || '');
  const name = escapeHtml(domain.display_name || domain.name || domain.domain_id || id);
  const desc = escapeHtml(domain.description || '');
  const isOrch = (domain.domain_id || domain.id || '') === 'solaceagi.com';
  const isDefault = Boolean(domain.default_install);
  const loginRequired = Boolean(domain.login_required);

  const iconUrl = `${API_BASE}/api/v1/domains/${encodeURIComponent(id)}/icon`;
  const fallbackLetter = (domain.display_name || domain.domain_id || '?')[0].toUpperCase();

  const cardClass = `domain-card${isOrch ? ' domain-card--orch' : ''}`;
  const fallbackBg = isOrch ? '' : '';

  const badges = [
    isOrch ? '<span class="badge badge--orch">✦ Orch</span>' : '',
    isDefault && !isOrch ? '<span class="badge badge--default">★ Default</span>' : '',
    loginRequired ? '<span class="badge badge--lock">🔒</span>' : '',
  ].filter(Boolean).join('');

  return `
    <div class="${cardClass}" data-domain-id="${id}" role="button" tabindex="0"
         aria-label="Open ${escapeHtml(name)} management page">
      <div class="domain-card__icon-fallback">${escapeHtml(fallbackLetter)}</div>
      <div class="domain-card__body">
        <div class="domain-card__name">${name}</div>
        <div class="domain-card__desc">${desc || id}</div>
      </div>
      ${badges ? `<div class="domain-badges">${badges}</div>` : ''}
    </div>`;
}

async function loadDomains() {
  const listEl = document.getElementById('domain-list');
  const countEl = document.getElementById('domain-count');
  if (!listEl) return;

  listEl.innerHTML = '<span class="spinner"></span>';
  try {
    const data = await apiFetch('/api/v1/domains');
    const domains = Array.isArray(data.domains) ? data.domains
      : Array.isArray(data) ? data : [];

    if (countEl) countEl.textContent = `${domains.length} domains`;

    if (domains.length === 0) {
      listEl.innerHTML = '<p class="yy-empty">No domains found. <a href="http://localhost:8888/domains" target="_blank" rel="noopener">Browse store</a></p>';
      return;
    }

    // Sort: solaceagi.com first, then default-install, then rest alphabetically
    domains.sort((a, b) => {
      const aId = a.domain_id || a.id || '';
      const bId = b.domain_id || b.id || '';
      if (aId === 'solaceagi.com') return -1;
      if (bId === 'solaceagi.com') return 1;
      if (a.default_install && !b.default_install) return -1;
      if (!a.default_install && b.default_install) return 1;
      return (a.display_name || aId).localeCompare(b.display_name || bId);
    });

    listEl.innerHTML = domains.map(renderDomainCard).join('');

    // Wire click + keyboard navigation
    listEl.querySelectorAll('.domain-card').forEach((card) => {
      const id = card.dataset.domainId;
      card.addEventListener('click', () => navigateToDomain(id));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigateToDomain(id); }
      });
    });
  } catch (_err) {
    listEl.innerHTML = '<p class="yy-empty">Could not load domains. Is Solace Hub running?</p>';
    if (countEl) countEl.textContent = '';
  }
}

// ── EVENTS tab ───────────────────────────────────────────────────────────────

function renderEventCard(event) {
  const id = escapeHtml(event.id || '');
  const title = escapeHtml(event.title || 'Event');
  const summary = escapeHtml(event.summary || '');
  const ts = relativeTime(event.ts);
  const url = event.detail_url || `${HUB_BASE}/events/${id}`;

  return `
    <a class="event-card" href="${escapeHtml(url)}" target="_blank" rel="noopener"
       aria-label="${title}">
      <div class="event-card__title">${title}</div>
      ${summary ? `<div class="event-card__summary">${summary}</div>` : ''}
      ${ts ? `<div class="event-card__time">${ts}</div>` : ''}
    </a>`;
}

async function loadEvents() {
  const listEl = document.getElementById('event-list');
  const labelEl = document.getElementById('event-domain-label');
  if (!listEl) return;

  const domain = getCurrentDomain();
  if (labelEl) {
    labelEl.textContent = domain ? `Events for ${domain}` : 'Navigate to a site to see its events';
  }
  if (!domain) {
    listEl.innerHTML = '<p class="yy-empty">No site detected.</p>';
    return;
  }

  listEl.innerHTML = '<span class="spinner"></span>';
  try {
    const data = await apiFetch(`/api/v1/events/feed?domain=${encodeURIComponent(domain)}`);
    const items = Array.isArray(data.items) ? data.items : [];
    if (items.length === 0) {
      listEl.innerHTML = '<p class="yy-empty">No events yet for this domain.</p>';
      return;
    }
    listEl.innerHTML = items.slice(0, 20).map(renderEventCard).join('');
  } catch (_err) {
    listEl.innerHTML = '<p class="yy-empty">Could not load events.</p>';
  }

  // Auto-refresh every 30s while events tab is active
  clearTimeout(_eventsTimer);
  _eventsTimer = setTimeout(() => {
    const eventsPanel = document.getElementById('panel-events');
    if (eventsPanel && eventsPanel.classList.contains('active')) loadEvents();
  }, 30000);
}

// ── CHAT tab ─────────────────────────────────────────────────────────────────

function showChatLocked() {
  const lockedMsg = document.getElementById('chat-locked-msg');
  const inputRow = document.getElementById('chat-input-row');
  if (lockedMsg) lockedMsg.style.display = 'block';
  if (inputRow) inputRow.style.display = 'none';
}

async function sendChatMessage() {
  if (!_isLoggedIn) { showChatLocked(); return; }
  const input = document.getElementById('chat-input');
  const messagesEl = document.getElementById('chat-messages');
  if (!input || !messagesEl) return;

  const text = input.value.trim();
  if (!text) return;
  input.value = '';

  // Append user message
  const userMsg = document.createElement('div');
  userMsg.className = 'chat-msg chat-msg--user';
  userMsg.textContent = text;
  messagesEl.appendChild(userMsg);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Optimistic "typing" indicator
  const typing = document.createElement('div');
  typing.className = 'chat-msg chat-msg--bot';
  typing.textContent = '…';
  messagesEl.appendChild(typing);

  try {
    const res = await apiFetch('/api/yinyang/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, domain: getCurrentDomain() }),
    });
    typing.textContent = res.reply || res.message || '(no response)';
  } catch (_err) {
    typing.textContent = 'Could not reach the AI service.';
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  // Wire chat send
  const sendBtn = document.getElementById('chat-send');
  const chatInput = document.getElementById('chat-input');
  if (sendBtn) sendBtn.addEventListener('click', () => sendChatMessage().catch(() => {}));
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage().catch(() => {}); }
    });
  }

  // Check registration, then load domains (primary content)
  await checkRegistration();
  await loadDomains();
});
