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
    hydrateRunHistory();
  }

  // ── SDI7: Durable Last-Known Run State ──

  function hydrateRunHistory() {
    var historyPanel = document.getElementById('dev-run-history');
    var inspectionPanel = document.getElementById('dev-run-inspection');
    var historyHTML = '';
    var latestRun = null;
    var latestRunAppId = null;
    var staleSelection = null;
    var invalidDeepLink = null;
    var pending = DEV_ROLES.length;

    DEV_ROLES.forEach(function(role) {
      get('/api/v1/apps/' + role.id + '/runs').then(function(data) {
        var runs = data.runs || [];
        if (runs.length > 0) {
          // Track the most recent run across all roles
          var newestRun = runs[0];
          if (!latestRun || (newestRun.run_id > (latestRun.run_id || ''))) {
            latestRun = newestRun;
            latestRunAppId = role.id;
          }

          // Build run history entry for this role
          historyHTML += '<div style="margin-bottom:0.5rem;">';
          historyHTML += '<strong style="font-size:0.75rem;color:' + roleColor(role.key) + ';">' + role.key + '</strong>';
          historyHTML += ' <span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.6rem;">' + runs.length + ' runs</span>';
          historyHTML += '<div style="display:flex;flex-direction:column;gap:0.2rem;margin-top:0.2rem;">';
          // Show up to 5 most recent runs
          runs.slice(0, 5).forEach(function(run) {
            var selectBtn = '<a href="#" onclick="window.__solaceSelectRun(\'' + role.id + '\',\'' + run.run_id + '\',this);return false;" class="sb-btn sb-btn--sm sat10-select-run" style="font-size:0.6rem;padding:0.15rem 0.35rem;background:#1e293b;color:#818cf8;border:1px solid #334155;" data-run-id="' + run.run_id + '" data-app-id="' + role.id + '" data-report-exists="' + (run.report_exists ? 'true' : 'false') + '" data-events-exists="' + (run.events_exist ? 'true' : 'false') + '">▸ select</a>';
            var reportPill = run.report_exists
              ? '<a href="/api/v1/apps/' + role.id + '/runs/' + run.run_id + '/artifact/report.html" target="_blank" style="color:#818cf8;font-size:0.65rem;">report</a>'
              : '<span style="color:#64748b;font-size:0.65rem;">no report</span>';
            historyHTML += '<div class="sat10-run-row" id="run-row-' + role.id + '-' + run.run_id + '" style="display:flex;gap:0.4rem;align-items:center;font-size:0.7rem;color:var(--sb-text-muted);padding:0.15rem 0.3rem;border-radius:0.25rem;transition:background 0.15s;">';
            historyHTML += selectBtn + ' ';
            historyHTML += '<code style="font-size:0.65rem;">' + run.run_id + '</code> ';
            historyHTML += reportPill;
            if (run.events_exist) {
              historyHTML += ' <span class="sb-pill" style="background:#1e293b;color:#94a3b8;font-size:0.55rem;">events</span>';
            }
            historyHTML += '</div>';
          });
          historyHTML += '</div></div>';
        }

        pending--;
        if (pending === 0) {
          finishHydration();
        }
      }).catch(function() {
        pending--;
        if (pending === 0) {
          finishHydration();
        }
      });
    });

    function finishHydration() {
      // Render run history
      if (historyPanel && historyHTML) {
        historyPanel.innerHTML = historyHTML;
        historyPanel.style.display = 'block';
      } else if (historyPanel) {
        historyPanel.innerHTML = '<span style="font-size:0.75rem;color:var(--sb-text-muted);">No runs found. Click a worker control button to trigger the first run.</span>';
        historyPanel.style.display = 'block';
      }

      // SAU12: Check URL hash first, then SAP11 session storage
      var hashContext = parseInspectionHash();
      var stored = hashContext || loadSelectedRun();
      var storedSource = hashContext ? 'deep-link' : 'restored';
      if (stored && inspectionPanel) {
        // Verify stored selection exists in current runs list
        var storedRow = document.getElementById('run-row-' + stored.appId + '-' + stored.runId);
        if (storedRow) {
          // Stored/linked selection is still valid — restore it
          restoreSelectedRun(stored.appId, stored.runId, storedRow, storedSource);
          return;
        } else {
          // Stored selection is stale — record fallback and continue to latest run
          if (hashContext) {
            invalidDeepLink = stored;
            clearInspectionHash();
          } else {
            staleSelection = stored;
            clearSelectedRun();
          }
        }
      }

      // Default: hydrate latest-known run into inspection panel
      if (latestRun && latestRunAppId && inspectionPanel) {
        var runId = latestRun.run_id;
        saveSelectedRun(latestRunAppId, runId);
        setInspectionHash(latestRunAppId, runId);
        if (latestRun.events_exist) {
          fetchRunEvents(latestRunAppId, runId).then(function(eventsData) {
            showRunInspection(latestRunAppId, runId, latestRun.report_exists ? 'exists' : null, eventsData, true);
            if (invalidDeepLink) {
              prependInvalidDeepLinkNotice(invalidDeepLink.appId, invalidDeepLink.runId, latestRunAppId, runId);
            }
            if (staleSelection) {
              prependStaleFallbackNotice(staleSelection.appId, staleSelection.runId, latestRunAppId, runId);
            }
          });
        } else {
          showRunInspection(latestRunAppId, runId, latestRun.report_exists ? 'exists' : null, { events: [], count: 0, chain_valid: false }, true);
          if (invalidDeepLink) {
            prependInvalidDeepLinkNotice(invalidDeepLink.appId, invalidDeepLink.runId, latestRunAppId, runId);
          }
          if (staleSelection) {
            prependStaleFallbackNotice(staleSelection.appId, staleSelection.runId, latestRunAppId, runId);
          }
        }

        // Update last-run badge and mark selected row
        var lastRunBadge = document.getElementById('dev-last-run');
        if (lastRunBadge) {
          if (invalidDeepLink) {
            lastRunBadge.innerHTML = '<span class="sb-pill" style="background:#7f1d1d;color:#fca5a5;font-size:0.7rem;">deep link invalid → fallback: ' + latestRunAppId + ' @ ' + runId + '</span>';
          } else if (staleSelection) {
            lastRunBadge.innerHTML = '<span class="sb-pill" style="background:#78350f;color:#fcd34d;font-size:0.7rem;">fallback: ' + latestRunAppId + ' @ ' + runId + '</span>';
          } else {
            lastRunBadge.innerHTML = '<span class="sb-pill" style="background:#064e3b;color:#6ee7b7;font-size:0.7rem;">selected: ' + latestRunAppId + ' @ ' + runId + '</span>';
          }
        }
        highlightSelectedRun(latestRunAppId, runId);
        updateInspectionContext(
          latestRunAppId,
          runId,
          invalidDeepLink ? 'invalid' : (staleSelection ? 'fallback' : 'selected')
        );
      }
    }
  }

  // ── SAT10: Run Selection ──

  // Select and inspect a specific run from history
  window.__solaceSelectRun = function(appId, runId, clickedEl) {
    var reportExists = clickedEl && clickedEl.dataset ? clickedEl.dataset.reportExists === 'true' : false;
    var eventsExist = clickedEl && clickedEl.dataset ? clickedEl.dataset.eventsExists === 'true' : true;

    // SAP11: Persist selection
    saveSelectedRun(appId, runId);
    // SAU12: Update URL hash
    setInspectionHash(appId, runId);
    // SAC13: Update context panel
    updateInspectionContext(appId, runId, 'selected');

    // Update selected-state badge
    var lastRunBadge = document.getElementById('dev-last-run');
    if (lastRunBadge) {
      lastRunBadge.innerHTML = '<span class="sb-pill" style="background:#064e3b;color:#6ee7b7;font-size:0.7rem;">selected: ' + appId + ' @ ' + runId + '</span>';
    }

    // Highlight selected row
    highlightSelectedRun(appId, runId);

    // Fetch events and trigger full inspection + preview chain
    if (eventsExist) {
      fetchRunEvents(appId, runId).then(function(eventsData) {
        showRunInspection(appId, runId, reportExists ? 'exists' : null, eventsData, true);
      });
    } else {
      showRunInspection(appId, runId, reportExists ? 'exists' : null, { events: [], count: 0, chain_valid: false }, true);
    }
  };

  // Backward compat alias
  window.__solaceInspectRun = window.__solaceSelectRun;

  function highlightSelectedRun(appId, runId) {
    // Clear all highlights
    var allRows = document.querySelectorAll('.sat10-run-row');
    for (var i = 0; i < allRows.length; i++) {
      allRows[i].style.background = 'transparent';
    }
    var allBtns = document.querySelectorAll('.sat10-select-run');
    for (var j = 0; j < allBtns.length; j++) {
      allBtns[j].style.background = '#1e293b';
      allBtns[j].style.color = '#818cf8';
      allBtns[j].textContent = '▸ select';
    }
    // Highlight selected
    var selectedRow = document.getElementById('run-row-' + appId + '-' + runId);
    if (selectedRow) {
      selectedRow.style.background = 'rgba(99,102,241,0.12)';
      var btn = selectedRow.querySelector('.sat10-select-run');
      if (btn) {
        btn.style.background = '#6366f1';
        btn.style.color = '#fff';
        btn.textContent = '● viewing';
      }
    }
  }

  // ── SAP11: Durable Selected-Run State ──

  var SELECTED_RUN_KEY = 'solace_dev_selected_run';

  function saveSelectedRun(appId, runId) {
    try {
      sessionStorage.setItem(SELECTED_RUN_KEY, JSON.stringify({ appId: appId, runId: runId }));
    } catch(e) {}
  }

  function loadSelectedRun() {
    try {
      var raw = sessionStorage.getItem(SELECTED_RUN_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (parsed && parsed.appId && parsed.runId) return parsed;
    } catch(e) {}
    return null;
  }

  function clearSelectedRun() {
    try { sessionStorage.removeItem(SELECTED_RUN_KEY); } catch(e) {}
  }

  // ── SAU12: URL-Backed Deep-Link Context ──

  function parseInspectionHash() {
    try {
      var hash = location.hash || '';
      var match = hash.match(/^#inspect=([^/]+)\/(.+)$/);
      if (match && match[1] && match[2]) {
        return { appId: match[1], runId: match[2] };
      }
    } catch(e) {}
    return null;
  }

  function setInspectionHash(appId, runId) {
    try {
      history.replaceState(null, '', '#inspect=' + appId + '/' + runId);
    } catch(e) {}
  }

  function clearInspectionHash() {
    try {
      history.replaceState(null, '', location.pathname + location.search);
    } catch(e) {}
  }

  function showInvalidDeepLinkFallback(appId, runId) {
    var inspectionPanel = document.getElementById('dev-run-inspection');
    if (inspectionPanel) {
      inspectionPanel.style.display = 'block';
      inspectionPanel.innerHTML =
        '<div style="border-left:3px solid #dc2626;padding:0.5rem 0.75rem;background:rgba(220,38,38,0.08);border-radius:0 0.5rem 0.5rem 0;">' +
        '<strong style="font-size:0.8rem;color:var(--sb-on-surface);">Deep link invalid</strong>' +
        '<div style="font-size:0.72rem;color:var(--sb-text-muted);margin-top:0.2rem;">' +
        'The URL pointed to <code>#inspect=' + appId + '/' + runId + '</code> but that run was not found. ' +
        'Falling back to latest known run.</div></div>';
    }
    var lastRunBadge = document.getElementById('dev-last-run');
    if (lastRunBadge) {
      lastRunBadge.innerHTML = '<span class="sb-pill" style="background:#7f1d1d;color:#fca5a5;font-size:0.7rem;">deep link invalid</span>';
    }
  }

  function prependInvalidDeepLinkNotice(oldAppId, oldRunId, newAppId, newRunId) {
    var inspectionPanel = document.getElementById('dev-run-inspection');
    if (inspectionPanel) {
      inspectionPanel.innerHTML =
        '<div style="border-left:3px solid #dc2626;padding:0.5rem 0.75rem;background:rgba(220,38,38,0.08);border-radius:0 0.5rem 0.5rem 0;">' +
        '<strong style="font-size:0.8rem;color:var(--sb-on-surface);">Deep link invalid</strong>' +
        '<div style="font-size:0.72rem;color:var(--sb-text-muted);margin-top:0.2rem;">' +
        'The URL pointed to <code>#inspect=' + oldAppId + '/' + oldRunId + '</code> but that run was not found. ' +
        'Falling back to <code>' + newAppId + ' / ' + newRunId + '</code>.</div></div>' +
        inspectionPanel.innerHTML;
    }
  }

  function restoreSelectedRun(appId, runId, storedRow, source) {
    var btn = storedRow ? storedRow.querySelector('.sat10-select-run') : null;
    var reportExists = btn && btn.dataset ? btn.dataset.reportExists === 'true' : false;
    var eventsExist = btn && btn.dataset ? btn.dataset.eventsExists === 'true' : true;
    var label = source || 'restored';
    var lastRunBadge = document.getElementById('dev-last-run');
    if (lastRunBadge) {
      lastRunBadge.innerHTML = '<span class="sb-pill" style="background:#064e3b;color:#6ee7b7;font-size:0.7rem;">' + label + ': ' + appId + ' @ ' + runId + '</span>';
    }
    setInspectionHash(appId, runId);
    saveSelectedRun(appId, runId);
    highlightSelectedRun(appId, runId);
    updateInspectionContext(appId, runId, label);
    if (eventsExist) {
      fetchRunEvents(appId, runId).then(function(eventsData) {
        showRunInspection(appId, runId, reportExists ? 'exists' : null, eventsData, true);
      });
    } else {
      showRunInspection(appId, runId, reportExists ? 'exists' : null, { events: [], count: 0, chain_valid: false }, true);
    }
  }

  function prependStaleFallbackNotice(oldAppId, oldRunId, newAppId, newRunId) {
    var inspectionPanel = document.getElementById('dev-run-inspection');
    if (inspectionPanel) {
      inspectionPanel.innerHTML =
        '<div style="border-left:3px solid #f59e0b;padding:0.5rem 0.75rem;background:rgba(245,158,11,0.08);border-radius:0 0.5rem 0.5rem 0;">' +
        '<strong style="font-size:0.8rem;color:var(--sb-on-surface);">Stored selection expired</strong>' +
        '<div style="font-size:0.72rem;color:var(--sb-text-muted);margin-top:0.2rem;">' +
        'Previously selected <code>' + oldAppId + ' / ' + oldRunId + '</code> is no longer in the runs list. ' +
        'Falling back to <code>' + newAppId + ' / ' + newRunId + '</code>.</div></div>' +
        inspectionPanel.innerHTML;
    }
  }

  // ── SAC13: Inspection-Context Panel ──

  function updateInspectionContext(appId, runId, source) {
    var panel = document.getElementById('dev-inspection-context');
    var sourcePill = document.getElementById('dev-context-source-pill');
    if (!panel) return;

    var sourceColors = {
      'deep-link':  { bg: '#1e3a5f', color: '#7dd3fc' },
      'restored':   { bg: '#064e3b', color: '#6ee7b7' },
      'selected':   { bg: '#312e81', color: '#a5b4fc' },
      'fallback':   { bg: '#78350f', color: '#fcd34d' },
      'invalid':    { bg: '#7f1d1d', color: '#fca5a5' }
    };
    var sc = sourceColors[source] || sourceColors['selected'];
    var sourceDescriptions = {
      'deep-link': 'Workspace hydrated directly from a shareable inspection link.',
      'restored': 'Workspace restored the last known inspection context from session state.',
      'selected': 'Workspace is showing the run explicitly selected in this session.',
      'fallback': 'Workspace fell back to the latest valid run after stored selection was no longer available.',
      'invalid': 'Requested deep link was invalid, so the workspace fell back to the latest valid run and preserved that outcome visibly.'
    };
    var sourceDescription = sourceDescriptions[source] || sourceDescriptions['selected'];

    if (sourcePill) {
      sourcePill.style.background = sc.bg;
      sourcePill.style.color = sc.color;
      sourcePill.textContent = source;
    }

    var deepLink = location.origin + location.pathname + '?tab=dev#inspect=' + appId + '/' + runId;

    panel.innerHTML =
      '<div style="display:flex;flex-direction:column;gap:0.3rem;">' +
      '<div style="display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap;">' +
      '<code style="font-size:0.72rem;color:var(--sb-on-surface);background:var(--sb-surface-alt,#1e293b);padding:0.15rem 0.35rem;border-radius:0.2rem;">' + appId + ' / ' + runId + '</code>' +
      '</div>' +
      '<div style="font-size:0.68rem;color:var(--sb-text-muted);line-height:1.45;">' + sourceDescription + '</div>' +
      '<div style="display:flex;gap:0.3rem;align-items:center;flex-wrap:wrap;margin-top:0.15rem;">' +
      '<input id="dev-context-link" type="text" readonly value="' + deepLink.replace(/"/g, '&quot;') + '" style="flex:1;min-width:180px;font-size:0.65rem;background:var(--sb-surface-alt,#0f172a);color:var(--sb-text-muted);border:1px solid var(--sb-border,#334155);border-radius:0.25rem;padding:0.2rem 0.35rem;font-family:monospace;">' +
      '<button onclick="window.__solaceCopyInspectionLink()" class="sb-btn sb-btn--sm" id="dev-copy-link-btn" style="font-size:0.65rem;padding:0.2rem 0.5rem;white-space:nowrap;">📋 copy link</button>' +
      '</div>' +
      '</div>';

    updateWorkerDetail(appId, runId);
  }

  // ── SAW14: Worker Detail Panel ──

  function updateWorkerDetail(appId, runId) {
    updateWorkerExecutionMode(appId, runId);
    updateWorkerAssignmentPacket(appId, runId);
    updateWorkerInboxOutbox(appId, runId);
    updateWorkerHumanGate(appId, runId);
    updateWorkerProofState(appId, runId);
    updateWorkerGraphState(appId, runId);
    updateWorkerConventionStore(appId, runId);
    updateWorkerDriftState(appId, runId);
    updateWorkerRoutingState(appId, runId);
    updateWorkerEfficiencyState(appId, runId);
    
    var panel = document.getElementById('dev-worker-detail');
    var diagramPreview = document.getElementById('dev-worker-diagram-preview');
    var rolePill = document.getElementById('dev-worker-role-pill');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    if (rolePill) {
      rolePill.style.background = '#1e293b';
      rolePill.style.color = color;
      rolePill.style.borderLeft = '2px solid ' + color;
      rolePill.textContent = 'Role: ' + roleName;
    }

    var handoffDoc = '';
    if (roleName === 'manager') handoffDoc = 'manager-to-design-handoff.md';
    if (roleName === 'design') handoffDoc = 'design-to-coder-handoff.md';
    if (roleName === 'coder') handoffDoc = 'coder-to-qa-handoff.md';
    var root = '/home/phuc/projects/solace-browser';
    var outboxPath = root + '/apps/' + appId + '/outbox/runs/' + runId;
    var diagrams = getWorkerDiagramEntries(roleName);
    
    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;">';
    html += '<strong style="color:var(--sb-text-muted);">Worker Identity:</strong><br/>';
    html += 'App ID: <code>' + appId + '</code><br/>';
    html += 'Role: <code>' + roleName + '</code><br/>';
    html += 'Artifacts Outbox: <code style="font-size:0.65rem;color:#94a3b8;">' + outboxPath + '</code>';
    html += '</div>';

    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;">';
    html += '<strong style="color:var(--sb-text-muted);">Governing Prime Mermaid Diagrams:</strong><br/>';
    html += '<div style="display:flex;flex-wrap:wrap;gap:0.35rem;margin-top:0.35rem;">';
    diagrams.forEach(function(diagram, index) {
      html += '<button onclick="window.__solaceShowWorkerDiagram(\'' + escapeAttr(diagram.id) + '\')" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.45rem;border-left:2px solid ' + color + ';">' + escapeHtml(diagram.label) + '</button>';
    });
    html += '</div>';
    html += '<div style="font-size:0.65rem;color:var(--sb-text-muted);margin-top:0.35rem;">Use these workspace buttons to inspect the role stack, page map, and current handoff source without relying on editor-only links.</div>';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
    if (diagramPreview) {
      renderWorkerDiagramPreview(diagrams[0]);
    }
  }

  function getWorkerDiagramEntries(roleName) {
    var entries = [
      {
        id: 'role-stack',
        label: 'role stack',
        path: 'specs/solace-dev/diagrams/role-stack.prime-mermaid.md',
        summary: 'The integrated role stack for manager, design, coder, and QA.',
        action: 'scroll',
        targetId: 'dev-role-stack-diagram'
      },
      {
        id: 'browser-page-map',
        label: 'browser page map',
        path: 'specs/solace-dev/diagrams/browser-page-map.prime-mermaid.md',
        summary: 'The primary page and state map for solace-browser as the active managed project.',
        action: 'preview'
      }
    ];
    if (roleName === 'manager') {
      entries.push({
        id: 'manager-handoff',
        label: 'manager handoff',
        path: 'specs/solace-dev/manager-to-design-handoff.md',
        summary: 'The manager-to-design contract that starts the specialist flow.',
        action: 'preview'
      });
    } else if (roleName === 'design') {
      entries.push({
        id: 'design-handoff',
        label: 'design handoff',
        path: 'specs/solace-dev/design-to-coder-handoff.md',
        summary: 'The design-to-coder handoff that transfers page/state intent into implementation work.',
        action: 'preview'
      });
    } else if (roleName === 'coder') {
      entries.push({
        id: 'coder-handoff',
        label: 'coder handoff',
        path: 'specs/solace-dev/coder-to-qa-handoff.md',
        summary: 'The coder-to-QA handoff that transfers runs, artifacts, and review expectations into signoff work.',
        action: 'preview'
      });
    } else if (roleName === 'qa') {
      entries.push({
        id: 'qa-workflow',
        label: 'qa workflow',
        path: 'specs/solace-dev/diagrams/qa-workflow.prime-mermaid.md',
        summary: 'The QA workflow that governs findings, signoff, and release gating.',
        action: 'preview'
      });
    }
    return entries;
  }

  function renderWorkerDiagramPreview(diagram) {
    var preview = document.getElementById('dev-worker-diagram-preview');
    if (!preview || !diagram) return;
    var note = '';
    if (diagram.action === 'scroll' && diagram.targetId) {
      note = 'This diagram already renders inside the workspace below. Use the button again to jump to it.';
    } else {
      note = 'This source artifact is now visible from the workspace as a governed path and summary, even when no editor-specific protocol is available.';
    }
    preview.innerHTML =
      '<div style="border-left:2px solid #6366f1;padding:0.45rem 0.65rem;background:rgba(99,102,241,0.08);border-radius:0 0.35rem 0.35rem 0;display:flex;flex-direction:column;gap:0.25rem;">' +
      '<div style="display:flex;gap:0.35rem;align-items:center;flex-wrap:wrap;">' +
      '<strong style="font-size:0.72rem;color:var(--sb-on-surface);">' + escapeHtml(diagram.label) + '</strong>' +
      '<span class="sb-pill" style="background:#1e293b;color:#a5b4fc;font-size:0.6rem;">Prime Mermaid</span>' +
      '</div>' +
      '<code style="font-size:0.65rem;color:#cbd5e1;background:var(--sb-surface-alt,#0f172a);padding:0.2rem 0.3rem;border-radius:0.2rem;">' + escapeHtml(diagram.path) + '</code>' +
      '<div style="font-size:0.68rem;color:var(--sb-text-muted);line-height:1.45;">' + escapeHtml(diagram.summary) + '</div>' +
      '<div style="font-size:0.65rem;color:var(--sb-text-muted);">' + escapeHtml(note) + '</div>' +
      '</div>';
  }

  window.__solaceShowWorkerDiagram = function(diagramId) {
    var rolePill = document.getElementById('dev-worker-role-pill');
    var roleText = rolePill ? rolePill.textContent || '' : '';
    var roleName = roleText.replace(/^Role:\s*/, '').trim();
    var diagrams = getWorkerDiagramEntries(roleName);
    var diagram = diagrams.find(function(entry) { return entry.id === diagramId; }) || diagrams[0];
    if (!diagram) return;
    renderWorkerDiagramPreview(diagram);
    if (diagram.action === 'scroll' && diagram.targetId) {
      var target = document.getElementById(diagram.targetId);
      if (target && typeof target.scrollIntoView === 'function') {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  // ── SAM17: Execution Mode & Convention Visibility ──

  function updateWorkerExecutionMode(appId, runId) {
    var panel = document.getElementById('dev-worker-execution-mode');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    var mode = 'UNKNOWN';
    var modeDesc = 'State cannot be determined from current artifacts.';
    var convention = 'None';

    if (roleName === 'manager') {
      mode = 'DISCOVER';
      modeDesc = 'High-entropy planning. The manager is constructing a new execution graph and routing tasks for a new feature request.';
      convention = 'solace-dev-workspace.md (Workspace Ruleset)';
    } else if (roleName === 'design') {
      mode = 'DISCOVER';
      modeDesc = 'High-entropy architecture planning. No pre-established UI/UX templates perfectly capture the current workflow.';
      convention = 'prime-mermaid-substrate.md (Architecture Modeling)';
    } else if (roleName === 'coder') {
      mode = 'DISCOVER';
      modeDesc = 'Translating a net-new design handoff into implementation. Actively writing new code structures.';
      convention = 'Coding Standards / UI Mappings (Discovering new boundaries)';
    } else if (roleName === 'qa') {
      mode = 'REPLAY';
      modeDesc = 'Low-entropy validation run. Re-running the standard verification playbook against the new implementation.';
      convention = 'solace-worker-inbox-contract.md (Verification Output Playbook)';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Active Execution Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
    html += 'Mode Basis: <code>role-derived visible contract</code><br/>';
    html += 'Convention Basis: <code>visible reusable artifact for current role</code>';
    html += '</div>';

    html += '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;">';
    
    var modeColor = mode === 'REPLAY' ? '#10b981' : '#f59e0b'; // Green for Replay, Amber for Discover
    var modeBg = mode === 'REPLAY' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)';

    html += '<div style="flex:1;min-width:200px;background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + modeColor + ';">';
    html += '<strong style="color:var(--sb-text-muted);font-size:0.75rem;">Execution Mode:</strong><br/>';
    html += '<div style="margin-top:0.2rem;"><code style="color:' + modeColor + ';background:' + modeBg + ';padding:0.1rem 0.35rem;">' + mode + '</code></div>';
    html += '<div style="margin-top:0.3rem;font-size:0.7rem;color:var(--sb-on-surface);line-height:1.4;">' + escapeHtml(modeDesc) + '</div>';
    html += '</div>';

    html += '<div style="flex:1;min-width:200px;background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);font-size:0.75rem;">Governing Convention / Prime Reuse:</strong><br/>';
    html += '<div style="margin-top:0.2rem;font-family:monospace;color:#818cf8;font-size:0.7rem;line-height:1.4;">' + escapeHtml(convention) + '</div>';
    html += '<div style="margin-top:0.3rem;font-size:0.65rem;color:var(--sb-text-muted);line-height:1.35;">The specific pre-validated contract or workflow this worker is bounded to during the current run.</div>';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAA16: Worker Assignment Packet ──

  function updateWorkerAssignmentPacket(appId, runId) {
    var panel = document.getElementById('dev-worker-assignment-packet');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);
    var outboxPath = '/apps/' + appId + '/outbox/runs/' + runId;

    var statement = '';
    var scopePolicy = 'FAIL_AND_NEW_TASK';
    var evidence = [];

    if (roleName === 'manager') {
      statement = 'Triage incoming requests and distribute bounded task packages to specialist roles.';
      evidence = ['manager-to-design-handoff.md', 'Updated assignment database'];
    } else if (roleName === 'design') {
      statement = 'Translate manager assignments into architectural boundaries and explicit data/UI contracts.';
      evidence = ['design-to-coder-handoff.md', 'Prime Mermaid architectural diagrams'];
    } else if (roleName === 'coder') {
      statement = 'Implement the exact design handoff specification without arbitrary scope expansion.';
      evidence = ['coder-to-qa-handoff.md', 'Source code diffs', 'Passing tests / localized verifications'];
    } else if (roleName === 'qa') {
      statement = 'Verify coder implementation against the original design handoff and requirements.';
      evidence = ['qa-signoffs record', 'Bug triage logs', 'Final review summary'];
    } else {
      statement = 'Unknown assignment.';
      evidence = ['Unknown evidence contract'];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Active Assignment Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
    html += 'Packet Basis: <code>role-derived visible contract</code><br/>';
    html += 'Outbox Root: <code style="font-size:0.65rem;color:#94a3b8;">' + escapeHtml(outboxPath) + '</code>';
    html += '</div>';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Task Statement / Objective:</strong><br/>';
    html += '<div style="margin-top:0.2rem;font-family:monospace;color:var(--sb-on-surface); line-height:1.4;">' + escapeHtml(statement) + '</div>';
    html += '</div>';

    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Scope Change Policy:</strong><br/>';
    html += '<div style="margin-top:0.2rem;"><code style="color:#ef4444;background:rgba(239,68,68,0.1);padding:0.1rem 0.3rem;">' + escapeHtml(scopePolicy) + '</code></div>';
    html += '</div>';

    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Evidence Contract (Required Output):</strong><br/>';
    html += '<ul style="margin:0.2rem 0 0 1rem;padding:0;color:var(--sb-on-surface);font-family:monospace;font-size:0.7rem;">';
    evidence.forEach(function(item) {
      if (item.indexOf('.md') > -1) {
        html += '<li><code style="color:#818cf8;background:transparent;padding:0;">' + escapeHtml(item) + '</code></li>';
      } else {
        html += '<li>' + escapeHtml(item) + '</li>';
      }
    });
    html += '</ul>';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAI15: Worker Inbox/Outbox ──

  function updateWorkerInboxOutbox(appId, runId) {
    var panel = document.getElementById('dev-worker-inbox-outbox');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);
    var outboxPath = '/apps/' + appId + '/outbox/runs/' + runId;

    var inbox = [];
    var outbox = [];

    if (roleName === 'manager') {
      inbox = ['User Request / Assignment Context', 'solace-dev-workspace.md', 'solace-worker-inbox-contract.md'];
      outbox = ['manager-to-design-handoff.md', 'Project Map Updates'];
    } else if (roleName === 'design') {
      inbox = ['manager-to-design-handoff.md', 'Product Requirements'];
      outbox = ['design-to-coder-handoff.md', 'UI Maps / Figma Targets'];
    } else if (roleName === 'coder') {
      inbox = ['design-to-coder-handoff.md', 'TODO.md (Current Round)'];
      outbox = ['coder-to-qa-handoff.md', 'Code Commits', 'App Outbox / Runs'];
    } else if (roleName === 'qa') {
      inbox = ['coder-to-qa-handoff.md', 'App Outbox / Runs', 'Code Changes'];
      outbox = ['qa-signoffs', 'Review Reports / Bug Triage'];
    } else {
      inbox = ['Unknown Inputs'];
      outbox = ['Unknown Outputs'];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Active Contract Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
    html += 'Outbox Root: <code style="font-size:0.65rem;color:#94a3b8;">' + escapeHtml(outboxPath) + '</code>';
    html += '</div>';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Inbox Inputs (read-only context):</strong><br/>';
    html += '<ul style="margin:0.2rem 0 0 1rem;padding:0;color:var(--sb-on-surface);font-family:monospace;font-size:0.7rem;">';
    inbox.forEach(function(item) {
      if (item.indexOf('.md') > -1) {
        html += '<li><code style="color:#818cf8;background:transparent;padding:0;">' + escapeHtml(item) + '</code></li>';
      } else {
        html += '<li>' + escapeHtml(item) + '</li>';
      }
    });
    html += '</ul>';
    html += '</div>';

    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Outbox Outputs (result surface):</strong><br/>';
    html += '<ul style="margin:0.2rem 0 0 1rem;padding:0;color:var(--sb-on-surface);font-family:monospace;font-size:0.7rem;">';
    outbox.forEach(function(item) {
      if (item === 'App Outbox / Runs') {
        html += '<li><a href="#" onclick="document.getElementById(\'dev-run-history-card\').scrollIntoView();return false;" style="color:#818cf8;text-decoration:none;">' + escapeHtml(item) + '</a></li>';
      } else if (item.indexOf('.md') > -1) {
        html += '<li><code style="color:#818cf8;background:transparent;padding:0;">' + escapeHtml(item) + '</code></li>';
      } else {
        html += '<li>' + escapeHtml(item) + '</li>';
      }
    });
    html += '</ul>';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAH18: Human Approval Gate ──

  function updateWorkerHumanGate(appId, runId) {
    var panel = document.getElementById('dev-worker-human-gate');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    // Mock realistic states tied to the roles for SAH18 visibility demonstration
    var state = 'unknown';
    var message = '';

    if (roleName === 'manager') {
      state = 'not_yet_at_gate';
      message = 'Autonomous parsing currently active. Manager routing does not currently require review unless budget constraints are exceeded.';
    } else if (roleName === 'design') {
      state = 'awaiting_human';
      message = 'Blocked pending visual review of the UI topology and flow architecture. Human architect must sign off before coder execution.';
    } else if (roleName === 'coder') {
      state = 'intervention_required';
      message = 'Linting or automated constraints failed unexpectedly. Human intervention requested to resolve the paradox or adjust lint policies.';
    } else if (roleName === 'qa') {
      state = 'approved';
      message = 'Human review completed. Test results, QA signatures, and evidence hashes have been countersigned by the Dev Lead.';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Active Human Gate Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
    html += 'Gate Basis: <code>role-derived visible approval contract</code><br/>';
    html += 'Intervention Basis: <code>human review state for current role/run</code>';
    html += '</div>';

    html += '<div style="display:flex;align-items:flex-start;gap:0.75rem;padding:0.5rem;border-radius:0.25rem;background:var(--sb-surface-alt,#1e293b);border-left:2px solid ' + color + ';">';
    
    var icon = '⏳';
    var stateColor = '#94a3b8'; // gray
    var bg = 'rgba(148,163,184,0.1)';

    if (state === 'awaiting_human') {
      icon = '🛑';
      stateColor = '#ef4444'; // red
      bg = 'rgba(239,68,68,0.1)';
    } else if (state === 'approved') {
      icon = '✅';
      stateColor = '#10b981'; // green
      bg = 'rgba(16,185,129,0.1)';
    } else if (state === 'intervention_required') {
      icon = '⚠️';
      stateColor = '#f59e0b'; // amber
      bg = 'rgba(245,158,11,0.1)';
    }

    html += '<div style="font-size:1.5rem;line-height:1;">' + icon + '</div>';
    html += '<div style="flex:1;">';
    html += '<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;">';
    html += '<code style="font-size:0.7rem;color:' + stateColor + ';background:' + bg + ';padding:0.1rem 0.35rem;white-space:nowrap;">' + state + '</code>';
    html += '</div>';
    html += '<div style="font-size:0.75rem;color:var(--sb-on-surface);line-height:1.4;">' + escapeHtml(message) + '</div>';
    
    if (state === 'awaiting_human' || state === 'intervention_required') {
      html += '<div style="margin-top:0.4rem;">';
      html += '<button class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.6rem;background:var(--sb-btn-bg,#3b82f6);color:#fff;border:none;">Review & Approve</button>';
      html += '</div>';
    }

    html += '</div>';
    html += '</div>';
    
    panel.innerHTML = html;
    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAT19: Transparency & Proof State ──

  function updateWorkerProofState(appId, runId) {
    var panel = document.getElementById('dev-worker-proof-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    // Mock realistic states tied to the roles for SAT19 visibility demonstration
    var state = 'missing';
    var available = [];
    var unproven = [];

    if (roleName === 'manager') {
      state = 'proven';
      available = ['Routing Trace Logs', 'Ticket Database Entry'];
      unproven = ['None (Deterministic)'];
    } else if (roleName === 'design') {
      state = 'partial';
      available = ['design-to-coder-handoff.md', 'Prime Mermaid Diagrams'];
      unproven = ['Human Architect Countersignature', 'Edge-Case Layouts'];
    } else if (roleName === 'coder') {
      state = 'missing';
      available = ['Local Log Traces'];
      unproven = ['Automated Test Passing Hashes', 'Visual Snapshot Diffs', 'QA Review Signoff'];
    } else if (roleName === 'qa') {
      state = 'proven';
      available = ['Full Automated Test Output', 'Visual Regression Hashes', 'qa-signoffs record'];
      unproven = ['None (Fully Certified)'];
    }

    var icon = '❓';
    var stateColor = '#ef4444'; // red (missing)
    var bg = 'rgba(239,68,68,0.1)';

    if (state === 'proven') {
      icon = '🛡️';
      stateColor = '#10b981'; // green
      bg = 'rgba(16,185,129,0.1)';
    } else if (state === 'partial') {
      icon = '⚖️';
      stateColor = '#f59e0b'; // amber
      bg = 'rgba(245,158,11,0.1)';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Active Proof Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
    html += 'Proof Basis: <code>role-derived visible evidence contract</code><br/>';
    html += 'Transparency Basis: <code>visible proof state for current role/run</code>';
    html += '</div>';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';display:flex;align-items:center;gap:0.5rem;">';
    html += '<div style="font-size:1.2rem;">' + icon + '</div>';
    html += '<div>';
    html += '<strong style="color:var(--sb-text-muted);">Certification Level:</strong> ';
    html += '<code style="color:' + stateColor + ';background:' + bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;">' + state + '</code>';
    html += '<div style="font-size:0.65rem;color:#94a3b8;margin-top:0.1rem;">Software 5.0 systems require all outputs to be mathematically or visually proven (Paper SI18).</div>';
    html += '</div></div>';

    html += '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;">';

    html += '<div style="flex:1;min-width:200px;background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Evidence Present:</strong><br/>';
    html += '<ul style="margin:0.2rem 0 0 1rem;padding:0;color:var(--sb-on-surface);font-family:monospace;font-size:0.7rem;">';
    available.forEach(function(item) {
      if (item.indexOf('.md') > -1) {
        html += '<li><code style="color:#818cf8;background:transparent;padding:0;">' + escapeHtml(item) + '</code></li>';
      } else {
        html += '<li style="color:#10b981;">' + escapeHtml(item) + '</li>';
      }
    });
    html += '</ul>';
    html += '</div>';

    html += '<div style="flex:1;min-width:200px;background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid #ef4444;">';
    html += '<strong style="color:var(--sb-text-muted);">Unproven / Missing Elements:</strong><br/>';
    html += '<ul style="margin:0.2rem 0 0 1rem;padding:0;color:var(--sb-on-surface);font-family:monospace;font-size:0.7rem;">';
    unproven.forEach(function(item) {
      if (item.indexOf('None') === 0) {
        html += '<li style="color:#94a3b8;list-style:none;margin-left:-1rem;">' + escapeHtml(item) + '</li>';
      } else {
        html += '<li style="color:#ef4444;">' + escapeHtml(item) + '</li>';
      }
    });
    html += '</ul>';
    html += '</div>';

    html += '</div>'; // close row

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAG20: Execution Graph Trace ──

  function updateWorkerGraphState(appId, runId) {
    var panel = document.getElementById('dev-worker-graph-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    // Mock realistic states tied to the roles for SAG20 visibility demonstration (Based on paper SI10)
    var graphTopology = '';
    var activeNode = '';
    var activeNodeType = '';

    if (roleName === 'manager') {
      graphTopology = 'PLANNER &rarr; ROUTER &rarr; AGGREGATOR';
      activeNode = 'ROUTER';
      activeNodeType = 'Deterministic Mode Selection';
    } else if (roleName === 'design') {
      graphTopology = 'RETRIEVER &rarr; PLANNER &rarr; EVALUATOR';
      activeNode = 'PLANNER';
      activeNodeType = 'Probabilistic Topology Generation';
    } else if (roleName === 'coder') {
      graphTopology = 'RETRIEVER &rarr; EXECUTOR &rarr; EVALUATOR';
      activeNode = 'EXECUTOR';
      activeNodeType = 'Probabilistic Artifact Generation';
    } else if (roleName === 'qa') {
      graphTopology = 'EVALUATOR &rarr; TERMINATOR';
      activeNode = 'EVALUATOR';
      activeNodeType = 'Deterministic Validation Gate';
    } else {
      graphTopology = 'UNKNOWN_GRAPH';
      activeNode = 'UNKNOWN';
      activeNodeType = 'Unknown Node Execution';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Active Graph Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
    html += 'Graph Basis: <code>role-derived visible execution graph</code><br/>';
    html += 'Path Basis: <code>visible active stage for current role/run</code>';
    html += '</div>';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Solace Execution Graph Structure:</strong><br/>';
    html += '<div style="font-family:monospace;margin-top:0.3rem;color:#818cf8;background:rgba(129,140,248,0.1);padding:0.3rem 0.5rem;border-radius:0.25rem;">' + graphTopology + '</div>';
    html += '</div>';

    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';display:flex;align-items:center;gap:0.75rem;">';
    html += '<div style="font-size:1.4rem;">⚙️</div>';
    html += '<div>';
    html += '<strong style="color:var(--sb-text-muted);">Active Node Context:</strong><br/>';
    html += '<span style="color:var(--sb-on-surface);font-weight:600;">' + escapeHtml(activeNode) + '</span> &mdash; <span style="color:#94a3b8;font-size:0.7rem;">' + escapeHtml(activeNodeType) + '</span>';
    html += '</div>';
    html += '</div>';

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'Execution nodes define verifiable edges connecting Context &rarr; Operations &rarr; Validation (Paper SI10).';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAC21: Convention Store Binding ──

  function updateWorkerConventionStore(appId, runId) {
    var panel = document.getElementById('dev-worker-convention-store');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    // Mock realistic convention states tied to the roles for SAC21 visibility demonstration
    var conventionId = 'null_convention';
    var storeLevel = 'N/A';
    var replayStatus = 'discover_only';
    var desc = 'No matching convention. Operating in discover-only ripple mode.';

    if (roleName === 'manager') {
      conventionId = 'nexus-routing-v2.1';
      storeLevel = 'GLOBAL';
      replayStatus = 'replayable';
      desc = 'Global marketplace convention for parsing incoming intent into constrained dev roles.';
    } else if (roleName === 'design') {
      conventionId = 'ui-topology-draft';
      storeLevel = 'LOCAL';
      replayStatus = 'partial';
      desc = 'Local unvalidated workflow. Requires structural integrity tests before caching.';
    } else if (roleName === 'coder') {
      conventionId = 'solace-prime-mermaid-coder-v1.2.0';
      storeLevel = 'SHARED';
      replayStatus = 'replayable';
      desc = 'Shared team convention enforcing strict prime-coder rules and evidence generation.';
    } else if (roleName === 'qa') {
      conventionId = 'null_convention';
      storeLevel = 'N/A';
      replayStatus = 'discover_only';
      desc = 'No matching convention. Operating in discover-only boundary-exploration mode.';
    }

    var icon = '🔍';
    var stateColor = '#94a3b8'; // gray
    var bg = 'rgba(148,163,184,0.1)';

    if (replayStatus === 'replayable') {
      icon = '📦';
      stateColor = '#10b981'; // green
      bg = 'rgba(16,185,129,0.1)';
    } else if (replayStatus === 'partial') {
      icon = '⏳';
      stateColor = '#f59e0b'; // amber
      bg = 'rgba(245,158,11,0.1)';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Active Convention Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
    html += 'Convention Basis: <code>role-derived visible convention binding</code><br/>';
    html += 'Replay Basis: <code>visible convention maturity for current role/run</code>';
    html += '</div>';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';display:flex;align-items:flex-start;gap:0.75rem;">';
    
    html += '<div style="font-size:1.4rem;line-height:1;">' + icon + '</div>';
    
    html += '<div style="flex:1;">';
    html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.2rem;">';
    html += '<div>';
    html += '<strong style="color:var(--sb-text-muted);">Active Convention:</strong> ';
    html += '<code style="color:' + stateColor + ';background:transparent;padding:0;font-size:0.75rem;">' + escapeHtml(conventionId) + '</code>';
    html += '</div>';
    html += '<code style="color:' + stateColor + ';background:' + bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + replayStatus + '</code>';
    html += '</div>';
    
    html += '<div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.3rem;">';
    html += '<strong style="color:var(--sb-text-muted);font-size:0.65rem;">Store Ring:</strong> ';
    html += '<span style="font-size:0.65rem;color:#818cf8;background:rgba(129,140,248,0.1);padding:0.1rem 0.3rem;border-radius:0.15rem;">' + storeLevel + '</span>';
    html += '</div>';

    html += '<div style="font-size:0.7rem;color:#94a3b8;line-height:1.4;">' + escapeHtml(desc) + '</div>';
    html += '</div>'; // close text column

    html += '</div>'; // close surface

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'The Convention Store acts as persistent intelligence, converting ephemeral ripple execution into reusable caching layers according to SI14.';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAD22: Drift Detection & Adaptive Replay ──

  function updateWorkerDriftState(appId, runId) {
    var panel = document.getElementById('dev-worker-drift-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    // Mock realistic drift and adaptive replay states tied to the roles for SAD22 visibility demonstration
    var driftStatus = 'safe_replay';
    var deviation = '';
    var adaptation = '';

    if (roleName === 'manager') {
      driftStatus = 'safe_replay';
      deviation = '&lt; 1% text similarity variance';
      adaptation = 'None required. Proceeding via exact match.';
    } else if (roleName === 'design') {
      driftStatus = 'drift_detected';
      deviation = 'DOM structure altered; unexpected modal overlay';
      adaptation = 'Replay halted. Flagging for intervention.';
    } else if (roleName === 'coder') {
      driftStatus = 'fallback_to_discover';
      deviation = 'CSS class names randomized (visual drift detected)';
      adaptation = 'Re-routing to probabilistic visual identification.';
    } else if (roleName === 'qa') {
      driftStatus = 'safe_replay';
      deviation = 'Exact signature match';
      adaptation = 'Validating deterministic execution traces.';
    } else {
      driftStatus = 'unknown_state';
      deviation = 'N/A';
      adaptation = 'Drift evaluation incomplete.';
    }

    var icon = '✅';
    var stateColor = '#10b981'; // green
    var bg = 'rgba(16,185,129,0.1)';
    var label = 'SAFE REPLAY';

    if (driftStatus === 'drift_detected') {
      icon = '⚠️';
      stateColor = '#ef4444'; // red
      bg = 'rgba(239,68,68,0.1)';
      label = 'DRIFT DETECTED';
    } else if (driftStatus === 'fallback_to_discover') {
      icon = '🔄';
      stateColor = '#f59e0b'; // amber
      bg = 'rgba(245,158,11,0.1)';
      label = 'FALLBACK TO DISCOVER';
    } else if (driftStatus === 'unknown_state') {
      icon = '❔';
      stateColor = '#94a3b8'; // gray
      bg = 'rgba(148,163,184,0.1)';
      label = 'UNKNOWN DRIFT STATE';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';">';
    html += '<strong style="color:var(--sb-text-muted);">Active Drift Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
    html += 'Replay Basis: <code>role-derived visible replay-safety contract</code><br/>';
    html += 'Drift Basis: <code>visible environment deviation for current role/run</code>';
    html += '</div>';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';display:flex;align-items:flex-start;gap:0.75rem;">';
    
    html += '<div style="font-size:1.4rem;line-height:1;">' + icon + '</div>';
    
    html += '<div style="flex:1;">';
    html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.2rem;">';
    html += '<div>';
    html += '<strong style="color:var(--sb-text-muted);">Replay Safety Evaluation:</strong> ';
    html += '</div>';
    html += '<code style="color:' + stateColor + ';background:' + bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + label + '</code>';
    html += '</div>';
    
    html += '<div style="display:flex;flex-direction:column;gap:0.2rem;margin-bottom:0.3rem;">';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Observed Deviation:</span> <span style="font-family:monospace;font-size:0.7rem;color:#818cf8;">' + deviation + '</span></div>';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">System Adaptation:</span> <span style="color:var(--sb-on-surface);">' + adaptation + '</span></div>';
    html += '</div>';

    html += '</div>'; // close text column
    html += '</div>'; // close surface

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'Adaptive Replay protects execution against environment non-stationarity natively without requiring retraining (Paper SI12).';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAR23: Hybrid Routing ──

  function updateWorkerRoutingState(appId, runId) {
    var panel = document.getElementById('dev-worker-routing-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    // Mock realistic routing states tied to the roles for SAR23 visibility demonstration
    var routingDecision = 'unknown';
    var costLatency = '';
    var justification = '';

    if (roleName === 'manager') {
      routingDecision = 'replay';
      costLatency = 'Zero Planning / Zero API Cost / Minimum Latency';
      justification = 'High confidence routing via exact deterministic playbook.';
    } else if (roleName === 'qa') {
      routingDecision = 'deterministic';
      costLatency = 'Zero API Cost / High Throughput';
      justification = 'Evaluating strict verification gates.';
    } else if (roleName === 'coder') {
      routingDecision = 'local_model';
      costLatency = 'Low API Cost / Local execution latency';
      justification = 'Safe code generation isolated to private inference.';
    } else if (roleName === 'design') {
      routingDecision = 'external_api';
      costLatency = 'High API Cost / Fallback latency';
      justification = 'Complex layout generation requires maximum semantic capability.';
    } else {
      routingDecision = 'unknown_state';
      costLatency = 'N/A';
      justification = 'Routing evaluation incomplete.';
    }

    var icon = '❓';
    var stateColor = '#94a3b8'; // gray
    var bg = 'rgba(148,163,184,0.1)';
    var label = 'UNKNOWN ROUTE';

    if (routingDecision === 'replay') {
      icon = '⏩';
      stateColor = '#10b981'; // green
      bg = 'rgba(16,185,129,0.1)';
      label = 'REPLAY (CONVENTION)';
    } else if (routingDecision === 'deterministic') {
      icon = '⚙️';
      stateColor = '#3b82f6'; // blue
      bg = 'rgba(59,130,246,0.1)';
      label = 'DETERMINISTIC PROCESS';
    } else if (routingDecision === 'local_model') {
      icon = '🧠';
      stateColor = '#8b5cf6'; // purple
      bg = 'rgba(139,92,246,0.1)';
      label = 'LOCAL MODEL (OSS)';
    } else if (routingDecision === 'external_api') {
      icon = '☁️';
      stateColor = '#f59e0b'; // amber
      bg = 'rgba(245,158,11,0.1)';
      label = 'EXTERNAL API FALLBACK';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';display:flex;align-items:flex-start;gap:0.75rem;">';
    
    html += '<div style="font-size:1.4rem;line-height:1;">' + icon + '</div>';
    
    html += '<div style="flex:1;">';
    html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.2rem;">';
    html += '<div>';
    html += '<strong style="color:var(--sb-text-muted);">Route Selection:</strong> ';
    html += '</div>';
    html += '<code style="color:' + stateColor + ';background:' + bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + label + '</code>';
    html += '</div>';
    
    html += '<div style="display:flex;flex-direction:column;gap:0.2rem;margin-bottom:0.3rem;">';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Cost &amp; Latency Profile:</span> <span style="font-family:monospace;font-size:0.7rem;color:#818cf8;">' + costLatency + '</span></div>';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Routing Justification:</span> <span style="color:var(--sb-on-surface);">' + justification + '</span></div>';
    html += '</div>';

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Routing Context:</strong><br/>';
    html += 'App ID: <code>' + (appId || 'unknown') + '</code><br/>';
    html += 'Role: <code>' + roleName + '</code><br/>';
    html += 'Run: <code>' + (runId || 'latest') + '</code><br/>';
    html += 'Routing Basis: <code>role-derived visible route selection</code><br/>';
    html += 'Cost Basis: <code>visible route-cost profile for current role/run</code>';
    html += '</div>';

    html += '</div>'; // close text column
    html += '</div>'; // close surface

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'Hybrid Routing allocates computation optimally across replay, deterministic, local, and external API modes (Paper SI13).';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAE24: Efficiency Metrics & Replay Rate ──

  function updateWorkerEfficiencyState(appId, runId) {
    var panel = document.getElementById('dev-worker-efficiency-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    // Mock realistic efficiency metrics tied to the roles for SAE24 visibility demonstration
    var sysProfile = 'Unknown Profile';
    var replayRate = 'N/A';
    var computeEconomics = 'N/A';
    var executionLatency = 'N/A';
    var summaryText = 'Efficiency metrics evaluation incomplete.';

    if (roleName === 'manager') {
      sysProfile = 'Replay Heavy';
      replayRate = '92%';
      computeEconomics = '-95% vs Discover (Ripple Avoided)';
      executionLatency = '&lt; 50ms (Zero Planning)';
      summaryText = 'Highly mature execution. System functioning efficiently operating on Stillwater.';
    } else if (roleName === 'qa') {
      sysProfile = 'Deterministic Verification';
      replayRate = '100%';
      computeEconomics = '-99% vs API (Pure Compute)';
      executionLatency = '&lt; 10ms (Local Binary)';
      summaryText = 'Zero orchestration overhead. Evaluating strict boolean gates.';
    } else if (roleName === 'coder') {
      sysProfile = 'Mixed (Local + Replay)';
      replayRate = '65%';
      computeEconomics = '-75% vs API (OSS Local Model)';
      executionLatency = '~ 2.5s (Local Inference)';
      summaryText = 'Caching constraints preventing API ripple. System learning.';
    } else if (roleName === 'design') {
      sysProfile = 'Discover Heavy (Ripple)';
      replayRate = '12%';
      computeEconomics = 'Baseline (Max API Payload)';
      executionLatency = '~ 14.0s (External Model Wait)';
      summaryText = 'Expensive orchestration phase. Uncached convention building.';
    }

    var icon = '📉';
    var stateColor = '#94a3b8'; // gray
    var bg = 'rgba(148,163,184,0.1)';

    if (sysProfile.indexOf('Replay') > -1 || sysProfile.indexOf('Deterministic') > -1) {
      icon = '📈';
      stateColor = '#10b981'; // green
      bg = 'rgba(16,185,129,0.1)';
    } else if (sysProfile.indexOf('Mixed') > -1) {
      icon = '⚖️';
      stateColor = '#3b82f6'; // blue
      bg = 'rgba(59,130,246,0.1)';
    } else if (sysProfile.indexOf('Discover') > -1) {
      icon = '💸';
      stateColor = '#f59e0b'; // amber
      bg = 'rgba(245,158,11,0.1)';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';display:flex;align-items:flex-start;gap:0.75rem;">';
    
    html += '<div style="font-size:1.4rem;line-height:1;">' + icon + '</div>';
    
    html += '<div style="flex:1;">';
    html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.2rem;">';
    html += '<div>';
    html += '<strong style="color:var(--sb-text-muted);">System Economics Profile:</strong> ';
    html += '</div>';
    html += '<code style="color:' + stateColor + ';background:' + bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(sysProfile) + '</code>';
    html += '</div>';
    
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;margin-bottom:0.4rem;">';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Replay Rate:</span> <span style="font-family:monospace;font-size:0.75rem;color:' + stateColor + ';">' + replayRate + '</span></div>';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Execution Latency:</span> <span style="font-family:monospace;font-size:0.7rem;color:#e2e8f0;">' + executionLatency + '</span></div>';
    html += '<div style="grid-column: span 2;"><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Compute Economics:</span> <span style="font-family:monospace;font-size:0.7rem;color:#818cf8;">' + computeEconomics + '</span></div>';
    html += '</div>';

    html += '<div style="padding-top:0.3rem;border-top:1px solid rgba(255,255,255,0.05);">';
    html += '<span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Summary:</span> <span style="color:var(--sb-on-surface);font-size:0.7rem;">' + escapeHtml(summaryText) + '</span>';
    html += '</div>';

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Efficiency Context:</strong><br/>';
    html += 'App ID: <code>' + (appId || 'unknown') + '</code><br/>';
    html += 'Role: <code>' + roleName + '</code><br/>';
    html += 'Run: <code>' + (runId || 'latest') + '</code><br/>';
    html += 'Efficiency Basis: <code>role-derived visible replay-rate and route economics</code><br/>';
    html += 'Latency Basis: <code>visible execution-latency profile for current role/run</code>';
    html += '</div>';

    html += '</div>'; // close text column
    html += '</div>'; // close surface

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'Solace evaluates execution maturity by converting Discover computations (Ripple) into efficient Replay memory (Stillwater) (Paper SI19).';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  window.__solaceCopyInspectionLink = function() {
    var input = document.getElementById('dev-context-link');
    var btn = document.getElementById('dev-copy-link-btn');
    if (!input) return;
    var link = input.value;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(link).then(function() {
        if (btn) { btn.textContent = '✓ copied'; setTimeout(function() { btn.textContent = '📋 copy link'; }, 1500); }
      }).catch(function() {
        fallbackCopy(input, btn);
      });
    } else {
      fallbackCopy(input, btn);
    }
  };

  function fallbackCopy(input, btn) {
    input.select();
    try {
      document.execCommand('copy');
      if (btn) { btn.textContent = '✓ copied'; setTimeout(function() { btn.textContent = '📋 copy link'; }, 1500); }
    } catch(e) {}
  }

  function roleColor(key) {
    var colors = { manager: '#d946ef', design: '#3b82f6', coder: '#10b981', qa: '#f59e0b' };
    return colors[key] || '#94a3b8';
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
      html += '<a href="/api/v1/apps/' + appId + '/runs/' + runId + '/artifact/report.html" target="_blank" style="color:#818cf8;">open report.html →</a>';
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

    // First-class artifact links (SDA8)
    html += '<div style="margin-top:0.4rem;display:flex;gap:0.3rem;flex-wrap:wrap;">';
    if (runId) {
      var artifactBase = '/api/v1/apps/' + appId + '/runs/' + runId + '/artifact/';
      html += '<a href="/apps/' + appId + '/runs/' + runId + '" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">run detail</a>';
      html += '<a href="' + artifactBase + 'report.html" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">report.html</a>';
      html += '<a href="' + artifactBase + 'payload.json" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">payload.json</a>';
      html += '<a href="' + artifactBase + 'stillwater.json" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">stillwater.json</a>';
      html += '<a href="' + artifactBase + 'events.jsonl" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">events.jsonl</a>';
      html += '<a href="/api/v1/apps/' + appId + '/runs/' + runId + '/events" target="_blank" class="sb-btn sb-btn--sm" style="font-size:0.65rem;padding:0.2rem 0.4rem;">events API</a>';
    }
    html += '</div>';
    html += '</div>';
    return html;
  }

  // Render inspection into the panel + trigger artifact previews
  function showRunInspection(appId, runId, reportPath, eventsData, statusOk) {
    var panel = document.getElementById('dev-run-inspection');
    if (!panel) return;
    panel.innerHTML = buildRunInspectionHTML(appId, runId, reportPath, eventsData, statusOk);
    panel.style.display = 'block';

    // Trigger native artifact previews (SAV9)
    if (runId) {
      hydrateArtifactPreviews(appId, runId);
    }
  }

  // ── SAV9: Workspace-Native Artifact Previews ──

  function artifactUrl(appId, runId, filename) {
    return API + '/api/v1/apps/' + appId + '/runs/' + runId + '/artifact/' + filename;
  }

  function hydrateArtifactPreviews(appId, runId) {
    var previewPanel = document.getElementById('dev-artifact-previews');
    if (!previewPanel) return;

    previewPanel.style.display = 'block';
    previewPanel.innerHTML =
      '<p class="sb-kicker" style="margin-bottom:0.5rem;">Artifact Previews</p>' +
      '<p style="font-size:0.7rem;color:var(--sb-text-muted);">' + appId + ' / ' + runId + '</p>' +
      '<div id="preview-payload" class="sav9-preview-slot" style="margin-top:0.5rem;"><span style="font-size:0.7rem;color:#94a3b8;">loading payload.json…</span></div>' +
      '<div id="preview-events" class="sav9-preview-slot" style="margin-top:0.5rem;"><span style="font-size:0.7rem;color:#94a3b8;">loading events.jsonl…</span></div>' +
      '<div id="preview-report" class="sav9-preview-slot" style="margin-top:0.5rem;"><span style="font-size:0.7rem;color:#94a3b8;">loading report…</span></div>';

    // Preview 1: payload.json
    fetchArtifactText(appId, runId, 'payload.json').then(function(result) {
      var slot = document.getElementById('preview-payload');
      if (!slot) return;
      if (result.missing) {
        slot.innerHTML = buildMissingState('payload.json', result.reason);
      } else {
        slot.innerHTML = buildPayloadPreview(result.text, appId, runId);
      }
    });

    // Preview 2: events.jsonl
    fetchArtifactText(appId, runId, 'events.jsonl').then(function(result) {
      var slot = document.getElementById('preview-events');
      if (!slot) return;
      if (result.missing) {
        slot.innerHTML = buildMissingState('events.jsonl', result.reason);
      } else {
        slot.innerHTML = buildEventsPreview(result.text, appId, runId);
      }
    });

    // Preview 3: report.html (summary only — not full render)
    fetchArtifactText(appId, runId, 'report.html').then(function(result) {
      var slot = document.getElementById('preview-report');
      if (!slot) return;
      if (result.missing) {
        slot.innerHTML = buildMissingState('report.html', result.reason);
      } else {
        slot.innerHTML = buildReportPreview(result.text, appId, runId);
      }
    });
  }

  function fetchArtifactText(appId, runId, filename) {
    return fetch(artifactUrl(appId, runId, filename))
      .then(function(r) {
        if (r.status === 404) return { missing: true, reason: 'not found in outbox' };
        if (r.status === 403) return { missing: true, reason: 'not in whitelist' };
        if (!r.ok) return { missing: true, reason: 'HTTP ' + r.status };
        return r.text().then(function(t) { return { missing: false, text: t }; });
      })
      .catch(function(err) {
        return { missing: true, reason: 'fetch error: ' + err.message };
      });
  }

  function buildMissingState(filename, reason) {
    return '<div style="border-left:2px solid #475569;padding:0.3rem 0.6rem;background:rgba(71,85,105,0.08);border-radius:0 0.25rem 0.25rem 0;">' +
      '<strong style="font-size:0.7rem;color:var(--sb-text-muted);">' + filename + '</strong> ' +
      '<span class="sb-pill" style="background:#1e293b;color:#94a3b8;font-size:0.6rem;">missing</span>' +
      '<div style="font-size:0.65rem;color:#64748b;margin-top:0.15rem;">' + reason + '</div>' +
      '</div>';
  }

  function buildPayloadPreview(text, appId, runId) {
    var truncated = text.length > 1200 ? text.slice(0, 1200) + '\n...(truncated)' : text;
    var keyCount = 0;
    try { keyCount = Object.keys(JSON.parse(text)).length; } catch(e) {}
    return '<div style="border-left:2px solid #6366f1;padding:0.3rem 0.6rem;background:rgba(99,102,241,0.06);border-radius:0 0.25rem 0.25rem 0;">' +
      '<div style="display:flex;gap:0.3rem;align-items:center;">' +
      '<strong style="font-size:0.7rem;color:var(--sb-on-surface);">payload.json</strong> ' +
      '<span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.6rem;">' + (text.length > 1024 ? Math.round(text.length/1024) + 'KB' : text.length + 'B') + '</span>' +
      (keyCount ? ' <span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.6rem;">' + keyCount + ' keys</span>' : '') +
      '</div>' +
      '<details style="margin-top:0.25rem;"><summary style="cursor:pointer;font-size:0.65rem;color:var(--sb-text-muted);">show payload</summary>' +
      '<pre style="font-size:0.6rem;background:var(--sb-surface-alt,#0f172a);padding:0.4rem;border-radius:0.25rem;max-height:200px;overflow-y:auto;margin-top:0.2rem;white-space:pre-wrap;word-break:break-all;">' +
      escapeHtml(truncated) + '</pre></details></div>';
  }

  function buildEventsPreview(text, appId, runId) {
    var lines = text.trim().split('\n').filter(function(l) { return l.trim(); });
    var total = lines.length;
    var tail = lines.slice(-5);
    var preview = '';
    tail.forEach(function(line) {
      try {
        var ev = JSON.parse(line);
        var ts = (ev.timestamp || '').slice(11, 19);
        var type = ev.event_type || ev.type || '?';
        var detail = ev.detail || ev.metadata || '';
        preview += ts + ' [' + type + '] ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) + '\n';
      } catch(e) {
        preview += line.slice(0, 120) + '\n';
      }
    });
    return '<div style="border-left:2px solid #10b981;padding:0.3rem 0.6rem;background:rgba(16,185,129,0.06);border-radius:0 0.25rem 0.25rem 0;">' +
      '<div style="display:flex;gap:0.3rem;align-items:center;">' +
      '<strong style="font-size:0.7rem;color:var(--sb-on-surface);">events.jsonl</strong> ' +
      '<span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.6rem;">' + total + ' events</span>' +
      '</div>' +
      '<pre style="font-size:0.6rem;background:var(--sb-surface-alt,#0f172a);padding:0.4rem;border-radius:0.25rem;max-height:120px;overflow-y:auto;margin-top:0.25rem;">' +
      escapeHtml(preview) + '</pre></div>';
  }

  function buildReportPreview(text, appId, runId) {
    // Extract title from <title>...</title>
    var titleMatch = text.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    var title = titleMatch ? titleMatch[1].trim() : 'Untitled Report';
    var sizeKB = Math.round(text.length / 1024);
    return '<div style="border-left:2px solid #f59e0b;padding:0.3rem 0.6rem;background:rgba(245,158,11,0.06);border-radius:0 0.25rem 0.25rem 0;">' +
      '<div style="display:flex;gap:0.3rem;align-items:center;">' +
      '<strong style="font-size:0.7rem;color:var(--sb-on-surface);">report.html</strong> ' +
      '<span class="sb-pill" style="background:#1e293b;color:#e2e8f0;font-size:0.6rem;">' + sizeKB + 'KB</span>' +
      '</div>' +
      '<div style="font-size:0.65rem;color:var(--sb-text-muted);margin-top:0.15rem;">' + escapeHtml(title) + '</div>' +
      '<details style="margin-top:0.25rem;"><summary style="cursor:pointer;font-size:0.65rem;color:var(--sb-text-muted);">preview report</summary>' +
      '<iframe sandbox="" srcdoc="' + escapeAttr(text) + '" style="width:100%;height:200px;border:1px solid var(--sb-border,#334155);border-radius:0.25rem;margin-top:0.2rem;background:#fff;"></iframe>' +
      '</details></div>';
  }

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function escapeAttr(s) {
    return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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
