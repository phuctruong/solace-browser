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

  // Domain traffic rankings (approximate, for sort order)
  // Monthly visits in millions (Similarweb approx, May 2025)
  var DOMAIN_TRAFFIC = {
    'localhost': 99999,
    'google.com': 85000, 'youtube.com': 35000, 'facebook.com': 18000,
    'instagram.com': 8000, 'twitter.com': 6500, 'reddit.com': 3500,
    'amazon.com': 3200, 'whatsapp.com': 2800, 'chatgpt.com': 2500,
    'linkedin.com': 2000, 'mail.google.com': 1800, 'github.com': 1000,
    'drive.google.com': 800, 'calendar.google.com': 500, 'openai.com': 400,
    'slack.com': 300, 'gemini.google.com': 200, 'claude.ai': 100,
    'news.ycombinator.com': 50, 'openrouter.ai': 10,
    'solaceagi.com': 1, 'phuc.net': 1
  };

  function renderDomains() {
    var container = qs('domain-accordion');
    if (!container) return;
    container.innerHTML = '';

    // Detect current domain from browser URL
    var currentDomain = '';
    try { currentDomain = window.top.location.hostname; } catch(e) {}
    if (!currentDomain || currentDomain === '127.0.0.1') currentDomain = 'localhost';

    // Sort by traffic (localhost always first)
    var sorted = state.domains.slice().sort(function(a, b) {
      if (a.host === 'localhost') return -1;
      if (b.host === 'localhost') return 1;
      return (DOMAIN_TRAFFIC[b.host] || 0) - (DOMAIN_TRAFFIC[a.host] || 0);
    });

    sorted.forEach(function (domain) {
      var isCurrentDomain = domain.host === currentDomain || (domain.host === 'localhost' && (currentDomain === 'localhost' || currentDomain === '127.0.0.1'));

      var item = document.createElement('div');
      item.className = 'yy-domain-item';
      item.dataset.domain = domain.host;

      // Header row
      var header = document.createElement('div');
      header.className = 'yy-domain-header' + (isCurrentDomain ? ' yy-selected yy-expanded' : '');
      header.innerHTML = '<img src="' + escapeHtml(domain.icon || '') + '" alt="" onerror="this.src=\'http://127.0.0.1:8888/icons/yinyang-logo.png\'">' +
        '<div class="yy-domain-info"><div class="yy-domain-name">' + escapeHtml(domain.label) + '</div>' +
        '<div class="yy-domain-apps-preview">' + (domain.app_count || 0) + ' apps</div></div>' +
        '<span class="yy-domain-badge"><span class="yy-pill yy-pill-muted" style="font-size:0.6rem">' + (domain.app_count || 0) + '</span></span>' +
        '<span class="yy-chevron">▶</span>';

      // Apps panel (hidden by default, open for current domain)
      var appsPanel = document.createElement('div');
      appsPanel.className = 'yy-domain-apps' + (isCurrentDomain ? ' yy-open' : '');
      appsPanel.id = 'apps-' + domain.host.replace(/\./g, '-');
      appsPanel.innerHTML = '<p class="yy-copy" style="font-size:0.65rem">Loading apps...</p>';

      header.addEventListener('click', function() {
        // Toggle expand
        var wasExpanded = header.classList.contains('yy-expanded');

        // Collapse all others
        container.querySelectorAll('.yy-domain-header').forEach(function(h) { h.classList.remove('yy-expanded', 'yy-selected'); });
        container.querySelectorAll('.yy-domain-apps').forEach(function(p) { p.classList.remove('yy-open'); });

        if (!wasExpanded) {
          header.classList.add('yy-expanded', 'yy-selected');
          appsPanel.classList.add('yy-open');
          loadDomainApps(domain, appsPanel);
          // Scroll into view
          setTimeout(function() { header.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 100);
        }

        // Navigate main browser
        selectDomain(domain.id);
        var url = domain.host === 'localhost' ? 'http://localhost:8888/dashboard' : 'http://localhost:8888/domains/' + encodeURIComponent(domain.host);
        navigateMainBrowser(url);
      });

      item.appendChild(header);
      item.appendChild(appsPanel);
      container.appendChild(item);

      // Auto-load apps for current domain
      if (isCurrentDomain) {
        loadDomainApps(domain, appsPanel);
      }
    });

    setText('domain-count', sorted.length + ' active');

    // Filter input
    var filterInput = qs('domain-filter');
    if (filterInput) {
      filterInput.addEventListener('input', function() {
        var query = this.value.toLowerCase();
        container.querySelectorAll('.yy-domain-item').forEach(function(item) {
          var domain = item.dataset.domain || '';
          item.style.display = domain.toLowerCase().indexOf(query) !== -1 ? '' : 'none';
        });
      });
    }
  }

  // Load apps for a domain into its expand panel
  function loadDomainApps(domain, panel) {
    getJson('/api/v1/domains/' + encodeURIComponent(domain.host) + '/status').then(function(d) {
      var apps = d.apps || [];
      if (!apps.length) {
        panel.innerHTML = '<p class="yy-copy" style="font-size:0.7rem">No apps for this domain.</p>';
        return;
      }
      var html = '';
      apps.forEach(function(app) {
        html += '<div class="yy-app-row">';
        html += '<div class="yy-app-name">' + escapeHtml(app.name || app.app_id) + '</div>';
        html += '<div class="yy-app-meta">' + (app.triggers || 0) + ' triggers · ' + (app.actions || 0) + ' actions</div>';
        html += '<div class="yy-app-actions">';
        html += '<button class="yy-btn-primary" onclick="window.runDomainAction(\'' + escapeHtml(app.app_id) + '\',\'run\')">Run</button>';
        html += '<button onclick="navigateMainBrowser(\'http://localhost:8888/apps/' + escapeHtml(app.app_id) + '\')">Details</button>';
        html += '</div></div>';
      });
      panel.innerHTML = html;
    }).catch(function() {
      panel.innerHTML = '<p class="yy-copy" style="font-size:0.7rem">Could not load apps.</p>';
    });
  }

  // Drill-down: show selected domain + its apps
  function openDomainDrillDown(domain) {
    var section = qs('selected-domain-section');
    var listSection = qs('domain-list-section');
    if (!section) return;

    // Show selected domain, hide domain list
    section.style.display = 'block';
    if (listSection) listSection.style.display = 'none';

    qs('selected-domain-icon').src = domain.icon || '';
    setText('selected-domain-name', domain.label);
    setText('selected-domain-apps-pill', (domain.app_count || 0) + ' apps');

    // Load domain apps
    var appsList = qs('domain-apps-list');
    if (!appsList) return;
    appsList.innerHTML = '<p class="yy-copy">Loading apps...</p>';

    getJson('/api/v1/domains/' + encodeURIComponent(domain.host) + '/status').then(function(d) {
      // OAuth3 status
      var oauth = d.oauth3_status || 'not_configured';
      var oauthPill = qs('selected-domain-oauth3');
      if (oauthPill) {
        if (oauth === 'active') { oauthPill.textContent = 'OAuth3 ✓'; oauthPill.className = 'yy-pill yy-pill-success'; }
        else { oauthPill.textContent = ''; oauthPill.className = ''; }
      }

      var apps = d.apps || [];
      if (!apps.length) {
        appsList.innerHTML = '<p class="yy-copy">No apps for this domain yet.</p>';
        return;
      }

      var html = '';
      apps.forEach(function(app) {
        html += '<div class="yy-app-row">';
        html += '<strong style="font-size:0.8rem">' + escapeHtml(app.name || app.app_id) + '</strong>';
        if (app.triggers > 0) html += ' <span class="yy-pill yy-pill-success" style="font-size:0.55rem">' + app.triggers + ' triggers</span>';
        html += '<div class="yy-app-actions">';
        html += '<button onclick="window.runDomainAction(\'' + escapeHtml(app.app_id) + '\',\'run\')">Run</button>';
        html += '<button onclick="navigateMainBrowser(\'http://localhost:8888/apps/' + escapeHtml(app.app_id) + '\')">Details</button>';
        html += '</div></div>';
      });
      appsList.innerHTML = html;
    }).catch(function() {
      appsList.innerHTML = '<p class="yy-copy">Could not load apps.</p>';
    });
  }

  // Auto-expand current domain when URL changes
  function autoExpandCurrentDomain() {
    var currentDomain = '';
    try { currentDomain = window.top.location.hostname; } catch(e) {}
    if (!currentDomain || currentDomain === '127.0.0.1') currentDomain = 'localhost';

    var container = qs('domain-accordion');
    if (!container) return;

    container.querySelectorAll('.yy-domain-item').forEach(function(item) {
      var domainHost = item.dataset.domain;
      var header = item.querySelector('.yy-domain-header');
      var panel = item.querySelector('.yy-domain-apps');
      if (domainHost === currentDomain && !header.classList.contains('yy-expanded')) {
        container.querySelectorAll('.yy-domain-header').forEach(function(h) { h.classList.remove('yy-expanded', 'yy-selected'); });
        container.querySelectorAll('.yy-domain-apps').forEach(function(p) { p.classList.remove('yy-open'); });
        header.classList.add('yy-expanded', 'yy-selected');
        panel.classList.add('yy-open');
        var domainData = state.domains.find(function(d) { return d.host === domainHost; });
        if (domainData) loadDomainApps(domainData, panel);
        setTimeout(function() { header.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 200);
      }
    });
  }

  // ── Tab Management: report browser tabs to runtime ──
  function reportTabs() {
    try {
      // In Chromium side panel, we can't use chrome.tabs directly
      // But we CAN navigate the main content area via window.top
      // Report the current tab info
      var tabInfo = { url: '', title: '' };
      try {
        tabInfo.url = window.top.location.href;
        tabInfo.title = window.top.document.title;
      } catch(e) {
        // Cross-origin — use last known URL
        tabInfo.url = state.lastReportedUrl || '';
      }
      sendToRuntime({ type: 'tab_info', tabs: [tabInfo] });
    } catch(e) {}
  }
  setInterval(reportTabs, 5000);

  // Navigate main browser area (works from sidebar)
  function navigateMainBrowser(url) {
    try {
      window.top.location.href = url;
    } catch(e) {
      // Cross-origin fallback: send via WebSocket command
      sendToRuntime({ type: 'navigate_request', url: url });
      // Also try postMessage
      try { window.top.postMessage({ type: 'solace_navigate', url: url }, '*'); } catch(e2) {}
    }
  }

  // Make it available globally for onclick handlers
  window.navigateMainBrowser = navigateMainBrowser;

  // Back button: return to domain list
  (function() {
    var backBtn = qs('back-to-domains');
    if (backBtn) {
      backBtn.addEventListener('click', function() {
        var section = qs('selected-domain-section');
        var listSection = qs('domain-list-section');
        if (section) section.style.display = 'none';
        if (listSection) listSection.style.display = 'block';
      });
    }
  })();

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
      setText('domain-count', '0 active');
      renderDomains();
      return;
    }
    if (!state.selectedDomain) {
      state.selectedDomain = state.domains[0];
    } else {
      const current = state.domains.find(function (entry) {
        return entry.id === state.selectedDomain.id || entry.host === state.selectedDomain.host;
      });
      state.selectedDomain = current || state.domains[0];
    }
    setText('domain-count', state.domains.length + ' active');
    renderDomains();
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
      // Reset reconnect backoff on successful connection
      state.reconnectAttempt = 0;
      // Update UI to show connected state
      var dot = document.getElementById('ws-status-dot');
      var statusEl = document.getElementById('hero-status');
      if (dot) dot.className = 'yy-status-dot status-online';
      if (statusEl) statusEl.textContent = 'Connected to Solace Runtime';
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
      // Update UI to show disconnected state
      var dot = document.getElementById('ws-status-dot');
      var statusEl = document.getElementById('hero-status');
      if (dot) dot.className = 'yy-status-dot status-offline';
      if (statusEl) statusEl.textContent = 'Disconnected — reconnecting...';
      // Exponential backoff for reconnection
      state.reconnectAttempt = (state.reconnectAttempt || 0) + 1;
      var delay = Math.min(1000 * Math.pow(2, state.reconnectAttempt - 1), 30000); // 1s → 2s → 4s → ... → 30s max
      setTimeout(connectControlSocket, delay);
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
          // Send URL + page content via WebSocket for auto-capture
          var pageContent = '';
          try { pageContent = window.top.document.documentElement.outerHTML; } catch(e) {}
          sendToRuntime({
            type: 'url_changed',
            url: currentUrl,
            title: window.top.document.title,
            content: pageContent.length > 100 ? pageContent : ''
          });
          // Detect solaceagi.com dashboard login → trigger auth handshake
          if (currentUrl.indexOf('solaceagi.com/dashboard') !== -1 && !state.handshakeAttempted) {
            detectDashboardLogin();
          }
          // Auto-capture: create Prime Wiki snapshot + Stillwater + PZip
          capturePageSnapshot(currentUrl);
          // Check for domain app triggers on this page
          checkDomainTriggers(currentUrl);
          // Auto-expand current domain in sidebar accordion
          autoExpandCurrentDomain();
        }
      } catch (e) {
        // Cross-origin — sidebar can't read top URL, try runtime URL API
        getJson('/api/v1/browser/current-url').then(function(d) {
          if (d && d.url && d.url !== state.lastReportedUrl) {
            state.lastReportedUrl = d.url;
            // Can't capture HTML cross-origin, but notify runtime
            sendToRuntime({ type: 'url_changed', url: d.url, title: '' });
          }
        }).catch(function(){});
      }
    }, 2000);
  }

  // Auto-capture: grab page HTML and send to wiki/extract (Part 11 evidence)
  function capturePageSnapshot(url) {
    try {
      // Only capture if same-origin (cross-origin pages can't be read)
      const html = window.top.document.documentElement.outerHTML;
      if (!html || html.length < 100) return;
      // Skip localhost pages (we're the sidebar itself)
      if (url.indexOf('localhost:8888') !== -1) return;
      if (url.indexOf('127.0.0.1:8888') !== -1) return;

      fetch(API_BASE + '/api/v1/wiki/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, content: html })
      }).then(function(r) { return r.json(); }).then(function(d) {
        if (d.status === 'extracted') {
          console.log('[Solace] Wiki snapshot:', d.codec, d.ratio, 'savings:', d.token_savings?.savings_pct + '%');
        }
      }).catch(function(){});
    } catch (e) {
      // Cross-origin — can't capture HTML, that's expected
    }
  }

  // Check domain app triggers for the current URL
  function checkDomainTriggers(url) {
    try {
      var parts = url.split('://');
      if (parts.length < 2) return;
      var hostPath = parts[1].split('/');
      var domain = hostPath[0];
      var path = '/' + hostPath.slice(1).join('/');
      // Skip localhost
      if (domain.indexOf('localhost') !== -1 || domain.indexOf('127.0.0.1') !== -1) {
        updateActiveApps(null, domain, path);
        return;
      }

      // Fetch trigger matches
      getJson('/api/v1/domains/' + encodeURIComponent(domain) + '/triggers?path=' + encodeURIComponent(path))
        .then(function(d) { updateActiveApps(d, domain, path); })
        .catch(function() {});

      // Fetch domain status
      getJson('/api/v1/domains/' + encodeURIComponent(domain) + '/status')
        .then(function(d) { updateDomainStatus(d); })
        .catch(function() {});
    } catch(e) {}
  }

  // Update the Active Apps section in the sidebar
  function updateActiveApps(data, domain, path) {
    var section = qs('active-apps-section');
    var list = qs('active-apps-list');
    var title = qs('active-apps-title');
    var count = qs('active-apps-count');
    if (!section || !list) return;

    if (!data || !data.matched_apps || data.matched_apps.length === 0) {
      section.style.display = 'none';
      return;
    }

    section.style.display = 'block';
    title.textContent = domain;
    count.textContent = data.matched_apps.length;
    count.className = 'yy-pill yy-pill-success';

    var html = '';
    data.matched_apps.forEach(function(app) {
      html += '<div class="yy-event-item" style="padding:0.5rem;margin-bottom:0.5rem;border:1px solid var(--yy-border);border-radius:8px">';
      html += '<strong>' + (app.app_name || app.app_id) + '</strong>';
      if (app.trigger_context) {
        html += ' <span class="yy-pill yy-pill-success" style="font-size:0.6rem">' + app.trigger_context + '</span>';
      }
      // Action buttons
      if (app.actions && app.actions.length > 0) {
        html += '<div style="margin-top:0.4rem;display:flex;gap:0.3rem;flex-wrap:wrap">';
        app.actions.forEach(function(action) {
          html += '<button class="yy-mode-btn" style="font-size:0.7rem;padding:0.2rem 0.5rem" onclick="runDomainAction(\'' + app.app_id + '\',\'' + action.id + '\')">' + action.label + '</button>';
        });
        html += '</div>';
      }
      html += '</div>';
    });
    list.innerHTML = html;
  }

  // Update the Domain Status section
  function updateDomainStatus(data) {
    var section = qs('domain-status-section');
    var name = qs('domain-status-name');
    var pill = qs('domain-oauth3-pill');
    var detail = qs('domain-status-detail');
    if (!section || !data) return;

    section.style.display = 'block';
    name.textContent = data.domain || '—';

    // OAuth3 status
    var oauthStatus = data.oauth3_status || 'not_configured';
    if (oauthStatus === 'active') {
      pill.textContent = 'OAuth3 ✓';
      pill.className = 'yy-pill yy-pill-success';
    } else if (oauthStatus === 'expired') {
      pill.textContent = 'OAuth3 expired';
      pill.className = 'yy-pill yy-pill-warning';
    } else {
      pill.textContent = 'No login';
      pill.className = 'yy-pill yy-pill-muted';
    }

    var html = '<p class="yy-copy">' + (data.apps_count||0) + ' apps, ' + (data.wiki_snapshots||0) + ' snapshots</p>';
    if (oauthStatus !== 'active' && data.apps_count > 0) {
      html += '<button class="yy-mode-btn" style="margin-top:0.3rem;font-size:0.75rem" onclick="setupOAuth3(\'' + (data.domain||'') + '\')">Setup OAuth3 Login</button>';
    }
    detail.innerHTML = html;
  }

  // Run a domain app action
  window.runDomainAction = function(appId, actionId) {
    postJson('/api/v1/apps/run/' + appId, { action: actionId }).then(function(d) {
      console.log('[Solace] Action result:', d);
    });
  };

  // Setup OAuth3 for a domain
  window.setupOAuth3 = function(domain) {
    // Navigate the main browser to the domain's login page
    try {
      var loginUrls = {
        'mail.google.com': 'https://accounts.google.com/signin',
        'github.com': 'https://github.com/login',
        'linkedin.com': 'https://www.linkedin.com/login',
      };
      var url = loginUrls[domain] || ('https://' + domain + '/login');
      window.top.location.href = url;
    } catch(e) {
      // Cross-origin fallback
      postJson('/api/navigate', { url: 'https://' + domain + '/login' });
    }
  };

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

  // ─── Sidebar Mode Toggle (Navigate vs Create) ───
  window.setYYMode = function(mode) {
    var navMode = document.getElementById('yy-nav-mode');
    var createMode = document.getElementById('yy-create-mode');
    var navBtn = document.getElementById('mode-nav-btn');
    var createBtn = document.getElementById('mode-create-btn');
    if (!navMode || !createMode) return;

    if (mode === 'create') {
      navMode.style.display = 'none';
      createMode.style.display = 'block';
      if (navBtn) navBtn.classList.remove('yy-mode-btn--active');
      if (createBtn) createBtn.classList.add('yy-mode-btn--active');
    } else {
      navMode.style.display = 'block';
      createMode.style.display = 'none';
      if (navBtn) navBtn.classList.add('yy-mode-btn--active');
      if (createBtn) createBtn.classList.remove('yy-mode-btn--active');
    }
  };

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
  var _sidebarUnlocked = false;

  function checkRegistration() {
    getJson('/api/v1/cloud/status').then(function (d) {
      var loggedIn = d.connected && d.config;
      var gate = qs('gate-overlay');
      var main = qs('main-content');
      // Always show main content — sidebar works without login (local apps)
      if (gate) gate.style.display = loggedIn ? 'none' : 'none'; // Hide gate always — show inline prompt instead
      if (main) main.style.display = 'block'; // Always visible
      if (loggedIn) {
        var dot = qs('gate-status-dot');
        if (dot) dot.className = 'yy-status-dot status-online';
        setText('gate-status', 'Signed in as ' + (d.config.user_email || ''));
      }
      // Always load domains and events (works offline / without login)
      if (!_sidebarUnlocked) {
        _sidebarUnlocked = true;
        refreshDomains();
        refreshEvents();
      }
    }).catch(function () {
      // Runtime not reachable — show gate
      var gate = qs('gate-overlay');
      var main = qs('main-content');
      if (gate) gate.style.display = 'block';
      if (main) main.style.display = 'none';
      setText('gate-status', 'Waiting for Solace Runtime...');
    });
  }

  // Poll fast initially (every 2s for first 30s), then every 5s
  var _regPollCount = 0;
  var _regPollInterval = setInterval(function() {
    _regPollCount++;
    checkRegistration();
    if (_regPollCount >= 15) {
      // After 30s, slow down to 5s
      clearInterval(_regPollInterval);
      setInterval(checkRegistration, 5000);
    }
  }, 2000);

  document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    initLanguageSwitcher();
    checkRegistration();
    hydrate();
  });
}());
