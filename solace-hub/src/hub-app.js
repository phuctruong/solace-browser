// Diagram: 04-hub-lifecycle
(function() {
  'use strict';

  if (window.__solaceHubEnhancerInstalled) {
    return;
  }
  window.__solaceHubEnhancerInstalled = true;

  var API = 'http://localhost:8888';

  function get(path) {
    return fetch(API + path).then(function(r) { return r.json(); });
  }

  function postEvalResult(payload) {
    return fetch(API + '/api/v1/hub/eval-result', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    }).catch(function() {});
  }

  function hubStateSnapshot() {
    var active = document.querySelector('.sb-tab.sb-tab--active[data-tab]');
    return {
      active_tab: active ? active.dataset.tab : null,
      tabs: Array.from(document.querySelectorAll('.sb-tab[data-tab]')).map(function(tab) {
        return {
          id: tab.dataset.tab,
          active: tab.classList.contains('sb-tab--active'),
          bound: tab.dataset.enhancedBound === '1'
        };
      }),
      visible_panels: Array.from(document.querySelectorAll('.hub-tab-panel')).filter(function(panel) {
        return !panel.hidden && panel.style.display !== 'none';
      }).map(function(panel) {
        return panel.id;
      }),
      topbar_user: document.getElementById('topbar-user') ? document.getElementById('topbar-user').textContent : null,
      version_badge: document.getElementById('hub-version-badge') ? document.getElementById('hub-version-badge').textContent : null,
      theme: document.documentElement.getAttribute('data-theme') || 'dark'
    };
  }

  function setActiveTabState(tabId) {
    document.querySelectorAll('.sb-tab[data-tab]').forEach(function(tab) {
      var selected = tab.dataset.tab === tabId;
      tab.classList.toggle('sb-tab--active', selected);
      tab.setAttribute('aria-selected', selected ? 'true' : 'false');
    });

    document.querySelectorAll('.hub-tab-panel').forEach(function(panel) {
      var selected = panel.id === 'tab-' + tabId;
      panel.hidden = !selected;
      panel.style.display = selected ? 'block' : 'none';
      panel.classList.toggle('sh-tab-panel-hidden', !selected);
    });
  }

  function runTabSideEffects(tabId) {
    if (tabId === 'sessions' && typeof window.refreshSessionsTab === 'function') {
      try { window.refreshSessionsTab(); } catch (e) {}
    }
    if (tabId === 'events' && typeof window.refreshEvents === 'function') {
      try { window.refreshEvents(); } catch (e) {}
    }
    if (tabId === 'settings' && typeof window.refreshSettings === 'function') {
      try { window.refreshSettings(); } catch (e) {}
    }
    if (tabId === 'dev') {
      try { hydrateDevWorkspace(); } catch (e) { console.warn('Dev hydration error:', e); }
    }
  }

  // ── SDH5: Live Dev Workspace Hydration ──

  var DEV_ROLES = [
    { id: 'solace-dev-manager', key: 'manager', tables: ['requests','assignments','approvals','artifacts','releases','projects','design_handoffs','coder_handoffs','qa_handoffs'] },
    { id: 'solace-design',      key: 'design',  tables: ['design_specs','design_reviews'] },
    { id: 'solace-coder',       key: 'coder',   tables: ['code_runs','code_artifacts','coder_reviews'] },
    { id: 'solace-qa',          key: 'qa',       tables: ['qa_runs','qa_findings','qa_signoffs'] }
  ];

  function hydrateDevWorkspace() {
    hydrateHubStatus();
    DEV_ROLES.forEach(function(role) {
      hydrateRoleCard(role);
    });
  }

  function hydrateHubStatus() {
    get('/api/v1/hub/status').then(function(data) {
      var el = document.getElementById('dev-live-status');
      if (!el) return;
      var uptime = data.uptime_seconds ? Math.floor(data.uptime_seconds / 60) + 'm' : '?';
      var apps = data.app_count || 0;
      var evidence = data.evidence_count || 0;
      var sessions = data.sessions || 0;
      el.innerHTML =
        '<span class="sb-pill sb-pill--info" style="font-size:0.7rem;">uptime: ' + uptime + '</span> ' +
        '<span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.7rem;">apps: ' + apps + '</span> ' +
        '<span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.7rem;">evidence: ' + evidence + '</span> ' +
        '<span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.7rem;">sessions: ' + sessions + '</span>';
    }).catch(function() {
      var el = document.getElementById('dev-live-status');
      if (el) el.innerHTML = '<span class="sb-pill" style="background:#450a0a;color:#fca5a5;font-size:0.7rem;">runtime offline</span>';
    });
  }

  function hydrateRoleCard(role) {
    // Fetch app metadata
    get('/api/v1/apps/' + role.id).then(function(data) {
      var badge = document.getElementById('role-live-' + role.key);
      if (!badge) return;
      var app = data.app || {};
      badge.innerHTML =
        '<span class="sb-pill sb-pill--info" style="font-size:0.65rem;">v' + (app.version || '?') + '</span>';
    }).catch(function() {
      var badge = document.getElementById('role-live-' + role.key);
      if (badge) badge.innerHTML = '<span class="sb-pill" style="background:#450a0a;color:#fca5a5;font-size:0.65rem;">offline</span>';
    });

    // Fetch table counts for role detail
    role.tables.forEach(function(table) {
      var appId = role.id;
      // Handoff tables live under manager
      if (table === 'design_handoffs' || table === 'coder_handoffs' || table === 'qa_handoffs') {
        appId = 'solace-dev-manager';
      }
      get('/api/v1/backoffice/' + appId + '/' + table + '?page_size=1').then(function(data) {
        var countEl = document.getElementById('live-count-' + role.key + '-' + table);
        if (countEl) {
          var total = data.total || 0;
          countEl.textContent = total;
          countEl.style.display = 'inline';
        }
      }).catch(function() {});
    });
  }

  // Upgraded worker run with structured feedback
  window.__solaceRunWorker = function(appId) {
    var output = document.getElementById('worker-control-output');
    var lastRun = document.getElementById('dev-last-run');
    output.style.display = 'block';
    var ts = new Date().toISOString().slice(11, 19);
    output.textContent = '[' + ts + '] Queuing worker run for ' + appId + '...\n';

    fetch(API + '/api/v1/apps/run/' + appId, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer dragon_rider_override' }
    })
    .then(function(r) { return r.json().then(function(d) { return { status: r.status, data: d }; }); })
    .then(function(res) {
      var ts2 = new Date().toISOString().slice(11, 19);
      var data = res.data;
      var statusCode = res.status;

      if (data.ok) {
        output.textContent += '[' + ts2 + '] ✓ Run completed (HTTP ' + statusCode + ')\n';
        output.textContent += 'Report: ' + (data.report || 'none') + '\n';
      } else {
        output.textContent += '[' + ts2 + '] ✗ Run failed (HTTP ' + statusCode + ')\n';
        output.textContent += 'Error: ' + (data.error || JSON.stringify(data)) + '\n';
      }
      output.textContent += '\nFull response:\n' + JSON.stringify(data, null, 2) + '\n';

      // Update last-run badge
      if (lastRun) {
        var pill = data.ok
          ? '<span class="sb-pill" style="background:#064e3b;color:#6ee7b7;font-size:0.7rem;">last: ' + appId + ' ✓ ' + ts2 + '</span>'
          : '<span class="sb-pill" style="background:#450a0a;color:#fca5a5;font-size:0.7rem;">last: ' + appId + ' ✗ ' + ts2 + '</span>';
        lastRun.innerHTML = pill;
      }
    })
    .catch(function(err) {
      var ts2 = new Date().toISOString().slice(11, 19);
      output.textContent += '[' + ts2 + '] ✗ Network error: ' + err.message + '\n';
      if (lastRun) {
        lastRun.innerHTML = '<span class="sb-pill" style="background:#450a0a;color:#fca5a5;font-size:0.7rem;">last: ' + appId + ' ✗ ' + ts2 + '</span>';
      }
    });
  };

  function activateHubTab(tabId) {
    setActiveTabState(tabId);
    runTabSideEffects(tabId);
    return hubStateSnapshot();
  }

  function executeHubCommand(command) {
    if (!command || typeof command !== 'object') {
      throw new Error('Hub command must be an object');
    }

    switch (command.op) {
      case 'get_state':
        return hubStateSnapshot();
      case 'set_active_tab':
        return activateHubTab(command.tab);
      case 'click_selector': {
        var element = document.querySelector(command.selector);
        if (!element) {
          throw new Error('Selector not found: ' + command.selector);
        }
        if (element.matches('.sb-tab[data-tab]')) {
          return activateHubTab(element.dataset.tab);
        }
        element.click();
        return hubStateSnapshot();
      }
      case 'get_text': {
        var target = document.querySelector(command.selector);
        if (!target) {
          throw new Error('Selector not found: ' + command.selector);
        }
        return {
          selector: command.selector,
          text: target.textContent || ''
        };
      }
      default:
        throw new Error('Unsupported hub command: ' + command.op);
    }
  }

  function installThemeSync() {
    document.querySelectorAll('.sb-theme-btn').forEach(function(btn) {
      if (btn.dataset.enhancedBound === '1') {
        return;
      }
      btn.dataset.enhancedBound = '1';
      btn.addEventListener('click', function() {
        document.documentElement.setAttribute('data-theme', btn.dataset.theme);
        if (document.body) {
          document.body.setAttribute('data-theme', btn.dataset.theme);
        }
      }, true);
    });
  }

  function installTabDelegation() {
    var tablist = document.querySelector('.sb-tabs[role="tablist"]');
    if (!tablist || tablist.dataset.enhancedBound === '1') {
      return;
    }

    tablist.dataset.enhancedBound = '1';

    var handler = function(e) {
      var tab = e.target.closest('.sb-tab[data-tab]');
      if (!tab) {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      activateHubTab(tab.dataset.tab);
    };

    tablist.addEventListener('click', handler, true);
    tablist.addEventListener('pointerup', handler, true);
    tablist.addEventListener('keydown', function(e) {
      var tab = e.target.closest('.sb-tab[data-tab]');
      if (!tab) {
        return;
      }
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        activateHubTab(tab.dataset.tab);
      }
    }, true);

    document.querySelectorAll('.sb-tab[data-tab]').forEach(function(tab) {
      tab.dataset.enhancedBound = '1';
    });

    var active = document.querySelector('.sb-tab.sb-tab--active[data-tab]') ||
      document.querySelector('.sb-tab[data-tab]');
    if (active) {
      activateHubTab(active.dataset.tab);
    }
  }

  function pollPendingHubCommands() {
    return get('/api/v1/hub/pending-js').then(function(payload) {
      var raw = payload && (payload.command || payload.js);
      if (!raw) {
        return;
      }

      var requestId = payload.request_id || null;

      try {
        var command = JSON.parse(raw);
        return postEvalResult({
          request_id: requestId,
          ok: true,
          result: executeHubCommand(command)
        });
      } catch (err) {
        return postEvalResult({
          request_id: requestId,
          ok: false,
          error: err ? String(err.message || err) : 'Hub command failed',
          result: {
            hint: 'Hub accepts structured JSON commands such as {"op":"set_active_tab","tab":"overview"}'
          }
        });
      }
    }).catch(function() {});
  }

  installThemeSync();
  installTabDelegation();

  document.addEventListener('DOMContentLoaded', function() {
    installThemeSync();
    installTabDelegation();
  });
  window.addEventListener('load', function() {
    installThemeSync();
    installTabDelegation();
  });

  setTimeout(pollPendingHubCommands, 200);
  setInterval(pollPendingHubCommands, 1000);
})();
