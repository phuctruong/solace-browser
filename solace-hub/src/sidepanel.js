(function () {
  'use strict';

  const API_BASE = 'http://127.0.0.1:8888';
  const YINYANG_WS_URL = 'ws://127.0.0.1:8888/ws/yinyang';
  const state = {
    sessionId: null,
    onboarding: null,
    summary: null,
    sync: { status: 'idle' },
    tunnel: { active: false, url: '' },
    oauth3: { items: [] },
    cli: { detected: {} },
    domains: [],
    domainStatuses: {},
    events: [],
    selectedDomain: null,
    controlSocket: null,
    lastReportedUrl: ''
  };

  function qs(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    const element = qs(id);
    if (element) {
      element.textContent = value;
    }
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  async function getJson(path) {
    const response = await fetch(API_BASE + path);
    if (!response.ok) {
      throw new Error('HTTP ' + response.status);
    }
    return response.json();
  }

  async function postJson(path, body) {
    const response = await fetch(API_BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    });
    if (!response.ok) {
      throw new Error('HTTP ' + response.status);
    }
    return response.json();
  }

  function appendChatMessage(role, content) {
    const container = qs('chat-messages');
    const message = document.createElement('div');
    message.className = 'yy-msg ' + (role === 'user' ? 'yy-msg-user' : 'yy-msg-ai');
    message.textContent = content;
    container.appendChild(message);
    container.scrollTop = container.scrollHeight;
  }

  async function navigateBrowser(url, options) {
    const payload = Object.assign({ url: url, launch: false }, options || {});
    await postJson('/api/navigate', payload);
  }

  function modelSummary() {
    if (!state.onboarding) {
      return 'No model source';
    }
    const sources = Array.isArray(state.onboarding.model_sources) ? state.onboarding.model_sources.slice() : [];
    if (!sources.length) {
      return 'No model source';
    }
    return sources.join(' + ');
  }

  function activeDomainCount() {
    return Object.values(state.domainStatuses).filter(function (entry) {
      return entry && entry.active;
    }).length;
  }

  function selectedDomainOrFallback() {
    if (state.selectedDomain) {
      return state.selectedDomain;
    }
    return {
      id: 'solaceagi-com',
      label: 'Solace AGI',
      host: 'solaceagi.com',
      url: API_BASE + '/domains/solaceagi.com',
      icon: '/branding/yinyang-rotating.gif',
      active: false,
      setup_state: 'agent-only'
    };
  }

  function domainStatusLabel(status) {
    if (!state.onboarding || state.onboarding.auth_state !== 'logged_in') {
      return 'Agent only';
    }
    if (!state.onboarding.apps_enabled) {
      return 'Pick source';
    }
    if (!status) {
      return 'Setup';
    }
    if (status.active) {
      return 'Active';
    }
    if (status.requires_login) {
      return 'Login';
    }
    return 'Setup';
  }

  function updateHero() {
    const onboarding = state.onboarding || { auth_state: 'logged_out', apps_enabled: false, membership_tier: 'free', device_id: 'pending' };
    const summary = state.summary || {};
    const runtimeHealthy = summary.status === 'ok';
    const dot = qs('ws-status-dot');
    dot.className = 'yy-status-dot ' + (runtimeHealthy ? 'status-online' : 'status-error');
    setText('mode-pill', onboarding.auth_state === 'logged_in' ? (onboarding.apps_enabled ? 'Apps on' : 'Signed in') : 'Agent only');
    setText('source-pill', modelSummary());
    setText('device-pill', onboarding.device_id || 'Device pending');
    setText(
      'hero-copy',
      onboarding.auth_state === 'logged_in'
        ? (onboarding.apps_enabled
          ? 'Apps are on. Click a domain to open its local page and review the recent event feed below.'
          : 'You are signed in. Turn on at least one source: BYOK, CLI wrapper, Ollama, or managed AI.')
        : 'AI agents can already control this browser. Sign in to turn on apps, app-store access, and dashboard orchestration.'
    );
    setText(
      'hero-status',
      runtimeHealthy
        ? 'Protected local runtime healthy on localhost:8888.'
        : 'Checking localhost:8888.'
    );
    setText('domain-count', String(activeDomainCount()) + ' active');
  }

  function renderDomains() {
    const container = qs('domain-grid');
    container.innerHTML = '';
    state.domains.forEach(function (domain) {
      const status = state.domainStatuses[domain.host];
      const button = document.createElement('button');
      const current = selectedDomainOrFallback();
      button.type = 'button';
      button.className = 'yy-domain-button' + (domain.id === current.id ? ' is-selected' : '');
      button.setAttribute('aria-pressed', domain.id === current.id ? 'true' : 'false');
      button.innerHTML = [
        '<img src="' + escapeHtml(domain.icon) + '" alt="">',
        '<span class="yy-domain-label">' + escapeHtml(domain.label) + '</span>',
        '<span class="yy-domain-status">' + escapeHtml(domainStatusLabel(status)) + '</span>'
      ].join('');
      button.addEventListener('click', function () {
        selectDomain(domain.id);
      });
      container.appendChild(button);
    });
  }

  function renderEvents() {
    const container = qs('event-feed');
    const domain = selectedDomainOrFallback();
    container.innerHTML = '';
    setText('event-feed-title', domain.label === 'Solace AGI' ? 'All events' : domain.label + ' events');
    setText('event-feed-copy', domain.label === 'Solace AGI'
      ? 'This feed shows all recent local activity. Click one event to open the full local details page.'
      : 'This feed shows recent activity for ' + domain.label + '. Click one event to open full local details.');
    setText('event-feed-pill', String(state.events.length) + ' events');
    if (!state.events.length) {
      const empty = document.createElement('div');
      empty.className = 'yy-detail-item';
      empty.textContent = 'No events yet for this domain.';
      container.appendChild(empty);
      return;
    }
    state.events.forEach(function (event) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'yy-event-item';
      button.innerHTML = [
        '<strong>' + escapeHtml(event.title || 'Event') + '</strong>',
        '<span>' + escapeHtml(event.summary || '') + '</span>',
        '<span class="yy-event-meta">' + escapeHtml(event.requires_signoff ? 'Requires sign-off' : 'Open details') + '</span>'
      ].join('');
      button.addEventListener('click', function () {
        const url = event.detail_url ? API_BASE + event.detail_url : API_BASE + '/events/' + encodeURIComponent(event.id);
        navigateBrowser(url);
      });
      container.appendChild(button);
    });
  }

  async function refreshDomainStatus(host) {
    const status = await getJson('/api/v1/domains/status?domain=' + encodeURIComponent(host));
    state.domainStatuses[host] = status;
    return status;
  }

  async function refreshDomains() {
    const payload = await getJson('/api/v1/domains');
    state.domains = Array.isArray(payload.items) ? payload.items : [];
    if (!state.domains.length) {
      state.selectedDomain = null;
      return;
    }
    if (!state.selectedDomain) {
      state.selectedDomain = state.domains[0];
      return;
    }
    const current = state.domains.find(function (entry) {
      return entry.id === state.selectedDomain.id || entry.host === state.selectedDomain.host;
    });
    state.selectedDomain = current || state.domains[0];
  }

  async function refreshEvents() {
    const selected = selectedDomainOrFallback();
    const domain = selected.host === 'solaceagi.com' ? 'solaceagi.com' : selected.host;
    const payload = await getJson('/api/v1/events/feed?domain=' + encodeURIComponent(domain));
    state.events = Array.isArray(payload.items) ? payload.items : [];
    renderEvents();
  }

  async function selectDomain(domainId) {
    const selected = state.domains.find(function (entry) { return entry.id === domainId; });
    if (!selected) {
      return;
    }
    state.selectedDomain = selected;
    await refreshDomainStatus(selected.host).catch(function () { return null; });
    renderDomains();
    await refreshEvents().catch(function () { state.events = []; renderEvents(); });
    await navigateBrowser(selected.url).catch(function () {
      setText('hero-status', 'Could not open the local page for ' + selected.label + '.');
    });
  }

  function bindPromptChips() {
    document.querySelectorAll('.yy-prompt-chip').forEach(function (button) {
      button.addEventListener('click', function () {
        qs('chat-input').value = button.getAttribute('data-prompt') || '';
        qs('chat-input').focus();
      });
    });
  }

  // ─── Control Channel: WebSocket to Solace Runtime ───
  // This is the bidirectional control channel between browser and runtime.
  // Runtime → Browser: navigate, reload, get_url, screenshot, execute
  // Browser → Runtime: url_changed, status, chat messages

  function detectSessionId() {
    // Check URL params first (?session=xxx), then generate one
    const params = new URLSearchParams(window.location.search);
    if (params.has('session')) {
      return params.get('session');
    }
    // Try to read from localStorage (persisted from launch)
    const stored = localStorage.getItem('solace_session_id');
    if (stored) return stored;
    // Generate new session ID and persist
    const id = 'sidebar-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8);
    localStorage.setItem('solace_session_id', id);
    return id;
  }

  function connectControlSocket() {
    state.sessionId = detectSessionId();
    const wsUrl = YINYANG_WS_URL + '?session=' + encodeURIComponent(state.sessionId);
    const socket = new WebSocket(wsUrl);
    state.controlSocket = socket;

    socket.addEventListener('open', function () {
      // Report current state on connect
      reportStatus();
      // Start URL monitoring
      startUrlMonitor();
    });

    socket.addEventListener('message', function (event) {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      handleCommand(payload);
    });

    socket.addEventListener('close', function () {
      state.controlSocket = null;
      // Reconnect after 3s
      setTimeout(connectControlSocket, 3000);
    });

    socket.addEventListener('error', function () {
      // Will trigger close → reconnect
    });
  }

  function handleCommand(payload) {
    const command = payload.command;
    if (!command) {
      // Not a command — might be sidebar state or chat response
      if (payload.type === 'ready') {
        setText('chat-model-pill', 'Model: ' + (payload.model || 'offline'));
      } else if (payload.type === 'response') {
        appendChatMessage('ai', payload.text || '');
      }
      return;
    }

    switch (command) {
      case 'navigate':
        if (payload.url) {
          window.top.location.href = payload.url;
        }
        break;
      case 'reload':
        window.top.location.reload();
        break;
      case 'get_url':
        sendToRuntime({
          type: 'status',
          url: window.top.location.href,
          title: window.top.document.title
        });
        break;
      case 'execute':
        if (payload.code) {
          try {
            const result = window.top.eval(payload.code);
            sendToRuntime({ type: 'execute_result', result: String(result) });
          } catch (e) {
            sendToRuntime({ type: 'execute_result', error: e.message });
          }
        }
        break;
      case 'screenshot':
        // Screenshot via html2canvas would need injection; for now report unsupported
        sendToRuntime({ type: 'screenshot', error: 'not_implemented_in_sidebar' });
        break;
    }
  }

  function sendToRuntime(msg) {
    if (state.controlSocket && state.controlSocket.readyState === WebSocket.OPEN) {
      state.controlSocket.send(JSON.stringify(msg));
    }
  }

  function reportStatus() {
    try {
      sendToRuntime({
        type: 'status',
        url: window.top.location.href,
        title: window.top.document.title,
        session_id: state.sessionId
      });
    } catch (e) {
      // Cross-origin — can't read top frame
      sendToRuntime({
        type: 'status',
        url: 'cross-origin',
        title: 'cross-origin',
        session_id: state.sessionId
      });
    }
  }

  function startUrlMonitor() {
    // Poll every 2s to detect URL changes (works cross-origin too)
    setInterval(function () {
      try {
        const currentUrl = window.top.location.href;
        if (currentUrl !== state.lastReportedUrl) {
          state.lastReportedUrl = currentUrl;
          sendToRuntime({
            type: 'url_changed',
            url: currentUrl,
            title: window.top.document.title
          });
          // Detect solaceagi.com dashboard login → trigger auth handshake
          if (currentUrl.indexOf('solaceagi.com/dashboard') !== -1 && !state.handshakeAttempted) {
            detectDashboardLogin();
          }
        }
      } catch (e) {
        // Cross-origin — sidebar can't read top URL
      }
    }, 2000);
  }

  // Detect login on solaceagi.com/dashboard and trigger auth handshake
  function detectDashboardLogin() {
    try {
      // Listen for postMessage from solaceagi.com dashboard (cross-origin safe)
      window.addEventListener('message', function handler(event) {
        if (event.origin && event.origin.indexOf('solaceagi.com') === -1) return;
        if (!event.data || event.data.type !== 'solace_auth') return;
        state.handshakeAttempted = true;
        window.removeEventListener('message', handler);
        performHandshake(event.data.token, event.data.email);
      });
      // Also try polling the runtime for cloud status (in case dashboard already sent it)
      if (!state.handshakeAttempted) {
        pollForDashboardAuth();
      }
    } catch (e) {
      // Cross-origin — expected
    }
  }

  function pollForDashboardAuth() {
    // The solaceagi.com/dashboard has a Local Hub Bridge that POSTs auth to localhost:8888
    // Check if it already connected by polling cloud status
    var pollCount = 0;
    var poller = setInterval(function () {
      pollCount++;
      if (pollCount > 30 || state.handshakeAttempted) {
        clearInterval(poller);
        return;
      }
      getJson('/api/v1/cloud/status').then(function (d) {
        if (d.connected) {
          state.handshakeAttempted = true;
          clearInterval(poller);
          showHandshakeProgress('Connected! Setting up your apps...');
          checkRegistration();
        }
      }).catch(function () {});
    }, 3000);
  }

  function performHandshake(token, email) {
    showHandshakeProgress('Verifying your account...');
    sendToRuntime({
      type: 'auth_handshake',
      token: token,
      email: email
    });
    // Poll for completion
    var checks = 0;
    var checker = setInterval(function () {
      checks++;
      if (checks > 20) {
        clearInterval(checker);
        showHandshakeProgress('Handshake timed out. Try refreshing the dashboard.');
        return;
      }
      getJson('/api/v1/cloud/status').then(function (d) {
        if (d.connected) {
          clearInterval(checker);
          showHandshakeProgress('Connected as ' + (d.config && d.config.user_email ? d.config.user_email : email) + '! Downloading apps...');
          setTimeout(function () {
            showHandshakeProgress('Ready! Yinyang is now active.');
            checkRegistration();
          }, 3000);
        }
      }).catch(function () {});
    }, 2000);
  }

  function showHandshakeProgress(message) {
    var dot = qs('gate-status-dot');
    var text = qs('gate-status');
    if (dot) dot.className = 'yy-status-dot status-connecting';
    if (text) text.textContent = message;
  }

  function bindChat() {
    qs('chat-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      const input = qs('chat-input');
      const message = input.value.trim();
      if (!message) {
        return;
      }
      appendChatMessage('user', message);
      input.value = '';
      if (/(^|\\s)(create|make|build|add)\\b/i.test(message) && /\\b(app|workflow|domain)\\b/i.test(message)) {
        try {
          if (/\\bdomain\\b/i.test(message) && !/\\bapp\\b|\\bworkflow\\b/i.test(message)) {
            const host = message
              .replace(/^(please\\s+)?(create|make|build|add)\\s+/i, '')
              .replace(/\\bdomain\\b/ig, '')
              .replace(/[^\\w.-]/g, ' ')
              .trim()
              .split(/\\s+/)
              .find(Boolean);
            if (!host) {
              throw new Error('missing domain host');
            }
            const createdDomain = await postJson('/api/v1/domains', { domain: host });
            appendChatMessage('ai', 'Added domain "' + (createdDomain.domain && createdDomain.domain.host ? createdDomain.domain.host : host) + '".');
            await refreshDomains();
            renderDomains();
            await refreshEvents().catch(function () { return null; });
            return;
          }
          const currentDomain = selectedDomainOrFallback();
          const title = message
            .replace(/^(please\\s+)?(create|make|build|add)\\s+/i, '')
            .replace(/\\b(app|workflow|domain)\\b/ig, '')
            .replace(/[^\\w\\s-]/g, ' ')
            .trim()
            .split(/\\s+/)
            .filter(Boolean)
            .slice(0, 5)
            .map(function (word) { return word.charAt(0).toUpperCase() + word.slice(1); })
            .join(' ') || (currentDomain.label + ' App');
          const created = await postJson('/api/v1/apps/custom/create', {
            domain: currentDomain.host,
            app_name: title,
            description: message
          });
          appendChatMessage('ai', 'Created "' + (created.app_id || title) + '". Open the domain page to edit setup, run it, or schedule it.');
          await refreshDomainStatus(currentDomain.host).catch(function () { return null; });
          await refreshDomains().catch(function () { return null; });
          renderDomains();
          await refreshEvents().catch(function () { return null; });
        } catch (error) {
          appendChatMessage('ai', 'I could not create that yet: ' + error.message);
        }
        return;
      }
      if (state.controlSocket && state.controlSocket.readyState === WebSocket.OPEN) {
        const currentDomain = selectedDomainOrFallback();
        sendToRuntime({
          type: 'chat',
          message: message,
          context: currentDomain.host
        });
      } else {
        appendChatMessage('ai', 'Not connected to Solace Runtime yet. Retrying...');
      }
    });
  }

  async function hydrate() {
    bindPromptChips();
    bindChat();
    connectControlSocket();
    renderDomains();
    renderEvents();
    try {
      const [onboarding, summary, sync, tunnel, oauth3, cli] = await Promise.all([
        getJson('/api/v1/onboarding/status'),
        getJson('/api/v1/hub/summary'),
        getJson('/api/v1/sync/status').catch(function () { return { status: 'idle' }; }),
        getJson('/api/v1/tunnel/status').catch(function () { return { active: false, url: '' }; }),
        getJson('/api/v1/oauth3/tokens').catch(function () { return { tokens: [] }; }),
        getJson('/api/v1/cli/detect').catch(function () { return { detected: {} }; })
      ]);
      state.onboarding = onboarding;
      state.summary = summary;
      state.sync = sync;
      state.tunnel = tunnel;
      state.oauth3 = { items: Array.isArray(oauth3.tokens) ? oauth3.tokens : [] };
      state.cli = cli;
      await refreshDomains();
      await Promise.all(state.domains.map(function (domain) {
        return refreshDomainStatus(domain.host).catch(function () { return null; });
      }));
      updateHero();
      renderDomains();
      await refreshEvents();
    } catch (error) {
      setText('hero-status', 'Waiting for localhost:8888.');
    }
  }

  // ─── Theme toggle ───
  function initTheme() {
    const saved = localStorage.getItem('solace_theme') || 'dark';
    document.body.setAttribute('data-theme', saved);
    const btn = qs('theme-toggle');
    if (btn) {
      btn.textContent = saved === 'dark' ? '☀' : '🌙';
      btn.addEventListener('click', function () {
        const current = document.body.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.body.setAttribute('data-theme', next);
        localStorage.setItem('solace_theme', next);
        btn.textContent = next === 'dark' ? '☀' : '🌙';
        // Sync to runtime
        postJson('/api/v1/settings/theme', { theme: next }).catch(function () {});
      });
    }
  }

  // ─── Language switcher (matches Solace Hub) ───
  function initLanguageSwitcher() {
    var toggle = qs('lang-toggle');
    var menu = qs('lang-menu');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', function(e) {
      e.stopPropagation();
      var isOpen = !menu.hidden;
      menu.hidden = isOpen;
      toggle.setAttribute('aria-expanded', String(!isOpen));
    });

    document.addEventListener('click', function(e) {
      if (!toggle.contains(e.target) && !menu.contains(e.target)) {
        menu.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
      }
    });

    menu.querySelectorAll('[data-lang]').forEach(function(item) {
      item.addEventListener('click', function(e) {
        e.preventDefault();
        var lang = item.getAttribute('data-lang');
        localStorage.setItem('solace_language', lang);
        // Sync to runtime
        postJson('/api/v1/settings/language', { language: lang }).catch(function() {});
        // Update current indicator
        menu.querySelectorAll('[aria-current]').forEach(function(a) { a.removeAttribute('aria-current'); });
        item.setAttribute('aria-current', 'page');
        menu.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
      });
    });

    // Restore saved language
    var saved = localStorage.getItem('solace_language') || 'en';
    var active = menu.querySelector('[data-lang="' + saved + '"]');
    if (active) {
      menu.querySelectorAll('[aria-current]').forEach(function(a) { a.removeAttribute('aria-current'); });
      active.setAttribute('aria-current', 'page');
    }
  }

  // ─── Registration gate ───
  function checkRegistration() {
    getJson('/api/v1/cloud/status').then(function (d) {
      const loggedIn = d.connected && d.config;
      qs('gate-overlay').style.display = loggedIn ? 'none' : 'block';
      qs('main-content').style.display = loggedIn ? 'block' : 'none';
      if (loggedIn) {
        const dot = qs('gate-status-dot');
        if (dot) dot.className = 'yy-status-dot status-online';
        setText('gate-status', 'Signed in');
      }
    }).catch(function () {
      // Runtime not reachable — show gate
      qs('gate-overlay').style.display = 'block';
      qs('main-content').style.display = 'none';
    });
  }

  // Poll registration status every 5s (user might sign in on solaceagi.com)
  setInterval(checkRegistration, 5000);

  document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    initLanguageSwitcher();
    checkRegistration();
    hydrate();
  });
}());
