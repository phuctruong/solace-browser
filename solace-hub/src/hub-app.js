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

  // ── SDR6: Run Inspection + Upgraded Worker Control ──

  // Extract run_id from a report path like ".../outbox/runs/20260328-051200/report.html"
  function extractRunId(reportPath) {
    if (!reportPath) return null;
    var parts = reportPath.replace(/\\/g, '/').split('/');
    for (var i = 0; i < parts.length; i++) {
      if (parts[i] === 'runs' && i + 1 < parts.length && /^\d{8}-\d{6}$/.test(parts[i+1])) {
        return parts[i+1];
      }
    }
    return null;
  }

  // Fetch and display run events
  function fetchRunEvents(appId, runId) {
    return get('/api/v1/apps/' + appId + '/runs/' + runId + '/events')
      .then(function(data) { return data; })
      .catch(function() { return { events: [], count: 0, chain_valid: false, error: true }; });
  }

  // Build the run inspection panel HTML
  function buildRunInspectionHTML(appId, runId, reportPath, eventsData, statusOk) {
    var statusPill = statusOk
      ? '<span class="sb-pill" style="background:#064e3b;color:#6ee7b7;font-size:0.65rem;">PASS</span>'
      : '<span class="sb-pill" style="background:#450a0a;color:#fca5a5;font-size:0.65rem;">FAIL</span>';

    var chainPill = eventsData.chain_valid
      ? '<span class="sb-pill" style="background:#064e3b;color:#6ee7b7;font-size:0.65rem;">chain ✓</span>'
      : '<span class="sb-pill" style="background:#78350f;color:#fcd34d;font-size:0.65rem;">chain ?</span>';

    var eventCount = eventsData.count || 0;
    var eventsPill = '<span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.65rem;">' + eventCount + ' events</span>';

    var html = '<div style="border-left:3px solid #6366f1;padding:0.5rem 0.75rem;margin-top:0.5rem;background:rgba(99,102,241,0.08);border-radius:0 0.5rem 0.5rem 0;">';
    html += '<div style="display:flex;gap:0.4rem;flex-wrap:wrap;align-items:center;">';
    html += '<strong style="font-size:0.8rem;color:var(--sb-on-surface);">' + appId + '</strong> ';
    html += statusPill + ' ' + chainPill + ' ' + eventsPill;
    html += '</div>';
    html += '<div style="margin-top:0.4rem;font-size:0.75rem;color:var(--sb-text-muted);">';
    html += '<strong>run_id:</strong> ' + (runId || '?') + '<br>';
    html += '<strong>report:</strong> ';
    if (reportPath && runId) {
      html += '<a href="/api/v1/apps/' + appId + '/runs/' + runId + '/report" target="_blank" style="color:#818cf8;">open report.html →</a>';
    } else {
      html += '<span style="color:#94a3b8;">none</span>';
    }
    html += '</div>';

    // Events detail (collapsed)
    if (eventCount > 0 && eventsData.events) {
      html += '<details style="margin-top:0.4rem;">';
      html += '<summary style="cursor:pointer;font-size:0.7rem;color:var(--sb-text-muted);">show ' + eventCount + ' events</summary>';
      html += '<pre style="font-size:0.65rem;background:var(--sb-surface-alt,#0f172a);padding:0.5rem;border-radius:0.25rem;max-height:150px;overflow-y:auto;margin-top:0.25rem;">';
      eventsData.events.forEach(function(ev) {
        var ts = ev.timestamp || '';
        var type = ev.event_type || ev.type || '?';
        var detail = ev.detail || ev.metadata || '';
        html += ts.slice(11, 19) + ' [' + type + '] ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) + '\n';
      });
      html += '</pre></details>';
    }

    // Artifact links
    html += '<div style="margin-top:0.4rem;display:flex;gap:0.3rem;flex-wrap:wrap;">';
    if (runId) {
      html += '<a href="/apps/' + appId + '/runs/' + runId + '" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">run detail</a>';
      html += '<a href="/api/v1/apps/' + appId + '/runs/' + runId + '/events" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">events api</a>';
      html += '<a href="/api/v1/apps/' + appId + '/runs/' + runId + '/report" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">report html</a>';
    }
    html += '</div>';
    html += '<div style="margin-top:0.35rem;font-size:0.68rem;color:#94a3b8;">payload.json and stillwater.json are not exposed as first-class Hub routes yet; use run detail and report routes for current inspection.</div>';
    html += '</div>';
    return html;
  }

  // Render inspection into the panel
  function showRunInspection(appId, runId, reportPath, eventsData, statusOk) {
    var panel = document.getElementById('dev-run-inspection');
    if (!panel) return;
    panel.innerHTML = buildRunInspectionHTML(appId, runId, reportPath, eventsData, statusOk);
    panel.style.display = 'block';
  }

  // Upgraded worker run with full inspection pipeline
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
      var runId = extractRunId(data.report);

      if (data.ok) {
        output.textContent += '[' + ts2 + '] ✓ Run completed (HTTP ' + statusCode + ')\n';
        output.textContent += 'Report: ' + (data.report || 'none') + '\n';
        output.textContent += 'Run ID: ' + (runId || 'unknown') + '\n';
      } else {
        output.textContent += '[' + ts2 + '] ✗ Run failed (HTTP ' + statusCode + ')\n';
        output.textContent += 'Error: ' + (data.error || JSON.stringify(data)) + '\n';
      }
      output.textContent += '\nFull response:\n' + JSON.stringify(data, null, 2) + '\n';

      // Update last-run badge
      if (lastRun) {
        var pill = data.ok
          ? '<span class="sb-pill" style="background:#064e3b;color:#6ee7b7;font-size:0.7rem;">last: ' + appId + ' ✓ ' + (runId || ts2) + '</span>'
          : '<span class="sb-pill" style="background:#450a0a;color:#fca5a5;font-size:0.7rem;">last: ' + appId + ' ✗ ' + ts2 + '</span>';
        lastRun.innerHTML = pill;
      }

      // Fetch events and show inspection panel
      if (runId) {
        fetchRunEvents(appId, runId).then(function(eventsData) {
          showRunInspection(appId, runId, data.report, eventsData, !!data.ok);
        });
      } else {
        showRunInspection(appId, null, data.report, { events: [], count: 0, chain_valid: false }, !!data.ok);
      }
    })
    .catch(function(err) {
      var ts2 = new Date().toISOString().slice(11, 19);
      output.textContent += '[' + ts2 + '] ✗ Network error: ' + err.message + '\n';
      if (lastRun) {
        lastRun.innerHTML = '<span class="sb-pill" style="background:#450a0a;color:#fca5a5;font-size:0.7rem;">last: ' + appId + ' ✗ ' + ts2 + '</span>';
      }
      showRunInspection(appId, null, null, { events: [], count: 0, chain_valid: false, error: true }, false);
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
