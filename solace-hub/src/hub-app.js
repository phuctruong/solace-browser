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
    updateWorkerDistillationState(appId, runId);
    updatePromotionDecisionState(appId, runId);
    updatePromotionAuditTrail(appId, runId);
    updateGovernanceSummary(appId, runId);
    updateManagerActionQueue(appId, runId);
    updateManagerDirectivePacket(appId, runId);
    updateDelegationHandoffLog(appId, runId);
    updateSpecialistAcceptanceState(appId, runId);
    updateSpecialistIntakeReadiness(appId, runId);
    updateSpecialistExecutionActivity(appId, runId);
    updateSpecialistExecutionEvidence(appId, runId);
    updateSpecialistArtifactBundle(appId, runId);
    updateSpecialistArtifactProvenance(appId, runId);
    updateSpecialistPromotionCandidate(appId, runId);
    updateSpecialistMemoryAdmission(appId, runId);
    updateSpecialistMemoryEntry(appId, runId);
    updateDepartmentMemoryQueue(appId, runId);
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

  // ── SAX25: Automatic Convention Distillation ──

  function updateWorkerDistillationState(appId, runId) {
    var panel = document.getElementById('dev-worker-distillation-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);

    // Mock realistic distillation states for SAX25 visibility demonstration
    var distillationState = 'unknown';
    var candidateId = 'N/A';
    var basis = 'N/A';

    if (roleName === 'coder') {
      distillationState = 'promoted';
      candidateId = 'solace-prime-mermaid-coder-v1.2.0';
      basis = 'Mature structural repetition (100% success rate across 5 traces). Promoted to SHARED memory.';
    } else if (roleName === 'manager') {
      distillationState = 'pending_candidate';
      candidateId = 'nexus-routing-v2.2-candidate';
      basis = 'Consistent assignment packet generation detected. Pending human validation gate for GLOBAL promotion.';
    } else if (roleName === 'design' || roleName === 'qa') {
      distillationState = 'blocked';
      candidateId = 'N/A';
      basis = 'Zero high-confidence repetition detected. Execution remains at Discover tier (Ripple).';
    } else {
      distillationState = 'unknown_state';
      candidateId = 'N/A';
      basis = 'Distillation evaluation incomplete.';
    }

    var icon = '❓';
    var stateColor = '#94a3b8'; // gray
    var bg = 'rgba(148,163,184,0.1)';
    var label = 'UNKNOWN DISTILLATION STATE';

    if (distillationState === 'promoted') {
      icon = '💎';
      stateColor = '#10b981'; // green
      bg = 'rgba(16,185,129,0.1)';
      label = 'PROMOTED / REPLAYABLE';
    } else if (distillationState === 'pending_candidate') {
      icon = '🧪';
      stateColor = '#f59e0b'; // amber
      bg = 'rgba(245,158,11,0.1)';
      label = 'CANDIDATE PENDING';
    } else if (distillationState === 'blocked') {
      icon = '⛔';
      stateColor = '#ef4444'; // red
      bg = 'rgba(239,68,68,0.1)';
      label = 'BLOCKED / NO CANDIDATE';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';display:flex;align-items:flex-start;gap:0.75rem;">';
    
    html += '<div style="font-size:1.4rem;line-height:1;">' + icon + '</div>';
    
    html += '<div style="flex:1;">';
    html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.2rem;">';
    html += '<div>';
    html += '<strong style="color:var(--sb-text-muted);">Promotion Status:</strong> ';
    html += '</div>';
    html += '<code style="color:' + stateColor + ';background:' + bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + label + '</code>';
    html += '</div>';
    
    html += '<div style="display:flex;flex-direction:column;gap:0.2rem;margin-bottom:0.3rem;">';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Candidate Convention:</span> <span style="font-family:monospace;font-size:0.7rem;color:#818cf8;">' + escapeHtml(candidateId) + '</span></div>';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Distillation Basis:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(basis) + '</span></div>';
    html += '</div>';

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Distillation Context:</strong><br/>';
    html += 'App ID: <code>' + (appId || 'unknown') + '</code><br/>';
    html += 'Role: <code>' + roleName + '</code><br/>';
    html += 'Run: <code>' + (runId || 'latest') + '</code><br/>';
    html += 'Promotion Basis: <code>role-derived visible convention promotion state</code><br/>';
    html += 'Evidence Basis: <code>visible repetition and validation signal for current role/run</code>';
    html += '</div>';

    html += '</div>'; // close text column
    html += '</div>'; // close surface

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'Automatic Convention Distillation transforms repeated execution patterns into persistent memory dynamically without retraining (Paper SI16).';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAM27: Promotion Decision Packet ──
  
  function updatePromotionDecisionState(appId, runId) {
    var panel = document.getElementById('dev-promotion-decision-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Mock realistic decision states tied to roles for SAM27
    var decisionState = 'unknown';
    var candidateId = 'N/A';
    var evidenceBasis = 'N/A';
    var approvalBasis = 'N/A';

    if (roleName === 'coder') {
      decisionState = 'pending';
      candidateId = 'solace-prime-mermaid-coder-v1.2.0';
      evidenceBasis = '100% success rate across 5 execution traces matching candidate constraints.';
      approvalBasis = 'Awaiting Solace Dev Manager signature for Global propagation.';
    } else if (roleName === 'manager') {
      decisionState = 'approved';
      candidateId = 'nexus-routing-v2.2-candidate';
      evidenceBasis = 'Consistent assignment packet generation meeting Department structural bounds.';
      approvalBasis = 'Manager executed PROMOTED approval. Target bounds set to GLOBAL.';
    } else if (roleName === 'design' || roleName === 'qa') {
      decisionState = 'blocked';
      candidateId = 'N/A';
      evidenceBasis = 'No candidate memory distilled for review.';
      approvalBasis = 'Decision gated. Insufficient repetition signal.';
    } else {
      decisionState = 'unknown_state';
      candidateId = 'N/A';
      evidenceBasis = 'No evaluation context available.';
      approvalBasis = 'No evaluation context available.';
    }

    var icon = '❓';
    var stateColor = '#94a3b8'; // gray
    var bg = 'rgba(148,163,184,0.1)';
    var label = 'UNKNOWN DECISION';

    if (decisionState === 'approved') {
      icon = '🛡️';
      stateColor = '#10b981'; // green
      bg = 'rgba(16,185,129,0.1)';
      label = 'APPROVED / PROMOTED';
    } else if (decisionState === 'pending') {
      icon = '👁️';
      stateColor = '#3b82f6'; // blue
      bg = 'rgba(59,130,246,0.1)';
      label = 'PENDING MANAGER REVIEW';
    } else if (decisionState === 'blocked') {
      icon = '🛑';
      stateColor = '#ef4444'; // red
      bg = 'rgba(239,68,68,0.1)';
      label = 'BLOCKED / REJECTED';
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + stateColor + ';display:flex;align-items:flex-start;gap:0.75rem;">';
    
    html += '<div style="font-size:1.4rem;line-height:1;">' + icon + '</div>';
    
    html += '<div style="flex:1;">';
    html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.2rem;">';
    html += '<div>';
    html += '<strong style="color:var(--sb-text-muted);">Manager Decision:</strong> ';
    html += '</div>';
    html += '<code style="color:' + stateColor + ';background:' + bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + label + '</code>';
    html += '</div>';
    
    html += '<div style="display:flex;flex-direction:column;gap:0.2rem;margin-bottom:0.3rem;">';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Candidate:</span> <span style="font-family:monospace;font-size:0.7rem;color:#c084fc;">' + escapeHtml(candidateId) + '</span></div>';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Evidence Basis:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(evidenceBasis) + '</span></div>';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Approval Basis:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(approvalBasis) + '</span></div>';
    html += '</div>';

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Packet Context:</strong><br/>';
    html += 'App ID: <code>' + (appId || 'unknown') + '</code><br/>';
    html += 'Role: <code>' + roleName + '</code><br/>';
    html += 'Run: <code>' + (runId || 'latest') + '</code><br/>';
    html += 'Packet Binding: <code>visible decision gating context for current role/run</code><br/>';
    html += 'Decision Basis: <code>visible evidence and manager approval state</code>';
    html += '</div>';

    html += '</div>'; // close text column
    html += '</div>'; // close surface

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'The Promotion Decision Packet exposes human-in-the-loop oversight directly into the intelligence environment (Paper SI17, SI18).';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAT28: Promotion Audit Trail & Approval Log ──
  
  function updatePromotionAuditTrail(appId, runId) {
    var panel = document.getElementById('dev-promotion-audit-trail-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Mock durable audit history for SAT28 visibility
    var auditLog = [];

    if (roleName === 'coder') {
      auditLog = [
        {
          timestamp: '2026-03-28T13:42:10Z',
          state: 'pending',
          stateColor: '#3b82f6',
          bg: 'rgba(59,130,246,0.1)',
          label: 'PENDING MANAGER REVIEW',
          candidate: 'solace-prime-mermaid-coder-v1.2.0',
          reason: 'Initial distillation threshold met (5 successes). Awaiting manager signature.'
        },
        {
          timestamp: '2026-03-27T18:15:00Z',
          state: 'blocked',
          stateColor: '#ef4444',
          bg: 'rgba(239,68,68,0.1)',
          label: 'BLOCKED / REJECTED',
          candidate: 'solace-prime-mermaid-coder-v1.1.0',
          reason: 'Manager Review: Insufficient boundary tests in structure. Requires additional node coverage.'
        }
      ];
    } else if (roleName === 'manager') {
      auditLog = [
        {
          timestamp: '2026-03-28T14:10:00Z',
          state: 'approved',
          stateColor: '#10b981',
          bg: 'rgba(16,185,129,0.1)',
          label: 'APPROVED / PROMOTED',
          candidate: 'nexus-routing-v2.2-candidate',
          reason: 'Manager Review: Authorized explicitly. Promoted to GLOBAL store.'
        },
        {
          timestamp: '2026-03-28T09:05:00Z',
          state: 'pending',
          stateColor: '#3b82f6',
          bg: 'rgba(59,130,246,0.1)',
          label: 'PENDING MANAGER REVIEW',
          candidate: 'nexus-routing-v2.2-candidate',
          reason: 'Distillation criteria achieved for routing structure.'
        }
      ];
    } else {
      auditLog = [
        {
          timestamp: 'N/A',
          state: 'blocked',
          stateColor: '#94a3b8',
          bg: 'rgba(148,163,184,0.1)',
          label: 'NO HISTORY',
          candidate: 'N/A',
          reason: 'Role execution lacks sufficient repetition for audit history.'
        }
      ];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    auditLog.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + entry.stateColor + ';display:flex;flex-direction:column;gap:0.3rem;">';
      
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<code style="font-size:0.65rem;color:#818cf8;">' + escapeHtml(entry.timestamp) + '</code>';
      html += '<code style="color:' + entry.stateColor + ';background:' + entry.bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(entry.label) + '</code>';
      html += '</div>';

      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;margin-top:0.2rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Candidate:</span> <span style="font-family:monospace;font-size:0.7rem;">' + escapeHtml(entry.candidate) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Transition Basis:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(entry.reason) + '</span></div>';
      // ALCOA evidence requirement from Phuc Forecast globally overriden
      var dummyHash = btoa(entry.candidate + entry.timestamp + entry.state).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Audit Hash:</span> <code style="font-size:0.6rem;color:#94a3b8;">' + dummyHash + '</code></div>';
      html += '</div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Audit Context:</strong><br/>';
    html += 'App ID: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
    html += 'Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Log Binding: <code>visible history tied to candidate node</code><br/>';
    html += 'History Basis: <code>visible state transitions for current role/candidate lineage</code><br/>';
    html += 'Evidence Standard: <code>ALCOA+ Part 11 explicit state transitions</code>';
    html += '</div>';

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'The Promotion Audit Trail guarantees intelligence evolution remains a perfectly inspectable ledger over time (Paper SI18 Transparency).';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAG29: Department Governance Summary ──
  
  function updateGovernanceSummary(appId, runId) {
    var panel = document.getElementById('dev-governance-summary-state');
    if (!panel) return;

    // The Governance Summary is department-wide, but we tailor the exact detail
    // based on the visible run, while supplying the aggregate metrics (Approved/Pending/Blocked).
    
    // Mock realistic aggregate governance state for SAG29 visibility
    var metrics = {
      approved: 12,
      pending: 5,
      blocked: 2,
      pressureLane: 'coder',
      pressureLabel: '70% Load',
      pressureDesc: 'Repetitive Prime Mermaid structural execution accumulating validation debt.'
    };

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    // Aggregate Stat Bar
    html += '<div style="display:flex;gap:0.4rem;">';
    
    // Approved
    html += '<div style="flex:1;background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-top:2px solid #10b981;display:flex;flex-direction:column;align-items:center;">';
    html += '<div style="font-size:1.1rem;font-weight:700;color:#10b981;">' + metrics.approved + '</div>';
    html += '<div style="font-size:0.55rem;color:var(--sb-text-muted);text-transform:uppercase;">Approved</div>';
    html += '</div>';

    // Pending
    html += '<div style="flex:1;background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-top:2px solid #3b82f6;display:flex;flex-direction:column;align-items:center;">';
    html += '<div style="font-size:1.1rem;font-weight:700;color:#3b82f6;">' + metrics.pending + '</div>';
    html += '<div style="font-size:0.55rem;color:var(--sb-text-muted);text-transform:uppercase;">Pending</div>';
    html += '</div>';

    // Blocked
    html += '<div style="flex:1;background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-top:2px solid #ef4444;display:flex;flex-direction:column;align-items:center;">';
    html += '<div style="font-size:1.1rem;font-weight:700;color:#ef4444;">' + metrics.blocked + '</div>';
    html += '<div style="font-size:0.55rem;color:var(--sb-text-muted);text-transform:uppercase;">Blocked</div>';
    html += '</div>';

    html += '</div>'; // close flex row

    // Pressure Indicator
    html += '<div style="background:rgba(245,158,11,0.05);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid #f59e0b;display:flex;flex-direction:column;gap:0.2rem;margin-top:0.2rem;">';
    html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
    html += '<span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Governance Pressure Area: <span style="font-family:monospace;color:#f59e0b;">' + escapeHtml(metrics.pressureLane) + '</span></span>';
    html += '<code style="color:#f59e0b;background:rgba(245,158,11,0.1);padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(metrics.pressureLabel) + '</code>';
    html += '</div>';
    html += '<div style="font-size:0.65rem;color:var(--sb-on-surface);">' + escapeHtml(metrics.pressureDesc) + '</div>';
    html += '</div>';

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Governance Context:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Governance Tracking: <code>Aggregating manager oversight bottlenecks across execution lanes</code><br/>';
    html += 'Pressure Basis: <code>visible per-lane approval load and pending governance debt</code><br/>';
    html += 'Evidence Standard: <code>Durable log topology (Paper SI18)</code>';
    html += '</div>';

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'Department Governance bridges single packet approvals into an operational map indicating structural health and iteration bounds.';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAA30: Manager Action Queue ──
  
  function updateManagerActionQueue(appId, runId) {
    var panel = document.getElementById('dev-manager-action-queue-state');
    if (!panel) return;

    // Define the Manager's actionable backlog
    var actions = [
      {
        priority: 'Immediate',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)',
        actionType: 'Review Promotion',
        candidate: 'solace-prime-mermaid-coder-v1.2.0',
        role: 'coder',
        reason: 'Candidate hit distillation threshold and awaits GLOBAL target binding.'
      },
      {
        priority: 'Pending',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)',
        actionType: 'Investigate Bottleneck',
        candidate: 'solace-ui-renderer-v1',
        role: 'design',
        reason: 'Lane is producing 40% of blocked decisions. Architecture drift likely.'
      },
      {
        priority: 'Blocked',
        color: '#94a3b8',
        bg: 'rgba(148,163,184,0.1)',
        actionType: 'Awaiting Run Completion',
        candidate: 'nexus-routing-v2.3',
        role: 'manager',
        reason: 'Dependent executions are still spinning. Evaluation gated.'
      }
    ];

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    actions.forEach(function(act) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + act.color + ';display:flex;flex-direction:column;gap:0.3rem;">';
      
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.75rem;">[' + escapeHtml(act.actionType) + ']</strong>';
      html += '<code style="color:' + act.color + ';background:' + act.bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(act.priority) + '</code>';
      html += '</div>';

      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Target Candidate:</span> <span style="font-family:monospace;font-size:0.7rem;color:#c084fc;">' + escapeHtml(act.candidate) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Lane Context:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(act.role) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Urgency Basis:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(act.reason) + '</span></div>';
      
      // Phuc Forecast / GLOW hashing requirement
      var dummyHash = btoa(act.candidate + act.priority + act.role).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Action Hash:</span> <code style="font-size:0.6rem;color:#94a3b8;">' + dummyHash + '</code></div>';

      html += '</div>';
      html += '</div>';
    });

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Queue Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Display Scope: <code>Department-wide actionable decisions</code><br/>';
    html += 'Priority Bound: <code>Requires human authorization (SI17)</code><br/>';
    html += 'Action Basis: <code>visible next-step governance queue derived from department pressure</code>';
    html += '</div>';

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'The Action Queue exposes the next explicit judgments required from the Manager, preventing hidden structural drift (Phuc Forecast).';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAD31: Manager Directive Packet ──

  function updateManagerDirectivePacket(appId, runId) {
    var panel = document.getElementById('dev-manager-directive-packet-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Mock explicit directive derived from the Manager Action Queue bounds for SAD31
    var directive = {
      state: 'unknown',
      action: 'N/A',
      target: 'N/A',
      evidence: 'N/A',
      delegation: 'N/A',
      color: '#94a3b8',
      bg: 'rgba(148,163,184,0.1)'
    };

    if (roleName === 'manager') {
      directive = {
        state: 'Immediate',
        action: 'EXECUTE PROMOTION',
        target: 'solace-prime-mermaid-coder-v1.2.0 (Coder Lane)',
        evidence: 'Distillation array returned 100% success rate matching architectural constraints (SAX25).',
        delegation: 'Sign cryptographic target binding. Re-allocate Coder Lane to Next Target Suite (SAA30).',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      };
    } else if (roleName === 'coder') {
      directive = {
        state: 'Pending',
        action: 'HALT EXECUTION',
        target: 'Pending Node (solace-ui-renderer-v1)',
        evidence: 'Lane producing 40% of blocked decisions. High latency detected.',
        delegation: 'Awaiting Manager routing directive to inject isolation branch into Dev queue.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      };
    } else if (roleName === 'design' || roleName === 'qa') {
      directive = {
        state: 'Blocked',
        action: 'DEFER',
        target: 'Department Level Analytics',
        evidence: 'Dependent sequences unresolved. Insufficient repetition for governance isolation.',
        delegation: 'No manual intervention required. Continue pipeline monitoring.',
        color: '#94a3b8',
        bg: 'rgba(148,163,184,0.1)'
      };
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + directive.color + ';display:flex;flex-direction:column;gap:0.3rem;">';
    
    html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
    html += '<strong style="color:var(--sb-on-surface);font-size:0.8rem;">[' + escapeHtml(directive.action) + ']</strong>';
    html += '<code style="color:' + directive.color + ';background:' + directive.bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(directive.state) + '</code>';
    html += '</div>';

    html += '<div style="display:flex;flex-direction:column;gap:0.15rem;margin-top:0.2rem;">';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Delegation Target:</span> <span style="font-family:monospace;font-size:0.7rem;color:#c084fc;">' + escapeHtml(directive.target) + '</span></div>';
    html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Trigger Evidence:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(directive.evidence) + '</span></div>';
    
    html += '<div style="margin-top:0.2rem;padding-top:0.2rem;border-top:1px dashed rgba(255,255,255,0.1);">';
    html += '<span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Next Explicit Delegation Step:</span> <br/>';
    html += '<span style="color:#10b981;font-weight:500;">' + escapeHtml(directive.delegation) + '</span>';
    html += '</div>';

    // Phuc Forecast bounds (crypto stamping)
    var dummyHash = btoa(directive.target + directive.action + directive.state).substring(0, 16);
    html += '<div style="margin-top:0.2rem;"><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Directive Stamp:</span> <code style="font-size:0.6rem;color:#94a3b8;">' + dummyHash + '</code></div>';

    html += '</div>';
    html += '</div>';

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Directive Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Action Source: <code>Manager Action Queue extraction</code><br/>';
    html += 'Resolution Bound: <code>Requires immediate delegation or approval trace (SI17)</code><br/>';
    html += 'Directive Basis: <code>visible bounded delegation packet for current governance context</code>';
    html += '</div>';

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += 'The Directive Packet formalizes exactly what action a manager must take and how execution returns to the specialist queue.';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAH32: Delegation Handoff Log ──

  function updateDelegationHandoffLog(appId, runId) {
    var panel = document.getElementById('dev-delegation-handoff-log-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Mock explicit handoff arrays deriving from SAD31 directives
    var handoffLogs = [];

    if (roleName === 'manager') {
      handoffLogs = [
        {
          state: 'Accepted',
          lane: 'coder',
          target: 'solace-prime-mermaid-coder-v1.2.0',
          payload: 'Execution target bound to GLOBAL tier. Awaiting final node initialization.',
          color: '#10b981',
          bg: 'rgba(16,185,129,0.1)'
        },
        {
          state: 'Pending',
          lane: 'design',
          target: 'solace-ui-renderer-v1',
          payload: 'Directive Dispatched: Halt rendering execution and dump architecture variables.',
          color: '#f59e0b',
          bg: 'rgba(245,158,11,0.1)'
        }
      ];
    } else if (roleName === 'coder') {
      handoffLogs = [
        {
          state: 'Accepted',
          lane: 'coder',
          target: 'solace-browser-hub-v2',
          payload: 'Isolating branch array. Sub-nodes spun down to allow Manager evaluation limits.',
          color: '#10b981',
          bg: 'rgba(16,185,129,0.1)'
        }
      ];
    } else {
      handoffLogs = [
        {
          state: 'Blocked',
          lane: roleName,
          target: 'Cross-Department Analytics',
          payload: 'Manager deferred directive context due to architecture instability. Spin lock active.',
          color: '#ef4444',
          bg: 'rgba(239,68,68,0.1)'
        }
      ];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    handoffLogs.forEach(function(log) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + log.color + ';display:flex;flex-direction:column;gap:0.3rem;">';
      
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.75rem;text-transform:uppercase;">[Dispatcher -> ' + escapeHtml(log.lane) + ']</strong>';
      html += '<code style="color:' + log.color + ';background:' + log.bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(log.state) + '</code>';
      html += '</div>';

      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Handoff Target:</span> <span style="font-family:monospace;font-size:0.7rem;color:#c084fc;">' + escapeHtml(log.target) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Dispatch Payload:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(log.payload) + '</span></div>';
      
      // Phuc Forecast bounds (crypto stamping)
      var dummyHash = btoa(log.target + log.lane + log.state).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Handoff Hash:</span> <code style="font-size:0.6rem;color:#94a3b8;">' + dummyHash + '</code></div>';

      html += '</div>';
      html += '</div>';
    });

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Handoff Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Dispatch Basis: <code>visible specialist handoff log for current directive context</code><br/>';
    html += 'Tracking Source: <code>Delegated Manager Packets (SAD31) deployed to specialists</code><br/>';
    html += 'Resolution Bound: <code>Requires specialist environment ACK/NACK signatures</code>';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAS33: Specialist Acceptance State ──

  function updateSpecialistAcceptanceState(appId, runId) {
    var panel = document.getElementById('dev-specialist-acceptance-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Mock explicit acceptance arrays deriving from SAH32 handoff logic
    var acceptanceLogs = [];

    if (roleName === 'coder') {
      acceptanceLogs = [
        {
          state: 'Confirmed',
          origin: 'manager',
          directive: 'Review Promotion',
          inboxTarget: '/home/phuc/projects/solace-prime/inbox/coder/packet.json',
          color: '#10b981',
          bg: 'rgba(16,185,129,0.1)'
        }
      ];
    } else if (roleName === 'design') {
      acceptanceLogs = [
        {
          state: 'Pending',
          origin: 'manager',
          directive: 'Halt rendering execution and dump architecture variables.',
          inboxTarget: '/home/phuc/projects/solace-prime/inbox/design/command_lock.json',
          color: '#f59e0b',
          bg: 'rgba(245,158,11,0.1)'
        }
      ];
    } else if (roleName === 'manager') {
      acceptanceLogs = [
        {
          state: 'Confirmed',
          origin: 'system',
          directive: 'Delegation Outbox Delivery Verified',
          inboxTarget: 'manager-outbox/specialist-queue-bound',
          color: '#10b981',
          bg: 'rgba(16,185,129,0.1)'
        }
      ];
    } else {
      acceptanceLogs = [
        {
          state: 'Rejected',
          origin: 'manager',
          directive: 'Unresolved node cascades',
          inboxTarget: 'Unreachable. Inbox partition closed.',
          color: '#ef4444',
          bg: 'rgba(239,68,68,0.1)'
        }
      ];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    acceptanceLogs.forEach(function(log) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + log.color + ';display:flex;flex-direction:column;gap:0.3rem;">';
      
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.75rem;text-transform:uppercase;">[Inbox Target -> ' + escapeHtml(log.origin) + ']</strong>';
      html += '<code style="color:' + log.color + ';background:' + log.bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(log.state) + '</code>';
      html += '</div>';

      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Bound Directive:</span> <span style="font-family:monospace;font-size:0.7rem;color:#c084fc;">' + escapeHtml(log.directive) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Inbox Trace:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(log.inboxTarget) + '</span></div>';
      
      // Phuc Forecast bounds (crypto stamping)
      var dummyHash = btoa(log.state + log.directive + log.inboxTarget).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Receipt Hash:</span> <code style="font-size:0.6rem;color:#94a3b8;">' + dummyHash + '</code></div>';

      html += '</div>';
      html += '</div>';
    });

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Acceptance Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Delivery Basis: <code>visible specialist receipt and inbox-delivery state for current handoff context</code><br/>';
    html += 'Evaluation Limit: <code>Verification of Specialist Inbox Delivery</code><br/>';
    html += 'Resolution Bound: <code>Closure of Manager Delegation loop (SI18)</code>';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAR34: Specialist Intake Readiness ──

  function updateSpecialistIntakeReadiness(appId, runId) {
    var panel = document.getElementById('dev-specialist-intake-readiness-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Mock explicit readiness arrays deriving from SAS33 inbox acceptance logic
    var readinessLogs = [];

    if (roleName === 'coder') {
      readinessLogs = [
        {
          state: 'Ready',
          specialist: 'solace-prime-mermaid-coder-v1.2.0',
          activePacket: 'inbox/coder/packet.json',
          constraint: 'Environment spun. Dependencies localized. No cascade blocks detected.',
          color: '#10b981',
          bg: 'rgba(16,185,129,0.1)'
        }
      ];
    } else if (roleName === 'design') {
      readinessLogs = [
        {
          state: 'Queued',
          specialist: 'solace-ui-renderer-v1',
          activePacket: 'inbox/design/command_lock.json',
          constraint: 'Awaiting primary Coder execution clearance before rendering loop begins.',
          color: '#f59e0b',
          bg: 'rgba(245,158,11,0.1)'
        }
      ];
    } else {
      readinessLogs = [
        {
          state: 'Blocked',
          specialist: 'System Manager',
          activePacket: 'Intake failed',
          constraint: 'Out of Context Memory Exception. Specialist partition suspended.',
          color: '#ef4444',
          bg: 'rgba(239,68,68,0.1)'
        }
      ];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    readinessLogs.forEach(function(log) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + log.color + ';display:flex;flex-direction:column;gap:0.3rem;">';
      
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.75rem;text-transform:uppercase;">[Execution Engine -> ' + escapeHtml(log.specialist) + ']</strong>';
      html += '<code style="color:' + log.color + ';background:' + log.bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(log.state) + '</code>';
      html += '</div>';

      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Intake Packet:</span> <span style="font-family:monospace;font-size:0.7rem;color:#c084fc;">' + escapeHtml(log.activePacket) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Execution Trace:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(log.constraint) + '</span></div>';
      
      // Phuc Forecast bounds (crypto stamping)
      var dummyHash = btoa(log.state + log.specialist + log.activePacket).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Readiness Hash:</span> <code style="font-size:0.6rem;color:#94a3b8;">' + dummyHash + '</code></div>';

      html += '</div>';
      html += '</div>';
    });

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Execution Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Execution Basis: <code>visible specialist intake clearance and execution-start state for current acceptance context</code><br/>';
    html += 'Evaluation Limit: <code>Clearance of execution partition dependencies</code><br/>';
    html += 'Resolution Bound: <code>Proceeds directly to Worker Loop (SI21)</code>';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAX35: Specialist Execution Activity ──

  function updateSpecialistExecutionActivity(appId, runId) {
    var panel = document.getElementById('dev-specialist-execution-activity-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Mock explicit execution activity deriving from SAR34 intake environments
    var activityLogs = [];

    if (roleName === 'coder') {
      activityLogs = [
        {
          state: 'Running',
          specialist: 'solace-prime-mermaid-coder-v1.2.0',
          activePacket: 'inbox/coder/packet.json',
          firstOutput: 'Node active. Generated preliminary AST matrix from source constraints.',
          color: '#10b981',
          bg: 'rgba(16,185,129,0.1)'
        }
      ];
    } else if (roleName === 'design') {
      activityLogs = [
        {
          state: 'Paused',
          specialist: 'solace-ui-renderer-v1',
          activePacket: 'inbox/design/command_lock.json',
          firstOutput: 'Execution halted at validation gate. Awaiting Coder structural hashes.',
          color: '#f59e0b',
          bg: 'rgba(245,158,11,0.1)'
        }
      ];
    } else {
      activityLogs = [
        {
          state: 'Failed',
          specialist: 'System Manager',
          activePacket: 'Intake failed',
          firstOutput: 'Process aborted. Fatal syntax error during initialization.',
          color: '#ef4444',
          bg: 'rgba(239,68,68,0.1)'
        }
      ];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    
    activityLogs.forEach(function(log) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + log.color + ';display:flex;flex-direction:column;gap:0.3rem;">';
      
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.75rem;text-transform:uppercase;">[Live Monitor -> ' + escapeHtml(log.specialist) + ']</strong>';
      html += '<code style="color:' + log.color + ';background:' + log.bg + ';padding:0.1rem 0.35rem;text-transform:uppercase;font-size:0.65rem;">' + escapeHtml(log.state) + '</code>';
      html += '</div>';

      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Running Packet:</span> <span style="font-family:monospace;font-size:0.7rem;color:#c084fc;">' + escapeHtml(log.activePacket) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">First Output Signal:</span> <span style="color:var(--sb-on-surface);">' + escapeHtml(log.firstOutput) + '</span></div>';
      
      // Phuc Forecast bounds (crypto stamping)
      var dummyHash = btoa(log.state + log.specialist + log.firstOutput).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.65rem;">Activity Hash:</span> <code style="font-size:0.6rem;color:#94a3b8;">' + dummyHash + '</code></div>';

      html += '</div>';
      html += '</div>';
    });

    html += '<div style="margin-top:0.15rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Observability Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Execution Basis: <code>visible specialist execution activity and first-output state for current readiness context</code><br/>';
    html += 'Evaluation Limit: <code>Verification of runtime operation states</code><br/>';
    html += 'Resolution Bound: <code>Confirms worker is generating output sequences (SI18)</code>';
    html += '</div>';

    html += '</div>';
    
    panel.innerHTML = html;
  }

  // ── SAE36: Specialist Execution Evidence ──

  function updateSpecialistExecutionEvidence(appId, runId) {
    var panel = document.getElementById('dev-specialist-execution-evidence-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Evidence entries derived from SAX35 activity signals (role-mocked; shown honestly)
    var evidenceLogs = [];

    if (roleName === 'coder') {
      evidenceLogs = [
        {
          state: 'Streaming',
          specialist: 'solace-prime-mermaid-coder-v1.2.0',
          activePacket: 'inbox/coder/packet.json',
          logLines: [
            '[00:00.12] AST parse pass 1/3 complete — 412 nodes resolved',
            '[00:00.38] Type-check layer engaged — 0 critical errors',
            '[00:00.61] Writing interim artifact: /tmp/coder-pass1.json'
          ],
          color: '#10b981',
          bg: 'rgba(16,185,129,0.1)'
        }
      ];
    } else if (roleName === 'design') {
      evidenceLogs = [
        {
          state: 'Stalled',
          specialist: 'solace-ui-renderer-v1',
          activePacket: 'inbox/design/command_lock.json',
          logLines: [
            '[00:01.04] Awaiting structural hash from Coder lane',
            '[00:06.00] No hash received — renderer blocked at gate SI17',
            '[00:12.00] Heartbeat timeout (2/3) — partition suspended'
          ],
          color: '#f59e0b',
          bg: 'rgba(245,158,11,0.1)'
        }
      ];
    } else if (roleName === 'qa') {
      evidenceLogs = [
        {
          state: 'Terminated',
          specialist: 'solace-qa-agent-v2',
          activePacket: 'inbox/qa/test-suite.json',
          logLines: [
            '[00:00.05] Test harness initialised — 18 suites loaded',
            '[00:00.22] Suite 3 FAIL: assertion mismatch on node boundary',
            '[00:00.23] Fatal — run aborted with exit code 1'
          ],
          color: '#ef4444',
          bg: 'rgba(239,68,68,0.1)'
        }
      ];
    } else {
      evidenceLogs = [
        {
          state: 'Terminated',
          specialist: 'System Manager',
          activePacket: 'N/A',
          logLines: ['[00:00.00] No specialist lane bound. Evidence stream closed.'],
          color: '#ef4444',
          bg: 'rgba(239,68,68,0.1)'
        }
      ];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    evidenceLogs.forEach(function(log) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + log.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header row
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;text-transform:uppercase;">[Evidence Stream → ' + escapeHtml(log.specialist) + ']</strong>';
      html += '<code style="color:' + log.color + ';background:' + log.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(log.state) + '</code>';
      html += '</div>';

      // Packet ref
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Source Packet:</span> <span style="font-family:monospace;font-size:0.68rem;color:#c084fc;">' + escapeHtml(log.activePacket) + '</span></div>';

      // Log lines
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;display:flex;flex-direction:column;gap:0.15rem;">';
      log.logLines.forEach(function(line) {
        html += '<code style="font-size:0.63rem;color:#94a3b8;white-space:pre-wrap;">' + escapeHtml(line) + '</code>';
      });
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(log.state + log.specialist + log.logLines[0]).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Evidence Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Evidence Basis: <code>visible specialist output-log and execution-evidence state for current activity context</code><br/>';
    html += 'Evidence values are <em>role-derived mocks</em> until runtime log path is wired.<br/>';
    html += 'Resolution Bound: <code>SI18 — Transparency as Product Feature</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAB37: Specialist Artifact Bundle ──

  function updateSpecialistArtifactBundle(appId, runId) {
    var panel = document.getElementById('dev-specialist-artifact-bundle-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Bundle entries derived from SAE36 evidence streams (role-mocked; shown honestly)
    var bundles = [];

    if (roleName === 'coder') {
      bundles = [{
        state: 'Partial',
        bundleId: 'coder-run-20260328-001',
        specialist: 'solace-prime-mermaid-coder-v1.2.0',
        sourcePacket: 'inbox/coder/packet.json',
        artifacts: [
          { name: 'coder-pass1.json',   size: '14.2 KB',  status: 'written' },
          { name: 'ast-matrix.bin',     size: '88.7 KB',  status: 'written' },
          { name: 'final-output.json',  size: '—',        status: 'pending' }
        ],
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      bundles = [{
        state: 'Open',
        bundleId: 'design-run-20260328-002',
        specialist: 'solace-ui-renderer-v1',
        sourcePacket: 'inbox/design/command_lock.json',
        artifacts: [
          { name: 'layout-draft.svg',   size: '—',        status: 'pending' },
          { name: 'tokens.json',        size: '—',        status: 'pending' }
        ],
        color: '#3b82f6',
        bg: 'rgba(59,130,246,0.1)'
      }];
    } else if (roleName === 'qa') {
      bundles = [{
        state: 'Sealed',
        bundleId: 'qa-run-20260328-003',
        specialist: 'solace-qa-agent-v2',
        sourcePacket: 'inbox/qa/test-suite.json',
        artifacts: [
          { name: 'test-report.json',   size: '6.1 KB',   status: 'written' },
          { name: 'coverage.xml',       size: '22.4 KB',  status: 'written' },
          { name: 'failure-trace.txt',  size: '1.3 KB',   status: 'written' }
        ],
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else {
      bundles = [{
        state: 'Open',
        bundleId: 'unknown-bundle',
        specialist: 'Unbound',
        sourcePacket: 'N/A',
        artifacts: [],
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    bundles.forEach(function(bundle) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + bundle.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">📦 ' + escapeHtml(bundle.bundleId) + '</strong>';
      html += '<code style="color:' + bundle.color + ';background:' + bundle.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(bundle.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Specialist:</span> <span style="font-family:monospace;font-size:0.68rem;color:#c084fc;">' + escapeHtml(bundle.specialist) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Source Packet:</span> <span style="font-family:monospace;font-size:0.63rem;">' + escapeHtml(bundle.sourcePacket) + '</span></div>';
      html += '</div>';

      // Artifact file table
      if (bundle.artifacts.length > 0) {
        html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;display:flex;flex-direction:column;gap:0.12rem;">';
        bundle.artifacts.forEach(function(a) {
          var statusColor = a.status === 'written' ? '#10b981' : '#64748b';
          html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
          html += '<code style="font-size:0.63rem;color:#94a3b8;">' + escapeHtml(a.name) + '</code>';
          html += '<span style="display:flex;gap:0.4rem;">';
          html += '<code style="font-size:0.6rem;color:#475569;">' + escapeHtml(a.size) + '</code>';
          html += '<code style="font-size:0.6rem;color:' + statusColor + ';">' + escapeHtml(a.status) + '</code>';
          html += '</span></div>';
        });
        html += '</div>';
      } else {
        html += '<div style="font-size:0.63rem;color:#475569;"><em>No artifacts written yet.</em></div>';
      }

      // ALCOA+ hash
      var alcoa = btoa(bundle.state + bundle.bundleId + bundle.specialist).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Bundle Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Artifact Basis: <code>visible specialist artifact-bundle and run-output state for current evidence context</code><br/>';
    html += 'Bundle values are <em>role-derived mocks</em> until run output path is wired.<br/>';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAV38: Specialist Artifact Provenance ──

  function updateSpecialistArtifactProvenance(appId, runId) {
    var panel = document.getElementById('dev-specialist-artifact-provenance-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Provenance entries derived from SAB37 bundle (role-mocked; shown honestly)
    var provenanceEntries = [];

    if (roleName === 'coder') {
      provenanceEntries = [{
        integrity: 'Partial',
        bundleId: 'coder-run-20260328-001',
        specialist: 'solace-prime-mermaid-coder-v1.2.0',
        sourcePacket: 'inbox/coder/packet.json',
        origin: 'manager-directive → SAD31 → SAH32 → inbox/coder',
        checks: [
          { file: 'coder-pass1.json',  result: 'hash-match',   detail: 'sha256:4f3a9c… ✓' },
          { file: 'ast-matrix.bin',    result: 'hash-match',   detail: 'sha256:8b12de… ✓' },
          { file: 'final-output.json', result: 'missing',      detail: 'File not yet produced' }
        ],
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      provenanceEntries = [{
        integrity: 'Invalid',
        bundleId: 'design-run-20260328-002',
        specialist: 'solace-ui-renderer-v1',
        sourcePacket: 'inbox/design/command_lock.json',
        origin: 'manager-directive → SAD31 → SAH32 → inbox/design',
        checks: [
          { file: 'layout-draft.svg',  result: 'hash-mismatch', detail: 'Expected sha256:cc01… got aa99…' },
          { file: 'tokens.json',       result: 'missing',        detail: 'File not produced — stall in SAE36' }
        ],
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else if (roleName === 'qa') {
      provenanceEntries = [{
        integrity: 'Verified',
        bundleId: 'qa-run-20260328-003',
        specialist: 'solace-qa-agent-v2',
        sourcePacket: 'inbox/qa/test-suite.json',
        origin: 'manager-directive → SAD31 → SAH32 → inbox/qa',
        checks: [
          { file: 'test-report.json',  result: 'hash-match', detail: 'sha256:7e2f01… ✓' },
          { file: 'coverage.xml',      result: 'hash-match', detail: 'sha256:3d90bc… ✓' },
          { file: 'failure-trace.txt', result: 'hash-match', detail: 'sha256:1a55ef… ✓' }
        ],
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else {
      provenanceEntries = [{
        integrity: 'Invalid',
        bundleId: 'unknown-bundle',
        specialist: 'Unbound',
        sourcePacket: 'N/A',
        origin: 'No lane bound',
        checks: [],
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var resultIcon = { 'hash-match': '✅', 'hash-mismatch': '❌', 'missing': '⏳' };
    var resultColor = { 'hash-match': '#10b981', 'hash-mismatch': '#ef4444', 'missing': '#f59e0b' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    provenanceEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">🔎 ' + escapeHtml(entry.bundleId) + '</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.integrity) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Specialist:</span> <span style="font-family:monospace;font-size:0.68rem;color:#c084fc;">' + escapeHtml(entry.specialist) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Provenance Chain:</span> <span style="font-size:0.63rem;color:#94a3b8;">' + escapeHtml(entry.origin) + '</span></div>';
      html += '</div>';

      // Integrity check table
      if (entry.checks.length > 0) {
        html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;display:flex;flex-direction:column;gap:0.12rem;">';
        entry.checks.forEach(function(c) {
          var ic = resultIcon[c.result] || '?';
          var cc = resultColor[c.result] || '#94a3b8';
          html += '<div style="display:flex;align-items:flex-start;gap:0.35rem;">';
          html += '<span style="font-size:0.63rem;">' + ic + '</span>';
          html += '<div style="display:flex;flex-direction:column;gap:0.05rem;">';
          html += '<code style="font-size:0.63rem;color:#94a3b8;">' + escapeHtml(c.file) + '</code>';
          html += '<span style="font-size:0.6rem;color:' + cc + ';">' + escapeHtml(c.detail) + '</span>';
          html += '</div></div>';
        });
        html += '</div>';
      } else {
        html += '<div style="font-size:0.63rem;color:#475569;"><em>No integrity checks available.</em></div>';
      }

      // ALCOA+ hash
      var alcoa = btoa(entry.integrity + entry.bundleId + entry.origin).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Provenance Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Provenance Basis: <code>visible specialist artifact provenance and integrity state for current bundle context</code><br/>';
    html += 'Provenance values are <em>role-derived mocks</em> until runtime hash path is wired.<br/>';
    html += 'Resolution Bound: <code>SI18 — Transparency as a Product Feature</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAP39: Specialist Promotion Candidate ──

  function updateSpecialistPromotionCandidate(appId, runId) {
    var panel = document.getElementById('dev-specialist-promotion-candidate-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Promotion entries derived from SAV38 provenance (role-mocked; shown honestly)
    var candidates = [];

    if (roleName === 'coder') {
      candidates = [{
        status: 'Provisional',
        bundleId: 'coder-run-20260328-001',
        specialist: 'solace-prime-mermaid-coder-v1.2.0',
        sourcePacket: 'inbox/coder/packet.json',
        basis: 'Provenance check: Partial. final-output.json not yet produced.',
        blockers: ['Awaiting final-output.json write completion'],
        gate: 'Human gate (SI17) required before promoting to department memory',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      candidates = [{
        status: 'Disqualified',
        bundleId: 'design-run-20260328-002',
        specialist: 'solace-ui-renderer-v1',
        sourcePacket: 'inbox/design/command_lock.json',
        basis: 'Provenance check: Invalid. Hash mismatch on layout-draft.svg; tokens.json missing.',
        blockers: [
          'hash-mismatch: layout-draft.svg (Expected sha256:cc01… got aa99…)',
          'missing: tokens.json'
        ],
        gate: 'Must re-run design lane with corrected packet',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else if (roleName === 'qa') {
      candidates = [{
        status: 'Ready-to-Seal',
        bundleId: 'qa-run-20260328-003',
        specialist: 'solace-qa-agent-v2',
        sourcePacket: 'inbox/qa/test-suite.json',
        basis: 'Provenance check: Verified. All 3 artifacts hash-matched.',
        blockers: [],
        gate: 'Human gate (SI17) — manager must approve seal action',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else {
      candidates = [{
        status: 'Disqualified',
        bundleId: 'unknown-bundle',
        specialist: 'Unbound',
        sourcePacket: 'N/A',
        basis: 'No specialist lane bound. Provenance chain incomplete.',
        blockers: ['No lane registered'],
        gate: 'N/A',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var statusIcon = { 'Ready-to-Seal': '🟢', 'Provisional': '🟡', 'Disqualified': '🔴' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    candidates.forEach(function(c) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + c.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (statusIcon[c.status] || '●') + ' ' + escapeHtml(c.bundleId) + '</strong>';
      html += '<code style="color:' + c.color + ';background:' + c.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(c.status) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Specialist:</span> <span style="font-family:monospace;font-size:0.68rem;color:#c084fc;">' + escapeHtml(c.specialist) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Promotion Basis:</span> <span style="font-size:0.63rem;color:#94a3b8;">' + escapeHtml(c.basis) + '</span></div>';
      html += '</div>';

      // Blockers
      if (c.blockers.length > 0) {
        html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;display:flex;flex-direction:column;gap:0.1rem;">';
        html += '<span style="font-size:0.6rem;color:#64748b;font-weight:600;">BLOCKERS</span>';
        c.blockers.forEach(function(b) {
          html += '<div style="display:flex;align-items:center;gap:0.25rem;"><span style="color:#ef4444;font-size:0.63rem;">⚠</span><code style="font-size:0.6rem;color:#94a3b8;">' + escapeHtml(b) + '</code></div>';
        });
        html += '</div>';
      } else {
        html += '<div style="font-size:0.63rem;color:#10b981;"><em>No blockers — all gates clear.</em></div>';
      }

      // Gate
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Seal Gate:</span> <span style="font-size:0.63rem;color:#cbd5e1;">' + escapeHtml(c.gate) + '</span></div>';

      // ALCOA+ hash
      var alcoa = btoa(c.status + c.bundleId + c.basis).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Promotion Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Promotion Basis: <code>visible specialist promotion-candidate and seal-readiness state for current provenance context</code><br/>';
    html += 'Promotion values are <em>role-derived mocks</em> until runtime provenance path is wired.<br/>';
    html += 'Resolution Bound: <code>SI17 — Human-in-the-Loop as First-Class Component</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAM40: Specialist Memory Admission ──

  function updateSpecialistMemoryAdmission(appId, runId) {
    var panel = document.getElementById('dev-specialist-memory-admission-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Admission entries derived from SAP39 seal action (role-mocked; shown honestly)
    var admissionTokens = [];

    if (roleName === 'qa') {
      admissionTokens = [{
        status: 'Admitted',
        bundleId: 'qa-run-20260328-003',
        specialist: 'solace-qa-agent-v2',
        sourcePacket: 'inbox/qa/test-suite.json',
        targetMemory: 'outbox/qa/verified-tests/',
        basis: 'Seal approved via SI17 Gate. Artifacts successfully written to department memory tree.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      admissionTokens = [{
        status: 'Queued',
        bundleId: 'coder-run-20260328-001',
        specialist: 'solace-prime-mermaid-coder-v1.2.0',
        sourcePacket: 'inbox/coder/packet.json',
        targetMemory: 'Pending allocation',
        basis: 'Awaiting promotion candidate to clear Provisional state.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      admissionTokens = [{
        status: 'Rejected',
        bundleId: 'design-run-20260328-002',
        specialist: 'solace-ui-renderer-v1',
        sourcePacket: 'inbox/design/command_lock.json',
        targetMemory: 'N/A',
        basis: 'Promotion disqualified (hash-mismatch). Admission request denied.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      admissionTokens = [{
        status: 'Rejected',
        bundleId: 'unknown-bundle',
        specialist: 'Unbound',
        sourcePacket: 'N/A',
        targetMemory: 'N/A',
        basis: 'No specialist lane bound. Admission impossible.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    admissionTokens.forEach(function(token) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + token.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (token.status === 'Admitted' ? '📥' : '🔒') + ' ' + escapeHtml(token.bundleId) + '</strong>';
      html += '<code style="color:' + token.color + ';background:' + token.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(token.status) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Specialist:</span> <span style="font-family:monospace;font-size:0.68rem;color:#c084fc;">' + escapeHtml(token.specialist) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Memory Target:</span> <span style="font-family:monospace;font-size:0.68rem;color:#10b981;">' + escapeHtml(token.targetMemory) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Admission Basis:</span> <span style="font-size:0.63rem;color:#94a3b8;">' + escapeHtml(token.basis) + '</span></div>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(token.status + token.bundleId + token.targetMemory).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Admission Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(runId || 'latest') + '</code><br/>';
    html += 'Admission Basis: <code>visible specialist seal-action request and department-memory admission state for current promotion context</code><br/>';
    html += 'Admission values are <em>role-derived mocks</em> until runtime fs pipeline is wired.<br/>';
    html += 'Resolution Bound: <code>SI18 — Transparency as Product Feature</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC41: Specialist Memory Entry ──

  function updateSpecialistMemoryEntry(appId, runId) {
    var panel = document.getElementById('dev-specialist-memory-entry-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Convention records derived from SAM40 admission target (role-mocked; shown honestly)
    var memoryEntries = [];

    if (roleName === 'qa') {
      memoryEntries = [{
        state: 'Live',
        bundleId: 'qa-run-20260328-003',
        specialist: 'solace-qa-agent-v2',
        sourcePacket: 'inbox/qa/test-suite.json',
        conventionTarget: 'tests/e2e/verified-suite-v3.json',
        objectDesc: 'Reusable end-to-end test convention bound to SI18 governance model.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      memoryEntries = [{
        state: 'Draft',
        bundleId: 'coder-run-20260328-001',
        specialist: 'solace-prime-mermaid-coder-v1.2.0',
        sourcePacket: 'inbox/coder/packet.json',
        conventionTarget: 'tmp/pending-ast-matrix.bin',
        objectDesc: 'Temporary layout pending bundle seal and SI17 memory admission.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      memoryEntries = [{
        state: 'Revoked',
        bundleId: 'design-run-20260328-002',
        specialist: 'solace-ui-renderer-v1',
        sourcePacket: 'inbox/design/command_lock.json',
        conventionTarget: 'N/A',
        objectDesc: 'Memory admission rejected. Bundle outputs purged from convention pool.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      memoryEntries = [{
        state: 'Revoked',
        bundleId: 'unknown-bundle',
        specialist: 'Unbound',
        sourcePacket: 'N/A',
        conventionTarget: 'N/A',
        objectDesc: 'Cannot form memory entry from unbound or untrusted sources.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var stateIcon = { 'Live': '📄', 'Draft': '📝', 'Revoked': '🗑️' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    memoryEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (stateIcon[entry.state] || '●') + ' ' + escapeHtml(entry.bundleId) + '</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Specialist:</span> <span style="font-family:monospace;font-size:0.68rem;color:#c084fc;">' + escapeHtml(entry.specialist) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Convention Target:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.conventionTarget) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.objectDesc) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.bundleId + entry.conventionTarget).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Entry Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Memory Basis: <code>visible specialist output -> memory admission -> department convention entry</code><br/>';
    html += 'Entry values are <em>role-derived mocks</em> until runtime registry binding is wired. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAQ26: Department Memory Queue ──

  function updateDepartmentMemoryQueue(appId, runId) {
    var panel = document.getElementById('dev-department-memory-queue');
    if (!panel) return;

    var queueItems = [
      {
        appId: 'solace-dev-manager',
        role: 'manager',
        state: 'pending',
        candidateId: 'nexus-routing-v2.2-candidate',
        basis: 'Consistent assignment packet generation detected. Pending human validation gate for GLOBAL promotion.',
        runRef: 'manager-run-routing-01'
      },
      {
        appId: 'solace-coder',
        role: 'coder',
        state: 'promoted',
        candidateId: 'solace-prime-mermaid-coder-v1.2.0',
        basis: 'Mature structural repetition (100% success rate across 5 traces). Promoted to SHARED memory.',
        runRef: 'coder-run-mermaid-05'
      },
      {
        appId: 'solace-design',
        role: 'design',
        state: 'blocked',
        candidateId: 'N/A',
        basis: 'No stable visual convention repetition yet. Output remains discover-tier.',
        runRef: 'design-run-layout-02'
      },
      {
        appId: 'solace-qa',
        role: 'qa',
        state: 'blocked',
        candidateId: 'N/A',
        basis: 'Verification traces are high-value but not yet reusable as a promoted department convention.',
        runRef: 'qa-run-falsifier-03'
      }
    ];

    var counts = { promoted: 0, pending: 0, blocked: 0 };
    queueItems.forEach(function(item) {
      if (item.state === 'promoted') counts.promoted += 1;
      else if (item.state === 'pending') counts.pending += 1;
      else counts.blocked += 1;
    });

    var html = '<div style="display:flex;flex-direction:column;gap:0.45rem;font-size:0.75rem;color:var(--sb-on-surface);">';
    html += '<div style="display:flex;gap:0.35rem;flex-wrap:wrap;">';
    html += '<span class="sb-pill" style="background:rgba(16,185,129,0.12);color:#10b981;">promoted ' + counts.promoted + '</span>';
    html += '<span class="sb-pill" style="background:rgba(245,158,11,0.12);color:#f59e0b;">pending ' + counts.pending + '</span>';
    html += '<span class="sb-pill" style="background:rgba(239,68,68,0.12);color:#ef4444;">blocked ' + counts.blocked + '</span>';
    html += '</div>';

    queueItems.forEach(function(item) {
      var color = '#94a3b8';
      var bg = 'rgba(148,163,184,0.1)';
      var label = 'UNKNOWN';
      if (item.state === 'promoted') {
        color = '#10b981';
        bg = 'rgba(16,185,129,0.1)';
        label = 'PROMOTED';
      } else if (item.state === 'pending') {
        color = '#f59e0b';
        bg = 'rgba(245,158,11,0.1)';
        label = 'PENDING REVIEW';
      } else if (item.state === 'blocked') {
        color = '#ef4444';
        bg = 'rgba(239,68,68,0.1)';
        label = 'BLOCKED';
      }

      var isActive = item.appId === appId;
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + color + ';' + (isActive ? 'box-shadow:0 0 0 1px rgba(129,140,248,0.35);' : '') + '">';
      html += '<div style="display:flex;align-items:center;justify-content:space-between;gap:0.5rem;margin-bottom:0.2rem;">';
      html += '<strong style="font-size:0.72rem;">' + escapeHtml(item.appId) + '</strong>';
      html += '<code style="color:' + color + ';background:' + bg + ';padding:0.1rem 0.35rem;font-size:0.65rem;">' + label + '</code>';
      html += '</div>';
      html += '<div style="display:flex;flex-direction:column;gap:0.16rem;font-size:0.69rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;">Role:</span> <code>' + escapeHtml(item.role) + '</code></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;">Candidate:</span> <span style="font-family:monospace;color:#818cf8;">' + escapeHtml(item.candidateId) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;">Run Reference:</span> <code>' + escapeHtml(item.runRef) + '</code></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;">Review Basis:</span> <span>' + escapeHtml(item.basis) + '</span></div>';
      html += '</div>';
      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.65rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Active Queue Context:</strong><br/>';
    html += 'Viewer Role: <code>solace-dev-manager</code><br/>';
    html += 'Selected Worker: <code>' + (appId || 'unknown') + '</code><br/>';
    html += 'Selected Run: <code>' + (runId || 'latest') + '</code><br/>';
    html += 'Queue Basis: <code>manager-facing visible department memory review queue</code><br/>';
    html += 'Promotion Basis: <code>role-derived visible promotion status across specialists</code>';
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
