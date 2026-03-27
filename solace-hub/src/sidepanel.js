// Diagram: 08b-sidebar-v2-two-modes
// Yinyang Sidebar v2 — Two-Mode Worker Theater
// States: logged_out | idle | domain_detected | worker_running | celebrate
(function () {
  'use strict';

  var API = 'http://127.0.0.1:8888';
  var state = {
    mode: 'loading',       // logged_out | idle | domain_detected | worker_running | celebrate
    gate: 'unregistered',  // unregistered | no_llm | byok | paid
    currentUrl: '',
    currentDomain: '',
    domainApps: [],
    worker: null,          // { id, name, domain, steps: [], status }
    recentSessions: [],
    ws: null,
    sessionId: null
  };

  // ─── Helpers ───
  function $(id) { return document.getElementById(id); }
  function hide(id) { var el = $(id); if (el) el.classList.add('yy-hidden'); }
  function show(id) { var el = $(id); if (el) el.classList.remove('yy-hidden'); }
  function setText(id, val) { var el = $(id); if (el) el.textContent = val; }
  function esc(s) { var d = document.createElement('div'); d.textContent = String(s || ''); return d.innerHTML; }

  // Navigate the MAIN browser tab (not the sidebar)
  function navigateMain(url) {
    if (typeof chrome !== 'undefined' && typeof chrome.send === 'function') {
      chrome.send('solaceNavigateTab', [url]);
    } else {
      postJson('/api/navigate', { url: url }).catch(function () {});
    }
  }

  function getJson(path) {
    return fetch(API + path).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function postJson(path, body) {
    return fetch(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    }).then(function (r) { return r.json(); });
  }

  function sendToRuntime(message) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify(message));
    }
  }

  function normalizeReportedTabs(tabs) {
    return (Array.isArray(tabs) ? tabs : []).map(function (tab, index) {
      return {
        id: String(typeof tab.index === 'number' ? tab.index : (tab.id || tab.url || ('tab-' + index))),
        index: typeof tab.index === 'number' ? tab.index : index,
        url: tab.url || '',
        title: tab.title || '',
        active: !!tab.active
      };
    });
  }

  function publishTabs(tabs) {
    var normalized = normalizeReportedTabs(tabs);
    sendToRuntime({
      type: 'tabs_list',
      session_id: state.sessionId,
      tabs: normalized
    });
    postJson('/api/v1/browser/tabs', { tabs: normalized }).catch(function () {});
  }

  function reportStatus() {
    var url = state.currentUrl || '';
    var title = '';
    try {
      url = window.top.location.href || url;
      title = window.top.document.title || '';
    } catch (e) {}
    sendToRuntime({
      type: 'status',
      session_id: state.sessionId,
      url: url,
      title: title
    });
  }

  function reportTabs() {
    try {
      if (typeof chrome !== 'undefined' && typeof chrome.send === 'function') {
        chrome.send('solaceGetTabs', []);
        return;
      }
      publishTabs([{
        id: state.currentUrl || 'active',
        index: 0,
        url: state.currentUrl || '',
        title: '',
        active: true
      }]);
    } catch (e) {}
  }

  function detectSessionId() {
    return getJson('/api/v1/browser/sessions').then(function (payload) {
      var sessions = Array.isArray(payload.sessions) ? payload.sessions.slice() : [];
      sessions.sort(function (a, b) {
        return String(b.started_at || '').localeCompare(String(a.started_at || ''));
      });
      if (sessions.length && sessions[0].session_id) {
        return sessions[0].session_id;
      }
      return 'sidebar-' + Date.now();
    }).catch(function () {
      return 'sidebar-' + Date.now();
    });
  }

  // ─── State Machine ───
  function switchMode(newMode) {
    state.mode = newMode;
    var shell = $('yy-shell');

    // Hide all state panels
    hide('yy-logged-out');
    hide('yy-idle');
    hide('yy-domain');
    hide('yy-worker');
    hide('yy-celebrate');

    // Remove all shell state classes
    shell.classList.remove('yy-shell--working', 'yy-shell--approval', 'yy-shell--done');

    // Show the right panel
    switch (newMode) {
      case 'logged_out':
        show('yy-logged-out');
        setText('yy-status-pill', 'sign in');
        $('yy-status-pill').className = 'yy-status-pill yy-status-pill--warning';
        break;

      case 'idle':
        show('yy-idle');
        setText('yy-status-pill', 'idle');
        $('yy-status-pill').className = 'yy-status-pill';
        break;

      case 'domain_detected':
        show('yy-domain');
        setText('yy-status-pill', state.currentDomain);
        $('yy-status-pill').className = 'yy-status-pill yy-status-pill--active';
        break;

      case 'worker_running':
        show('yy-worker');
        shell.classList.add('yy-shell--working');
        setText('yy-status-pill', 'working');
        $('yy-status-pill').className = 'yy-status-pill yy-status-pill--active';
        break;

      case 'celebrate':
        show('yy-celebrate');
        shell.classList.add('yy-shell--done');
        setText('yy-status-pill', 'done');
        $('yy-status-pill').className = 'yy-status-pill yy-status-pill--active';
        break;
    }
  }

  // ─── Auth Gate Check ───
  function checkAuth() {
    return getJson('/api/v1/sidebar/state').then(function (d) {
      state.gate = d.gate || 'unregistered';
      return state.gate;
    }).catch(function () {
      state.gate = 'unregistered';
      return 'unregistered';
    });
  }

  // ─── URL Matching (for context-aware app highlighting) ───
  function matchesUrl(app, url) {
    var patterns = app.url_match || [];
    if (!patterns.length || !url) return false;
    for (var i = 0; i < patterns.length; i++) {
      if (url.indexOf(patterns[i]) !== -1) return true;
    }
    return false;
  }

  // ─── Domain Detection ───
  function extractDomain(url) {
    try {
      var hostname = new URL(url).hostname;
      // Skip localhost and internal pages
      if (hostname === 'localhost' || hostname === '127.0.0.1') return '';
      return hostname;
    } catch (e) { return ''; }
  }

  function checkDomainApps(domain) {
    if (!domain) return Promise.resolve([]);
    return getJson('/api/v1/domains/' + encodeURIComponent(domain) + '/status')
      .then(function (d) { return d.apps || []; })
      .catch(function () { return []; });
  }

  function renderDomainApps(domain, apps) {
    state.currentDomain = domain;
    state.domainApps = apps;

    // Domain bar — icon + auth status
    var iconUrl = API + '/icons/yinyang-logo.png';
    $('yy-domain-icon').src = iconUrl;
    getJson('/api/v1/browser/current-url').then(function (d) {
      if (d.icon) $('yy-domain-icon').src = API + d.icon;
    }).catch(function () {});
    $('yy-domain-icon').onerror = function () { this.src = API + '/icons/yinyang-logo.png'; };
    setText('yy-domain-name', domain);
    setText('yy-domain-apps-count', apps.length + ' app' + (apps.length !== 1 ? 's' : ''));

    // Check OAuth3/auth status for this domain
    getJson('/api/v1/oauth3/domain/' + encodeURIComponent(domain)).then(function (auth) {
      var authEl = $('yy-domain-auth');
      if (!authEl) return;
      if (auth.status === 'active' || auth.status === 'likely_active') {
        authEl.innerHTML = '<span class="yy-auth-dot yy-auth-dot--active"></span> Signed in';
      } else if (auth.status === 'expired') {
        authEl.innerHTML = '<span class="yy-auth-dot yy-auth-dot--expired"></span> Sign in needed';
      } else {
        authEl.innerHTML = '<span class="yy-auth-dot yy-auth-dot--unknown"></span> Auth unknown';
      }
    }).catch(function () {});

    // App cards — highlighted if url_match patterns match current URL
    var currentUrl = state.currentUrl || '';
    var html = '';

    // Sort: matching apps first, then non-matching
    var sorted = apps.slice().sort(function (a, b) {
      var aMatch = matchesUrl(a, currentUrl) ? 0 : 1;
      var bMatch = matchesUrl(b, currentUrl) ? 0 : 1;
      return aMatch - bMatch;
    });

    sorted.forEach(function (app) {
      var scheduleText = app.schedule || 'Manual';
      var lastRun = app.last_run || 'Never';
      var hasArgs = app.arguments && app.arguments.length > 0;
      var appIcon = app.icon ? API + app.icon : '';
      var isMatch = matchesUrl(app, currentUrl);
      html += '<div class="yy-app-card' + (isMatch ? ' yy-app-card--active' : '') + '">';
      html += '<div class="yy-app-name">';
      if (appIcon) html += '<img src="' + esc(appIcon) + '" alt="" class="yy-app-icon-sm" onerror="this.classList.add(\'yy-hidden\')">';
      html += esc(app.name || app.app_id);
      if (isMatch) html += ' <span class="yy-match-badge">for this page</span>';
      html += '</div>';
      if (app.description) html += '<div class="yy-app-desc">' + esc(app.description) + '</div>';
      // Argument input (if app accepts arguments)
      if (hasArgs) {
        html += '<div class="yy-app-args" style="margin-top:0.3rem">';
        app.arguments.forEach(function (arg) {
          html += '<input class="yy-arg-input" data-arg="' + esc(arg.name || arg) + '" placeholder="' + esc(arg.label || arg.name || arg) + '" style="width:100%;padding:0.25rem 0.4rem;font-size:0.8rem;background:var(--yy-surface);border:1px solid var(--yy-border);color:var(--yy-text);border-radius:4px;margin-bottom:0.2rem">';
        });
        html += '</div>';
      }
      html += '<div class="yy-app-meta">';
      html += '<span>' + esc(scheduleText) + '</span>';
      html += '<span>' + esc(lastRun === 'Never' ? '' : 'Last: ' + lastRun) + '</span>';
      if (app.persona) html += '<span class="yy-llm-badge">' + esc(app.persona) + '</span>';
      html += '<button class="yy-btn-run" data-app-id="' + esc(app.app_id) + '">Run Now</button>';
      html += '<a href="#" class="yy-app-settings" data-navigate="http://localhost:8888/apps/' + esc(app.app_id) + '">Settings</a>';
      html += '</div></div>';
    });
    $('yy-domain-apps').innerHTML = html;

    // Bind run buttons — collect arguments if present
    $('yy-domain-apps').querySelectorAll('.yy-btn-run').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var appId = this.dataset.appId;
        var card = this.closest('.yy-app-card');
        var args = {};
        if (card) {
          card.querySelectorAll('.yy-arg-input').forEach(function (input) {
            if (input.value.trim()) args[input.dataset.arg] = input.value.trim();
          });
        }
        runWorker(appId, args);
      });
    });
  }

  // ─── Worker Running ───
  function runWorker(appId, args) {
    var app = state.domainApps.find(function (a) { return a.app_id === appId; });
    state.worker = {
      id: appId,
      name: app ? (app.name || appId) : appId,
      domain: state.currentDomain,
      steps: [],
      status: 'running',
      startTime: Date.now()
    };

    setText('yy-worker-name', state.worker.name);
    setText('yy-worker-pill', 'Working...');
    $('yy-worker-pill').className = 'yy-working-pill';
    setText('yy-worker-progress', '');
    $('yy-timeline').innerHTML = '';
    $('yy-approval-area').innerHTML = '';

    switchMode('worker_running');
    addTimelineEntry('Starting worker: ' + state.worker.name);

    // Trigger the worker run (with optional arguments)
    var payload = args && Object.keys(args).length > 0 ? { arguments: args } : {};
    postJson('/api/v1/apps/run/' + encodeURIComponent(appId), payload).then(function (d) {
      if (d.error) {
        addTimelineEntry('Error: ' + d.error);
        state.worker.status = 'error';
      } else {
        addTimelineEntry('Worker dispatched — run ID: ' + (d.run_id || '?'));
      }
    }).catch(function (e) {
      addTimelineEntry('Failed to start: ' + e.message);
    });
  }

  function addTimelineEntry(text) {
    var now = new Date();
    var time = now.toTimeString().substring(0, 8);
    var li = document.createElement('li');
    li.innerHTML = '<span class="yy-step-time">' + time + '</span><span class="yy-step-text">' + esc(text) + '</span>';
    $('yy-timeline').appendChild(li);
    // Auto-scroll to bottom
    var content = li.closest('.yy-content');
    if (content) content.scrollTop = content.scrollHeight;
  }

  function workerDone(summary, runId) {
    var elapsed = state.worker ? Math.round((Date.now() - state.worker.startTime) / 1000) : 0;
    var mins = Math.floor(elapsed / 60);
    var secs = elapsed % 60;

    setText('yy-celebrate-summary', summary || 'Work session complete');
    setText('yy-celebrate-stats', (mins > 0 ? mins + 'm ' : '') + secs + 's');

    var link = $('yy-celebrate-link');
    if (link && state.worker) {
      link.href = 'http://localhost:8888/apps/' + encodeURIComponent(state.worker.id) + (runId ? '/runs/' + runId : '');
    }

    switchMode('celebrate');

    // Return to idle after 30s
    setTimeout(function () {
      if (state.mode === 'celebrate') {
        refreshState();
      }
    }, 30000);
  }

  // ─── Stop Worker ───
  $('yy-btn-stop').addEventListener('click', function () {
    if (state.worker) {
      addTimelineEntry('Stopped by user');
      state.worker.status = 'cancelled';
    }
    refreshState();
  });

  // ─── View Work Session (celebrate link) ───
  $('yy-celebrate-link').addEventListener('click', function (e) {
    e.preventDefault();
    navigateMain(this.href);
    refreshState();
  });

  // ─── WebSocket for Live Updates ───
  function connectWebSocket() {
    if (state.ws) {
      try { state.ws.close(); } catch (e) {}
    }
    detectSessionId().then(function (sessionId) {
      state.sessionId = sessionId;
      try {
        state.ws = new WebSocket('ws://127.0.0.1:8888/ws/yinyang?session=' + encodeURIComponent(sessionId));
      } catch (e) {
        return;
      }
      state.ws.onmessage = function (evt) {
        try {
          var msg = JSON.parse(evt.data);
          handleWsMessage(msg);
        } catch (e) {}
      };
      state.ws.onopen = function () {
        reportStatus();
        reportTabs();
      };
      state.ws.onclose = function () {
        // Reconnect after 5s
        setTimeout(connectWebSocket, 5000);
      };
    }).catch(function () {});
  }

  function handleWsMessage(msg) {
    var command = msg.command || '';
    if (command === 'navigate' && msg.url) {
      navigateMain(msg.url);
      return;
    }
    if (command === 'execute') {
      var script = msg.code || msg.script || '';
      if (script) {
        try {
          if (typeof chrome !== 'undefined' && typeof chrome.send === 'function') {
            chrome.send('solaceEvaluateInPage', [script]);
          } else {
            window.top.eval(script);
          }
        } catch (e) {}
      }
      return;
    }
    if (command === 'close_other_tabs') {
      if (typeof chrome !== 'undefined' && typeof chrome.send === 'function') {
        chrome.send('solaceCloseOtherTabs', []);
        setTimeout(reportTabs, 500);
      }
      return;
    }
    if (command === 'close_tab') {
      if (typeof chrome !== 'undefined' && typeof chrome.send === 'function') {
        var targetIndex = Number(msg.tab_id);
        if (!Number.isNaN(targetIndex)) {
          chrome.send('solaceCloseTab', [targetIndex]);
          setTimeout(reportTabs, 500);
        }
      }
      return;
    }
    if (command === 'get_url') {
      reportStatus();
      return;
    }

    // Worker step events
    if (msg.type === 'worker_step' && state.mode === 'worker_running') {
      addTimelineEntry(msg.text || msg.message || 'Step completed');
      if (msg.progress) {
        setText('yy-worker-progress', msg.progress);
      }
    }

    // Worker done
    if (msg.type === 'worker_done') {
      workerDone(msg.summary, msg.run_id);
    }

    // Worker error
    if (msg.type === 'worker_error' && state.mode === 'worker_running') {
      addTimelineEntry('Error: ' + (msg.error || 'Unknown error'));
      state.worker.status = 'error';
    }

    // Approval needed
    if (msg.type === 'approval_needed' && state.mode === 'worker_running') {
      showApproval(msg);
    }

    // Domain app update
    if (msg.type === 'domain_apps_changed') {
      if (state.currentDomain) {
        checkDomainApps(state.currentDomain).then(function (apps) {
          if (apps.length > 0) renderDomainApps(state.currentDomain, apps);
        });
      }
    }
  }

  function showApproval(msg) {
    var shell = $('yy-shell');
    shell.classList.remove('yy-shell--working');
    shell.classList.add('yy-shell--approval');
    setText('yy-worker-pill', 'Needs approval');
    $('yy-worker-pill').className = 'yy-working-pill yy-status-pill--warning';

    var html = '<div class="yy-approval-card">';
    html += '<div class="yy-approval-title">' + esc(msg.action || 'Action requires approval') + '</div>';
    html += '<div class="yy-approval-desc">' + esc(msg.description || '') + '</div>';
    html += '<div class="yy-approval-actions">';
    html += '<button class="yy-btn-approve" data-approval-id="' + esc(msg.approval_id || '') + '">Approve</button>';
    html += '<button class="yy-btn-reject" data-approval-id="' + esc(msg.approval_id || '') + '">Reject</button>';
    html += '</div></div>';
    $('yy-approval-area').innerHTML = html;

    // Bind buttons
    $('yy-approval-area').querySelector('.yy-btn-approve').addEventListener('click', function () {
      postJson('/api/v1/approvals/' + this.dataset.approvalId + '/approve', {}).catch(function () {});
      $('yy-approval-area').innerHTML = '';
      addTimelineEntry('Approved');
      shell.classList.remove('yy-shell--approval');
      shell.classList.add('yy-shell--working');
      setText('yy-worker-pill', 'Working...');
      $('yy-worker-pill').className = 'yy-working-pill';
    });
    $('yy-approval-area').querySelector('.yy-btn-reject').addEventListener('click', function () {
      postJson('/api/v1/approvals/' + this.dataset.approvalId + '/reject', {}).catch(function () {});
      addTimelineEntry('Rejected — stopping worker');
      refreshState();
    });
  }

  // ─── Logged-Out Teaser ───
  function showTeaser(domain) {
    if (!domain) {
      hide('yy-teaser');
      return;
    }
    checkDomainApps(domain).then(function (apps) {
      if (apps.length > 0) {
        var iconUrl = API + '/icons/domains/' + encodeURIComponent(domain) + '.png';
        $('yy-teaser').innerHTML = '<div class="yy-teaser-domain">' +
          '<img src="' + esc(iconUrl) + '" alt="" onerror="this.src=\'' + API + '/icons/yinyang-logo.png\'">' +
          '<span>' + esc(apps.length) + ' AI worker' + (apps.length !== 1 ? 's' : '') + ' for ' + esc(domain) + '</span></div>' +
          '<p style="font-size:0.75rem;color:var(--yy-text-muted)">Sign in to activate</p>';
        show('yy-teaser');
      }
    }).catch(function () {});
  }

  // ─── Idle State Rendering ───
  function renderIdle() {
    // Get summary
    getJson('/api/v1/system/status').then(function (d) {
      var scheduled = d.scheduled_count || 0;
      var running = d.running_count || 0;
      setText('yy-idle-status', scheduled + ' workers scheduled, ' + running + ' running');
    }).catch(function () {
      setText('yy-idle-status', 'Dashboard available');
    });

    // Scheduled runs — split into "recently ran" and "upcoming"
    getJson('/api/schedules').then(function (d) {
      var jobs = (d.schedules || []).filter(function (j) { return j.enabled; });
      if (!jobs.length) return;

      var now = new Date();
      var nowH = now.getHours();
      var nowM = now.getMinutes();
      var nowMinutes = nowH * 60 + nowM;

      // Parse cron times and sort
      var parsed = jobs.map(function (job) {
        var parts = (job.cron || '').split(' ');
        var m = parseInt(parts[0]) || 0;
        var h = parseInt(parts[1]) || 0;
        var totalMin = h * 60 + m;
        var isPast = totalMin < nowMinutes;
        var ampm = h >= 12 ? 'pm' : 'am';
        var hDisp = h > 12 ? h - 12 : (h === 0 ? 12 : h);
        var timeLabel = hDisp + ':' + (m < 10 ? '0' : '') + m + ampm;
        return { job: job, timeLabel: timeLabel, totalMin: totalMin, isPast: isPast };
      }).sort(function (a, b) { return a.totalMin - b.totalMin; });

      var pastRuns = parsed.filter(function (p) { return p.isPast; });
      var upcoming = parsed.filter(function (p) { return !p.isPast; });

      var html = '';
      // Show current time
      var nowAmPm = nowH >= 12 ? 'pm' : 'am';
      var nowHDisp = nowH > 12 ? nowH - 12 : (nowH === 0 ? 12 : nowH);
      html += '<div class="yy-upcoming-item" style="border-bottom:2px solid var(--yy-accent);padding-bottom:0.3rem;margin-bottom:0.3rem">';
      html += '<span class="yy-upcoming-time" style="color:var(--yy-accent)">now</span>';
      html += '<span class="yy-upcoming-name" style="color:var(--yy-accent)">' + nowHDisp + ':' + (nowM < 10 ? '0' : '') + nowM + nowAmPm + '</span>';
      html += '</div>';

      // Recently ran (last 3)
      pastRuns.slice(-3).forEach(function (p) {
        html += '<div class="yy-upcoming-item" data-navigate="http://localhost:8888/apps/' + esc(p.job.app_id) + '">';
        html += '<span class="yy-upcoming-time" style="color:var(--yy-success)">' + esc(p.timeLabel) + '</span>';
        html += '<span class="yy-upcoming-name">' + esc(p.job.label || p.job.app_id) + ' <span style="color:var(--yy-success);font-size:0.7rem">ran</span></span>';
        html += '</div>';
      });

      // Upcoming (next 3)
      upcoming.slice(0, 3).forEach(function (p) {
        html += '<div class="yy-upcoming-item">';
        html += '<span class="yy-upcoming-time">' + esc(p.timeLabel) + '</span>';
        html += '<span class="yy-upcoming-name">' + esc(p.job.label || p.job.app_id) + '</span>';
        html += '</div>';
      });

      $('yy-upcoming-list').innerHTML = html;
      show('yy-upcoming');
      setText('yy-idle-status', jobs.length + ' workers scheduled, 0 running');
    }).catch(function () {});

    // Recent sessions (last 3 completed runs)
    getJson('/api/v1/events/feed?limit=5').then(function (d) {
      var items = (d.items || []).filter(function (e) { return e.type === 'app_run' || e.type === 'worker_done'; }).slice(0, 3);
      var html = '';
      items.forEach(function (item) {
        html += '<div class="yy-recent-session" data-url="http://localhost:8888/apps/' + esc(item.app_id || '') + '">';
        html += '<span class="yy-session-name">' + esc(item.app_name || item.app_id || 'Worker') + '</span>';
        html += '<span class="yy-session-time">' + esc(item.time || '') + '</span>';
        html += '</div>';
      });
      if (!html) {
        html = '<p style="font-size:0.75rem;color:var(--yy-text-muted)">No recent activity</p>';
        $('yy-idle-cta').textContent = 'Set up your first AI worker →';
      }
      $('yy-recent-sessions').innerHTML = html;

      // Click recent sessions
      $('yy-recent-sessions').querySelectorAll('.yy-recent-session').forEach(function (el) {
        el.addEventListener('click', function () {
          navigateMain(this.dataset.url);
        });
      });
    }).catch(function () {});
  }

  // ─── URL Monitor (detect domain changes) ───
  var lastMonitoredUrl = '';

  // Listen for tab updates from the C++ WebUI bridge (chrome.send('solaceGetTabs'))
  window.addEventListener('solace-tabs-updated', function () {
    var tabs = window.__solaceTabs || [];
    publishTabs(tabs);
    var active = tabs.find(function (t) { return t.active; });
    if (active && active.url) {
      processUrlChange(active.url);
    }
  });

  function monitorUrl() {
    // Method 1: Try direct access (same-origin only — works on localhost pages)
    var currentUrl = '';
    try { currentUrl = window.top.location.href; } catch (e) {}
    if (currentUrl && currentUrl.indexOf('127.0.0.1') === -1 && currentUrl.indexOf('localhost') === -1) {
      processUrlChange(currentUrl);
      return;
    }

    // Method 2: Ask runtime for current browser URL (works cross-origin)
    getJson('/api/v1/browser/current-url').then(function (d) {
      if (d.url) {
        processUrlChange(d.url);
      }
    }).catch(function () {});
  }

  function processUrlChange(currentUrl) {
    if (!currentUrl || currentUrl === lastMonitoredUrl) return;
    lastMonitoredUrl = currentUrl;
    state.currentUrl = currentUrl;
    var sameDocument = false;
    var title = '';
    var content = '';
    try {
      sameDocument = window.top.location.href === currentUrl;
      if (sameDocument) {
        title = window.top.document.title || '';
        content = window.top.document.documentElement.outerHTML || '';
      }
    } catch (e) {}
    sendToRuntime({
      type: 'url_changed',
      session_id: state.sessionId,
      url: currentUrl,
      title: title,
      content: content.length > 100 ? content : ''
    });

    // Don't change mode if worker is running
    if (state.mode === 'worker_running' || state.mode === 'celebrate') return;

    var domain = extractDomain(currentUrl);
    if (!domain) {
      // On localhost or no domain — show idle
      if (state.mode !== 'idle') switchMode('idle');
      return;
    }

    // Check if domain has apps
    checkDomainApps(domain).then(function (apps) {
      if (apps.length > 0) {
        renderDomainApps(domain, apps);
        switchMode('domain_detected');
      } else if (state.mode !== 'idle') {
        switchMode('idle');
      }
    });
  }

  // ─── Main Refresh (determine correct state) ───
  function refreshState() {
    checkAuth().then(function (gate) {
      if (gate === 'unregistered') {
        switchMode('logged_out');
        // Show teaser for current domain
        var domain = extractDomain(state.currentUrl);
        showTeaser(domain);
        return;
      }

      // Logged in (byok, paid, or no_llm) — check for running workers
      getJson('/api/v1/workers/active').then(function (d) {
        if (d.worker && d.worker.status === 'running') {
          // A worker is running — show worker mode
          state.worker = d.worker;
          setText('yy-worker-name', d.worker.name || d.worker.id);
          switchMode('worker_running');
          return;
        }
        // No worker running — check domain
        monitorUrl();
        if (state.mode !== 'domain_detected') {
          switchMode('idle');
          renderIdle();
        }
      }).catch(function () {
        // Workers API not available — just check domain
        monitorUrl();
        if (state.mode !== 'domain_detected') {
          switchMode('idle');
          renderIdle();
        }
      });
    });
  }

  // ─── Delegated click handler for data-navigate links ───
  document.addEventListener('click', function (e) {
    var link = e.target.closest('[data-navigate]');
    if (link) {
      e.preventDefault();
      navigateMain(link.dataset.navigate);
    }
  });

  // ─── Boot ───
  refreshState();
  connectWebSocket();

  // Poll URL changes every 2s
  setInterval(monitorUrl, 2000);

  // Refresh tab truth periodically in case the C++ bridge event is missed
  setInterval(reportTabs, 5000);

  // Refresh state every 15s
  setInterval(refreshState, 15000);

}());
