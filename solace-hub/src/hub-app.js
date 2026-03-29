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

  window.__solaceActiveRequestId = null;
  window.__solaceLastWorkflowRouteAction = null;
  window.__solaceLastWorkflowLaunchAction = null;

  function hydrateActiveWorkflowSelector() {
    var select = document.getElementById('dev-request-select');
    if (!select) return;
    
    get('/api/v1/backoffice/solace-dev-manager/requests').catch(function(){return {items:[]};}).then(function(res) {
      // Preserve current selection if any
      var currentVal = window.__solaceActiveRequestId;
      
      var items = res.items || [];
      var html = '<option value="">-- No Active Request (Fallback Mode) --</option>';
      items.forEach(function(req) {
        var label = '[' + req.ticket_type + '] ' + req.title + ' (' + req.id.substring(0,8) + ')';
        var selected = (req.id === currentVal) ? ' selected' : '';
        html += '<option value="' + req.id + '"' + selected + '>' + escapeHtml(label) + '</option>';
      });
      select.innerHTML = html;
    });
  }

  window.__solaceSelectRequest = function(reqId) {
    if (!reqId) {
       window.__solaceActiveRequestId = null;
    } else {
       window.__solaceActiveRequestId = reqId;
    }
    hydrateActiveWorkflowRoutes();
    hydrateDevWorkspace();
  };

  window.__solaceCreateSac67Request = function() {
    var title = prompt("Enter new Solace Browser request title:", "SAC67 Native Manager Request");
    if (!title) return;
    
    // 1. Get Project ID for 'solace-browser'
    get('/api/v1/backoffice/solace-dev-manager/projects').catch(function(){return {items:[]};}).then(function(res) {
        var items = res.items || [];
        var proj = items.find(function(p) { return p.repository === 'solace-browser'; });
        function createRequestForProject(projectId) {
          fetch(API + '/api/v1/backoffice/solace-dev-manager/requests', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                  project_id: projectId,
                  ticket_type: 'feature',
                  title: title,
                  status: 'assigned'
              })
          }).then(function(r) { return r.json(); }).then(function(reqData) {
              if (!reqData.created) { alert('Failed to create request'); return; }
              var reqId = reqData.record.id;
              
              // Auto-select this request
              window.__solaceSelectRequest(reqId);
              // Also refresh dropdown
              hydrateActiveWorkflowSelector();
          });
        }

        if (proj) {
          createRequestForProject(proj.id);
          return;
        }

        // 2. Create project on demand so the flow is self-hosting, not seed-script dependent
        fetch(API + '/api/v1/backoffice/solace-dev-manager/projects', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: 'Solace Browser',
                repository: 'solace-browser',
                description: 'Self-hosted Solace Dev workspace target project'
            })
        }).then(function(r) { return r.json(); }).then(function(projectData) {
            if (!projectData.created) { alert('Failed to create solace-browser project'); return; }
            createRequestForProject(projectData.record.id);
        });
    });
  };

  window.__solaceRouteActiveRequest = function(overrideTargetRole) {
    var reqId = window.__solaceActiveRequestId;
    if (!reqId) {
      alert("No active request selected to route.");
      return;
    }
    var targetRole = overrideTargetRole;
    if (!targetRole) {
        var sel = document.getElementById('dev-route-role-select');
        targetRole = sel ? sel.value : null;
    }
    if (!targetRole) return;

    get('/api/v1/backoffice/solace-dev-manager/assignments').catch(function(){return {items:[]};}).then(function(res) {
      var assignments = res.items || [];
      var existing = assignments.find(function(a) {
        return a.request_id === reqId && a.target_role === targetRole;
      });

      var path = API + '/api/v1/backoffice/solace-dev-manager/assignments';
      var method = 'POST';
      var body = {
        request_id: reqId,
        target_role: targetRole,
        details: 'Routed via Manager Action',
        status: 'active'
      };

      if (existing && existing.id) {
        path += '/' + existing.id;
        method = 'PUT';
        body = {
          request_id: existing.request_id,
          target_role: existing.target_role,
          details: existing.details || 'Routed via Manager Action',
          status: 'active'
        };
      }

      fetch(path, {
          method: method,
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(body)
      }).then(function(r) { return r.json(); }).then(function(result) {
          var mutation = (existing && existing.id) ? 'updated' : 'created';
          window.__solaceLastWorkflowRouteAction = {
            requestId: reqId,
            sourceAssignmentId: null,
            targetRole: targetRole,
            mutation: mutation,
            assignmentId: (result && result.record && result.record.id) ? result.record.id : (existing ? existing.id : null)
          };
          hydrateActiveWorkflowRoutes();
          hydrateActiveWorkflowResult();
          hydrateDevWorkspace();
      });
    });
  };

  window.__solaceRouteWorkflowNextStep = function(assignmentId, overrideTargetRole) {
    var reqId = window.__solaceActiveRequestId;
    if (!reqId || !assignmentId) return;

    var targetRole = overrideTargetRole;
    if (!targetRole) return;

    get('/api/v1/backoffice/solace-dev-manager/assignments').catch(function(){return {items:[]};}).then(function(res) {
      var assignments = res.items || [];
      var sourceAssignment = assignments.find(function(a) { return a.id === assignmentId && a.request_id === reqId; });
      if (!sourceAssignment) return;

      var existing = assignments.find(function(a) {
        return a.request_id === reqId && a.target_role === targetRole;
      });

      var path = API + '/api/v1/backoffice/solace-dev-manager/assignments';
      var method = 'POST';
      var mutation = 'created';
      var body = {
        request_id: reqId,
        target_role: targetRole,
        details: 'Routed via workflow result (' + sourceAssignment.target_role + ' -> ' + targetRole + ')',
        status: 'active'
      };

      if (existing && existing.id) {
        path += '/' + existing.id;
        method = 'PUT';
        mutation = 'updated';
        body = {
          request_id: existing.request_id,
          target_role: existing.target_role,
          details: existing.details || ('Routed via workflow result (' + sourceAssignment.target_role + ' -> ' + targetRole + ')'),
          status: 'active'
        };
      }

      fetch(path, {
          method: method,
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(body)
      }).then(function(r) { return r.json(); }).then(function(result) {
          window.__solaceLastWorkflowRouteAction = {
            requestId: reqId,
            sourceAssignmentId: assignmentId,
            targetRole: targetRole,
            mutation: mutation,
            assignmentId: (result && result.record && result.record.id) ? result.record.id : (existing ? existing.id : null)
          };
          hydrateActiveWorkflowRoutes();
          hydrateActiveWorkflowResult();
          hydrateDevWorkspace();
      });
    });
  };

  window.__solaceLaunchWorkflowNextStep = function(sourceAssignmentId, targetRole, targetAssignmentId) {
    var reqId = window.__solaceActiveRequestId;
    if (!reqId || !sourceAssignmentId || !targetRole || !targetAssignmentId) return;

    get('/api/v1/backoffice/solace-dev-manager/assignments').catch(function(){return {items:[]};}).then(function(res) {
      var assignments = res.items || [];
      var sourceAssignment = assignments.find(function(a) { return a.id === sourceAssignmentId && a.request_id === reqId; });
      var targetAssignment = assignments.find(function(a) { return a.id === targetAssignmentId && a.request_id === reqId && a.target_role === targetRole; });
      if (!sourceAssignment || !targetAssignment) return;

      var roleObj = DEV_ROLES.find(function(r) { return r.key === targetRole; });
      if (!roleObj) return;

      var appId = roleObj.id;
      fetch(API + '/api/v1/apps/run/' + appId, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer dragon_rider_override' }
      }).then(function(r) { return r.json().then(function(d) { return { status: r.status, data: d }; }); })
      .then(function(res) {
        var data = res.data;
        if (!data.ok) return;

        var runId = null;
        if (data.report) {
          var match = data.report.match(/runs\/([^\/]+)\/artifact\/report\.html/);
          if (match && match[1]) runId = match[1];
        }
        if (!runId) return;

        saveWorkflowLaunchBinding(reqId, targetAssignment.id, appId, runId);
        
        // --- SAC87 Preserve Origin vs Nested Truth ---
        if (window.__solaceLastWorkflowLaunchAction && window.__solaceLastWorkflowLaunchAction.targetAssignmentId === sourceAssignmentId) {
            window.__solaceLastWorkflowNestedLaunchAction = {
                requestId: reqId,
                sourceAssignmentId: sourceAssignmentId,
                sourceRole: window.__solaceLastWorkflowLaunchAction.targetRole,
                sourceRunId: window.__solaceLastWorkflowLaunchAction.runId,
                targetAssignmentId: targetAssignment.id,
                targetRole: targetRole,
                appId: appId,
                runId: runId,
                basis: 'workflow-routed-nested-assignment-launch'
            };
        } else {
            window.__solaceLastWorkflowLaunchAction = {
              requestId: reqId,
              sourceAssignmentId: sourceAssignmentId,
              targetAssignmentId: targetAssignment.id,
              targetRole: targetRole,
              appId: appId,
              runId: runId,
              basis: 'workflow-routed-assignment-launch'
            };
            window.__solaceLastWorkflowNestedLaunchAction = null;
        }
        // --------------------------------------------

        if (window.__solaceSelectRun) {
          window.__solaceSelectRun(appId, runId, null);
        }
        hydrateActiveWorkflowResult();
        hydrateDevWorkspace();
      });
    });
  };

  window.__solaceSignoffWorkflow = function(assignmentId, existingId, status) {
    if (!assignmentId) return;
    var launchCtx = window.__solaceLastWorkflowLaunchAction || null;
    
    var payload = {
        assignment_id: assignmentId,
        approver_role: 'manager',
        status: status,
        notes: (status === 'approved' ? 'Manager natively verified the workflow execution output.' : 'Manager rejected the workflow execution output.')
    };

    var url = API + '/api/v1/backoffice/solace-dev-manager/approvals';
    var method = 'POST';
    
    if (existingId) {
        url += '/' + existingId;
        method = 'PUT';
    }

    fetch(url, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    }).then(function(r) { return r.json(); }).then(function(res) {
        // --- SAC85 Tracking ---
        window.__solaceLastWorkflowSignoffActionResult = {
            assignmentId: assignmentId,
            status: status,
            requestId: window.__solaceActiveRequestId,
            mutation: (existingId ? 'UPDATE' : 'CREATE'),
            success: !!(res.created || res.updated),
            targetRole: launchCtx && launchCtx.targetAssignmentId === assignmentId ? launchCtx.targetRole : null,
            runId: launchCtx && launchCtx.targetAssignmentId === assignmentId ? launchCtx.runId : null
        };
        // ----------------------
        
        if (!res.created && !res.updated) {
            console.warn('Signoff mutation failed', res);
        }
        hydrateActiveWorkflowResult();
    });
  };

  function hydrateActiveWorkflowRoutes() {
    var panel = document.getElementById('dev-active-workflow-routing');
    var list = document.getElementById('dev-active-workflow-routes');
    var launchPanel = document.getElementById('dev-active-workflow-launch');
    if (!panel || !list) return;

    var reqId = window.__solaceActiveRequestId;
    if (!reqId) {
      panel.style.display = 'none';
      list.innerHTML = '';
      if (launchPanel) launchPanel.style.display = 'none';
      return;
    }

    panel.style.display = 'block';
    
    get('/api/v1/backoffice/solace-dev-manager/assignments').catch(function(){return {items:[]};}).then(function(res) {
      var assignments = res.items || [];
      var active = assignments.filter(function(a) { return a.request_id === reqId; });
      if (active.length === 0) {
        list.innerHTML = 'No assignments routed yet.';
        if (launchPanel) launchPanel.style.display = 'none';
        return;
      }
      var html = '<strong>Active Routes:</strong> ';
      var badges = active.map(function(a) {
        var color = a.status === 'active' ? '#6ee7b7' : '#94a3b8';
        return '<span class="sb-pill" style="color:' + color + '; border:1px solid ' + color + '; padding:0.1rem 0.3rem; margin-right:0.3rem;">' + a.target_role + ' (' + a.status + ')</span>';
      });
      list.innerHTML = html + badges.join('');
      if (launchPanel) launchPanel.style.display = 'block';
    });
  }

  window.__solaceLaunchRoutedFlow = function(overrideRequestedRole) {
    var reqId = window.__solaceActiveRequestId;
    if (!reqId) {
      alert("No active request selected. Cannot launch flow.");
      return;
    }
    var requestedRole = overrideRequestedRole;
    if (!requestedRole) {
        var routeSelect = document.getElementById('dev-route-role-select');
        requestedRole = routeSelect ? routeSelect.value : null;
    }

    var output = document.getElementById('dev-active-workflow-launch-output');
    if (output) {
      output.style.display = 'block';
      output.textContent = 'Resolving active assignment for request ID ' + reqId + '...\n';
      if (requestedRole) {
        output.textContent += 'Requested launch role: ' + requestedRole + '\n';
      }
    }

    // 1. Fetch assignments to find the active target_role for this reqId
    get('/api/v1/backoffice/solace-dev-manager/assignments').catch(function(){return {items:[]};}).then(function(res) {
      var assignments = res.items || [];
      var active = assignments.filter(function(a) { return a.request_id === reqId && a.status === 'active'; });
      
      if (active.length === 0) {
        clearWorkflowLaunchBinding();
        if (output) output.textContent += 'Error: No active assignment routed for this request. Please explicitly route a role first.\n';
        return;
      }
      
      var chosen = null;
      if (requestedRole) {
        chosen = active.find(function(a) { return a.target_role === requestedRole; }) || null;
      }
      if (!chosen) {
        chosen = active[0];
      }
      if (!chosen) {
        if (output) output.textContent += 'Error: Unable to resolve an executable active assignment.\n';
        return;
      }

      var targetRole = chosen.target_role;
      if (output) output.textContent += 'Resolved target role: ' + targetRole + '\n';
      if (output) output.textContent += 'Assignment ID: ' + chosen.id + '\n';
      
      var roleObj = DEV_ROLES.find(function(r) { return r.key === targetRole; });
      if (!roleObj) {
        if (output) output.textContent += 'Error: Target role ' + targetRole + ' does not map to a recognized application.\n';
        return;
      }

      var appId = roleObj.id;
      if (output) output.textContent += 'Executing mapped application: [' + appId + ']\n';
      if (output) output.textContent += 'Runtime Route: POST /api/v1/apps/run/' + appId + '\n';

      // 2. Map target_role to appId and execute `POST /api/v1/apps/run/{appId}`
      fetch(API + '/api/v1/apps/run/' + appId, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer dragon_rider_override' }
      }).then(function(r) { return r.json().then(function(d) { return { status: r.status, data: d }; }); })
      .then(function(res) {
        var data = res.data;
        if (data.ok) {
           if (output) output.textContent += 'Launch SUCCESS (HTTP ' + res.status + '). Worker executing...\n';
           var runId = null;
           if (data.report) {
               var match = data.report.match(/runs\/([^\/]+)\/artifact\/report\.html/);
               if (match && match[1]) runId = match[1];
           }
           if (output && runId) output.textContent += 'Run ID: ' + runId + '\n';
           if (runId) {
               saveWorkflowLaunchBinding(reqId, chosen.id, appId, runId);
           }
           
           if (runId && window.__solaceSelectRun) {
               window.__solaceSelectRun(appId, runId, null);
           }
        } else {
           if (output) output.textContent += 'Launch FAILED (HTTP ' + res.status + '). See logs.\n';
           if (output) output.textContent += JSON.stringify(data) + '\n';
        }
        hydrateDevWorkspace();
      }).catch(function(err) {
        if (output) output.textContent += 'Launch Error: ' + err + '\n';
      });
    });
  }

  function hydrateActiveWorkflowResult() {
    var panel = document.getElementById('dev-active-workflow-result');
    var content = document.getElementById('dev-active-workflow-result-content');
    if (!panel || !content) return;

    var reqId = window.__solaceActiveRequestId;
    var launchBinding = loadWorkflowLaunchBinding();
    var selectedRun = loadSelectedRun();
    var boundRun = null;

    if (launchBinding && launchBinding.requestId === reqId) {
      boundRun = {
        requestId: launchBinding.requestId,
        assignmentId: launchBinding.assignmentId,
        appId: launchBinding.appId,
        runId: launchBinding.runId,
        basis: 'workflow-launch-session-binding'
      };
    } else if (selectedRun) {
      boundRun = {
        requestId: reqId,
        assignmentId: null,
        appId: selectedRun.appId,
        runId: selectedRun.runId,
        basis: 'selected-run-fallback'
      };
    }
    
    if (!reqId || !boundRun) {
      panel.style.display = 'none';
      content.innerHTML = '';
      return;
    }

    Promise.all([
      get('/api/v1/backoffice/solace-dev-manager/assignments').catch(function(){return {items:[]};}),
      get('/api/v1/backoffice/solace-dev-manager/approvals').catch(function(){return {items:[]};})
    ]).then(function(responses) {
      var assignments = responses[0].items || [];
      var approvals = responses[1].items || [];
      var active = assignments.find(function(a) { 
        if (boundRun.assignmentId && a.id === boundRun.assignmentId) {
          return true;
        }
        return a.request_id === reqId && a.status === 'active' && DEV_ROLES.some(function(r) { return r.key === a.target_role && r.id === boundRun.appId });
      });

      if (!active) {
        panel.style.display = 'none';
        content.innerHTML = '';
        return;
      }
      
      var linkedApproval = approvals.find(function(item) { return item.assignment_id === active.id; }) || null;

      get('/api/v1/apps/' + boundRun.appId + '/runs').catch(function(){return {runs:[]};}).then(function(runData) {
        var runs = runData.runs || [];
        var actualRun = runs.find(function(r) { return r.run_id === boundRun.runId; });
        var reportExists = actualRun ? actualRun.report_exists : false;
        var eventsExist = actualRun ? actualRun.events_exist : false;
        var payloadExists = actualRun ? actualRun.payload_exists : false;

        panel.style.display = 'block';
        var html = '<div style="background:var(--sb-surface-alt,#1e293b); padding:0.4rem 0.5rem; border-radius:0.25rem; border-left:2px solid #fcd34d;">';
        html += '<strong>Back Office Request ID:</strong> <code>' + reqId.substring(0,8) + '</code><br/>';
        html += '<strong>Active Assignment ID:</strong> <code>' + active.id.substring(0,8) + '</code> (' + active.target_role + ')<br/>';
        html += '<strong>Launched Run Target:</strong> <code>' + boundRun.appId + ' / ' + boundRun.runId + '</code><br/>';

        html += '<div style="margin-top:0.3rem; padding-top:0.3rem; border-top:1px solid #334155;">';
        html += '<strong style="display:block; margin-bottom:0.1rem;">Run Artifacts:</strong>';
        if (reportExists) {
           html += '<a href="/api/v1/apps/' + boundRun.appId + '/runs/' + boundRun.runId + '/artifact/report.html" target="_blank" style="color:#818cf8; font-size:0.65rem; margin-right:0.4rem;">[↗ View Final Report]</a>';
        } else {
           html += '<span style="color:#64748b; font-size:0.65rem; margin-right:0.4rem;">[No Report]</span>';
        }
        if (eventsExist) {
           html += '<a href="/api/v1/apps/' + boundRun.appId + '/runs/' + boundRun.runId + '/events" target="_blank" style="color:#818cf8; font-size:0.65rem; margin-right:0.4rem;">[↗ View Events API]</a>';
           html += '<a href="/api/v1/apps/' + boundRun.appId + '/runs/' + boundRun.runId + '/artifact/events.jsonl" target="_blank" style="color:#818cf8; font-size:0.65rem; margin-right:0.4rem;">[↗ View Events File]</a>';
        } else {
           html += '<span style="color:#64748b; font-size:0.65rem; margin-right:0.4rem;">[No Events]</span>';
        }
        
        html += '</div>';

        // --- SAC73 & SAC74 Output ---
        html += '<div style="margin-top:0.3rem; padding-top:0.3rem; border-top:1px solid #334155; display:flex; align-items:center; justify-content:space-between;">';
        html += '<div>';
        html += '<strong style="display:block; margin-bottom:0.1rem;">Approval State:</strong>';
        if (linkedApproval) {
            var color = linkedApproval.status === 'approved' ? '#6ee7b7' : (linkedApproval.status === 'rejected' ? '#fca5a5' : '#fcd34d');
            html += '<span class="sb-pill" style="color:' + color + '; border:1px solid ' + color + '; font-size:0.65rem;">' + escapeHtml(linkedApproval.status) + '</span>';
            html += '<span style="font-size:0.65rem; color:var(--sb-text-muted); margin-left:0.4rem;">' + escapeHtml(linkedApproval.notes || '') + '</span>';
        } else {
            html += '<span class="sb-pill" style="color:#94a3b8; border:1px dashed #475569; font-size:0.65rem;">pending workflow signoff</span>';
            html += '<span style="font-size:0.65rem; color:var(--sb-text-muted); margin-left:0.4rem;">No manager approval registered for assignment.</span>';
        }
        html += '</div>';

        var linkedId = linkedApproval ? linkedApproval.id : '';
        html += '<div style="display:flex; gap:0.3rem;">';
        html += '<button onclick="window.__solaceSignoffWorkflow(\'' + active.id + '\', \'' + linkedId + '\', \'approved\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#064e3b;color:#34d399;font-weight:600;border:1px solid #059669;cursor:pointer;">Approve</button>';
        html += '<button onclick="window.__solaceSignoffWorkflow(\'' + active.id + '\', \'' + linkedId + '\', \'rejected\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#4c0519;color:#fca5a5;border:1px solid #e11d48;cursor:pointer;">Reject</button>';
        html += '</div>';
        
        html += '</div>';

        // --- SAC75 Output ---
        if (linkedApproval) {
            html += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
            html += '<strong style="display:block; margin-bottom:0.2rem;">Route Workflow Next Step:</strong>';
            html += '<div style="display:flex; gap:0.3rem;">';
            html += '<button onclick="window.__solaceRouteWorkflowNextStep(\'' + active.id + '\', \'design\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#3b82f6;color:#fff;border:none;cursor:pointer;">Route to Design</button>';
            html += '<button onclick="window.__solaceRouteWorkflowNextStep(\'' + active.id + '\', \'coder\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#10b981;color:#fff;border:none;cursor:pointer;">Route to Coder</button>';
            html += '<button onclick="window.__solaceRouteWorkflowNextStep(\'' + active.id + '\', \'qa\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#f59e0b;color:#fff;border:none;cursor:pointer;">Route to QA</button>';
            html += '</div></div>';
        }
        // --------------------

        var lastRouteAction = window.__solaceLastWorkflowRouteAction;
        if (lastRouteAction && lastRouteAction.requestId === reqId && lastRouteAction.sourceAssignmentId === active.id) {
          html += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
          html += '<strong style="display:block; margin-bottom:0.2rem;">Next-Step Route State:</strong>';
          html += 'Activated Role: <code>' + escapeHtml(lastRouteAction.targetRole) + '</code><br/>';
          if (lastRouteAction.assignmentId) {
            html += 'Activated Assignment ID: <code>' + escapeHtml(lastRouteAction.assignmentId.substring(0, 8)) + '</code><br/>';
          }
          html += 'Routing Basis: <code>Workflow-bound assignment ' + escapeHtml(lastRouteAction.mutation) + ' via real Back Office assignments path (SAC75)</code><br/>';
          
          // --- SAC76 Output ---
          html += '<div style="margin-top:0.3rem; display:flex; gap:0.3rem;">';
          html += '<button onclick="window.__solaceLaunchWorkflowNextStep(\'' + active.id + '\', \'' + escapeHtml(lastRouteAction.targetRole) + '\', \'' + escapeHtml(lastRouteAction.assignmentId || '') + '\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#0f172a;color:#fff;border:1px solid #3b82f6;cursor:pointer;">Launch Executable (' + escapeHtml(lastRouteAction.targetRole) + ')</button>';
          html += '</div>';
          // --------------------
          html += '</div>';
        }

        var lastLaunchAction = window.__solaceLastWorkflowLaunchAction;
        if (lastLaunchAction && lastLaunchAction.requestId === reqId && (lastLaunchAction.targetAssignmentId === active.id || lastLaunchAction.sourceAssignmentId === active.id)) {
          var exactPacketTruth =
            boundRun.basis === 'workflow-launch-session-binding' &&
            boundRun.assignmentId === lastLaunchAction.targetAssignmentId &&
            boundRun.appId === lastLaunchAction.appId &&
            boundRun.runId === lastLaunchAction.runId;

          html += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
          html += '<strong style="display:block; margin-bottom:0.2rem;">Next-Step Launch State:</strong>';
          html += 'Launched Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>';
          html += 'Launched Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>';
          html += 'Launched App: <code>' + escapeHtml(lastLaunchAction.appId) + '</code><br/>';
          html += 'Launched Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>';
          html += 'Launch Basis: <code>Workflow-bound routed assignment launch via real runtime run path (SAC76)</code><br/>';

          // --- SAC77 Output ---
          html += '<strong style="display:block; margin-top:0.3rem; margin-bottom:0.2rem;">Next-Step Inbox Packet State:</strong>';
          html += 'Packet Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>';
          html += 'Packet Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>';
          if (payloadExists && exactPacketTruth) {
            html += '<a href="/api/v1/apps/' + boundRun.appId + '/runs/' + boundRun.runId + '/artifact/payload.json" target="_blank" style="color:#34d399; font-weight:600; font-size:0.65rem;">[↗ View Inbox Packet (payload.json)]</a><br/>';
            html += 'Packet Basis: <code>Workflow-bound launched assignment packet via exact launched run artifact (SAC77)</code>';
          } else if (payloadExists) {
            html += '<a href="/api/v1/apps/' + boundRun.appId + '/runs/' + boundRun.runId + '/artifact/payload.json" target="_blank" style="color:#fcd34d; font-weight:600; font-size:0.65rem;">[↗ View Inbox Packet (payload.json)]</a><br/>';
            html += 'Packet Basis: <code>Payload artifact is visible, but current workflow binding fell back away from exact launched next-step run truth (SAC77/SAC78)</code>';
          } else {
            html += '<span style="color:#64748b; font-size:0.65rem;">[No Inbox Packet]</span><br/>';
            html += 'Packet Basis: <code>Workflow-bound launched assignment selected, but payload artifact missing for launched run (SAC77)</code>';
          }
          // --------------------

          // --- SAC79 Output ---
          html += '<strong style="display:block; margin-top:0.4rem; margin-bottom:0.2rem; color:#60a5fa;">Next-Step Packet Provenance & Handoff Truth:</strong>';
          html += '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #60a5fa; border-radius:0.15rem; font-size:0.65rem;">';
          html += 'Source Request ID: <code>' + escapeHtml(lastLaunchAction.requestId.substring(0,8)) + '</code><br/>';
          if (lastLaunchAction.sourceAssignmentId) {
             html += 'Source Assignment ID: <code>' + escapeHtml(lastLaunchAction.sourceAssignmentId.substring(0,8)) + '</code><br/>';
          }
          html += 'Target Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0,8)) + '</code><br/>';
          html += 'Launched Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>';
          html += 'Launched Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>';
          
          if (exactPacketTruth) {
             html += 'Contract Integrity: <span style="color:#34d399;font-weight:600;">Exact launched-workflow handoff tracked</span><br/>';
             html += 'Contract Basis: <code>Source assignment, target assignment, launched role, and launched run remain aligned in the exact workflow-bound branch (SAC79)</code>';
          } else {
             html += 'Contract Integrity: <span style="color:#fcd34d;font-weight:600;">Fallback handoff tracked</span><br/>';
             html += 'Contract Basis: <code>Handoff remains visible, but current packet or run view has fallen back away from exact launched-workflow truth (SAC79)</code>';
          }
          html += '</div>';
          // --------------------

          // --- SAC80 Output ---
          html += '<strong style="display:block; margin-top:0.4rem; margin-bottom:0.2rem; color:#a78bfa;">Next-Step Specialist Pickup Truth:</strong>';
          html += '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #a78bfa; border-radius:0.15rem; font-size:0.65rem;">';
          html += 'Dispatched Specialist: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>';
          html += 'Pickup Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>';
          
          if (eventsExist && exactPacketTruth) {
             html += 'Pickup Status: <span style="color:#34d399;font-weight:600;">[✓] Exact launched-workflow pickup tracked</span><br/>';
             html += 'Pickup Basis: <code>Events exist for the launched next-step run, and request, assignment, role, and run remain aligned in the exact workflow-bound branch (SAC80)</code>';
          } else if (eventsExist) {
             html += 'Pickup Status: <span style="color:#fcd34d;font-weight:600;">[?] Fallback pickup tracked</span><br/>';
             html += 'Pickup Basis: <code>Events exist for a visible next-step run, but the current workflow binding has fallen back away from exact launched-workflow pickup truth (SAC80)</code>';
          } else {
             html += 'Pickup Status: <span style="color:#94a3b8;font-weight:600;">[ ] Awaiting specialist pickup evidence</span><br/>';
             html += 'Pickup Basis: <code>No events exist yet for the launched next-step run, so specialist pickup is not proven in the workflow branch (SAC80)</code>';
          }
          html += '</div>';
          // --------------------

          html += '</div>';
        }

        if (boundRun.basis === 'workflow-launch-session-binding') {
          html += '<strong style="display:block;margin-top:0.3rem;">Binding Basis:</strong> <code style="background:rgba(252,211,77,0.15);color:#fcd34d;padding:0.1rem 0.3rem;border-radius:0.15rem;">Run execution explicitly bound to workflow launch session state (SAC70/71/72/73/74/75/76)</code>';
        } else {
          html += '<strong style="display:block;margin-top:0.3rem;">Binding Basis:</strong> <code style="background:rgba(239,68,68,0.12);color:#fca5a5;padding:0.1rem 0.3rem;border-radius:0.15rem;">Fallback to selected run only; not durable workflow launch proof</code>';
        }
        html += '</div>';
        
        // --- SAC78 Inbox Packet Preview Box ---
        html += '<div id="dev-active-workflow-payload-preview" style="margin-top:0.5rem;"></div>';
        // --------------------------------------

        // --- SAC81 Specialist Execution Evidence Box ---
        html += '<div id="dev-active-workflow-evidence-preview" style="margin-top:0.5rem;"></div>';
        // ---------------------------------------------

        // --- SAC72 Inline Preview Box ---
        html += '<div id="dev-active-workflow-preview" style="margin-top:0.5rem;"></div>';
        // --------------------------------

        // --- SAC83 Specialist Approval Box ---
        html += '<div id="dev-active-workflow-approval-preview" style="margin-top:0.5rem;"></div>';
        // -------------------------------------
        
        content.innerHTML = html;

        // --- SAC78 Fetch Inbox Packet Preview ---
        var payloadSlot = document.getElementById('dev-active-workflow-payload-preview');
        if (payloadSlot && lastLaunchAction && lastLaunchAction.requestId === reqId && (lastLaunchAction.targetAssignmentId === active.id || lastLaunchAction.sourceAssignmentId === active.id)) {
            payloadSlot.innerHTML = '<span style="font-size:0.7rem;color:#94a3b8;">loading inbox packet preview…</span>';
            if (payloadExists) {
                fetchArtifactText(boundRun.appId, boundRun.runId, 'payload.json').then(function(res) {
                    if (!res.missing && document.getElementById('dev-active-workflow-payload-preview')) {
                        var basisBanner = exactPacketTruth
                          ? '<div style="font-size:0.65rem;color:#34d399;margin-bottom:0.25rem;">Packet Preview Basis: exact launched next-step run artifact</div>'
                          : '<div style="font-size:0.65rem;color:#fcd34d;margin-bottom:0.25rem;">Packet Preview Basis: fallback packet preview; current workflow binding is not exact launched-run truth</div>';
                        document.getElementById('dev-active-workflow-payload-preview').innerHTML = basisBanner + buildPayloadPreview(res.text, boundRun.appId, boundRun.runId);
                    } else if (document.getElementById('dev-active-workflow-payload-preview')) {
                        document.getElementById('dev-active-workflow-payload-preview').innerHTML = buildMissingState('payload.json', res.reason || 'missing');
                    }
                });
            } else {
                payloadSlot.innerHTML = buildMissingState('payload.json', 'missing for launched next-step run');
            }
        }
        // ----------------------------------------

        // --- SAC81 Fetch Specialist Execution Evidence ---
        var evidenceSlot = document.getElementById('dev-active-workflow-evidence-preview');
        if (evidenceSlot && lastLaunchAction && lastLaunchAction.requestId === reqId && (lastLaunchAction.targetAssignmentId === active.id || lastLaunchAction.sourceAssignmentId === active.id)) {
            if (eventsExist) {
                evidenceSlot.innerHTML = '<strong style="display:block; margin-top:0.4rem; color:#2dd4bf;">Next-Step Specialist Execution Evidence Truth:</strong>' +
                                         '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #2dd4bf; border-radius:0.15rem; font-size:0.65rem; margin-bottom:0.5rem;">' +
                                         'Source Request ID: <code>' + escapeHtml(lastLaunchAction.requestId.substring(0, 8)) + '</code><br/>' +
                                         (lastLaunchAction.sourceAssignmentId ? 'Source Assignment ID: <code>' + escapeHtml(lastLaunchAction.sourceAssignmentId.substring(0, 8)) + '</code><br/>' : '') +
                                         'Target Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>' +
                                         'Launched Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>' +
                                         'Launched Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>' +
                                         (exactPacketTruth 
                                            ? 'Evidence Status: <span style="color:#34d399;font-weight:600;">[✓] Exact launched-workflow execution evidence tracked</span><br/>Evidence Basis: <code>Events exist for the launched next-step run, and request, assignment, role, and run remain aligned in the exact workflow-bound branch (SAC81)</code>' 
                                            : 'Evidence Status: <span style="color:#fcd34d;font-weight:600;">[?] Fallback execution evidence tracked</span><br/>Evidence Basis: <code>Events exist for a visible next-step run, but the current workflow binding has fallen back away from exact launched-workflow execution evidence truth (SAC81)</code>') +
                                         '<div id="dev-evidence-fetch-target" style="margin-top:0.4rem;"><span style="color:#94a3b8;">loading specialist execution evidence…</span></div></div>';
                
                fetchArtifactText(boundRun.appId, boundRun.runId, 'events.jsonl').then(function(res) {
                    if (!res.missing && document.getElementById('dev-evidence-fetch-target')) {
                        document.getElementById('dev-evidence-fetch-target').innerHTML = buildEventsPreview(res.text, boundRun.appId, boundRun.runId);
                    } else if (document.getElementById('dev-evidence-fetch-target')) {
                        document.getElementById('dev-evidence-fetch-target').innerHTML = buildMissingState('events.jsonl', res.reason || 'missing');
                    }
                });
            } else {
                evidenceSlot.innerHTML = '<strong style="display:block; margin-top:0.4rem; color:#94a3b8;">Next-Step Specialist Execution Evidence Truth:</strong>' +
                                         '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #475569; border-radius:0.15rem; font-size:0.65rem; margin-bottom:0.5rem; color:#64748b;">' +
                                         'Source Request ID: <code>' + escapeHtml(lastLaunchAction.requestId.substring(0, 8)) + '</code><br/>' +
                                         (lastLaunchAction.sourceAssignmentId ? 'Source Assignment ID: <code>' + escapeHtml(lastLaunchAction.sourceAssignmentId.substring(0, 8)) + '</code><br/>' : '') +
                                         'Target Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>' +
                                         'Launched Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>' +
                                         'Launched Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>' +
                                         'Evidence Status: <span style="color:#94a3b8;font-weight:600;">[ ] Awaiting specialist execution evidence</span><br/><code>No events.jsonl artifact exists yet for the launched next-step run, so specialist execution is not proven in the workflow branch (SAC81)</code></div>';
            }
        }
        // -------------------------------------------------

        // --- SAC82 Fetch Specialist Output Truth ---
        var previewSlot = document.getElementById('dev-active-workflow-preview');
        if (previewSlot && lastLaunchAction && lastLaunchAction.requestId === reqId && (lastLaunchAction.targetAssignmentId === active.id || lastLaunchAction.sourceAssignmentId === active.id)) {
            if (reportExists) {
                previewSlot.innerHTML = '<strong style="display:block; margin-top:0.4rem; color:#f472b6;">Next-Step Specialist Output Truth:</strong>' +
                                        '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #f472b6; border-radius:0.15rem; font-size:0.65rem; margin-bottom:0.5rem;">' +
                                        'Source Request ID: <code>' + escapeHtml(lastLaunchAction.requestId.substring(0, 8)) + '</code><br/>' +
                                        (lastLaunchAction.sourceAssignmentId ? 'Source Assignment ID: <code>' + escapeHtml(lastLaunchAction.sourceAssignmentId.substring(0, 8)) + '</code><br/>' : '') +
                                        'Target Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>' +
                                        'Launched Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>' +
                                        'Launched Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>' +
                                        (exactPacketTruth 
                                           ? 'Output Status: <span style="color:#34d399;font-weight:600;">[✓] Exact launched-workflow output tracked</span><br/>Output Basis: <code>Report output exists for the launched next-step run, and request, assignment, role, and run remain aligned in the exact workflow-bound branch (SAC82)</code>' 
                                           : 'Output Status: <span style="color:#fcd34d;font-weight:600;">[?] Fallback output tracked</span><br/>Output Basis: <code>Report output exists for a visible next-step run, but the current workflow binding has fallen back away from exact launched-workflow output truth (SAC82)</code>') +
                                        '<div id="dev-output-fetch-target" style="margin-top:0.4rem;"><span style="color:#94a3b8;">loading specialist output truth…</span></div></div>';
                
                fetchArtifactText(boundRun.appId, boundRun.runId, 'report.html').then(function(res) {
                    if (!res.missing && document.getElementById('dev-output-fetch-target')) {
                        document.getElementById('dev-output-fetch-target').innerHTML = buildReportPreview(res.text, boundRun.appId, boundRun.runId);
                    } else if (document.getElementById('dev-output-fetch-target')) {
                        document.getElementById('dev-output-fetch-target').innerHTML = buildMissingState('report.html', res.reason || 'missing');
                    }
                });
            } else {
                previewSlot.innerHTML = '<strong style="display:block; margin-top:0.4rem; color:#94a3b8;">Next-Step Specialist Output Truth:</strong>' +
                                        '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #475569; border-radius:0.15rem; font-size:0.65rem; margin-bottom:0.5rem; color:#64748b;">' +
                                        'Source Request ID: <code>' + escapeHtml(lastLaunchAction.requestId.substring(0, 8)) + '</code><br/>' +
                                        (lastLaunchAction.sourceAssignmentId ? 'Source Assignment ID: <code>' + escapeHtml(lastLaunchAction.sourceAssignmentId.substring(0, 8)) + '</code><br/>' : '') +
                                        'Target Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>' +
                                        'Launched Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>' +
                                        'Launched Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>' +
                                        'Output Status: <span style="color:#94a3b8;font-weight:600;">[ ] Awaiting specialist output truth</span><br/><code>No report.html artifact exists yet for the launched next-step run, so specialist output is not proven in the workflow branch (SAC82)</code></div>';
            }
        } else if (previewSlot) {
            // SAC72 Fallback Fetch Preview
            if (reportExists) {
                previewSlot.innerHTML = '<span style="font-size:0.7rem;color:#94a3b8;">loading report preview…</span>';
                fetchArtifactText(boundRun.appId, boundRun.runId, 'report.html').then(function(res) {
                    if (!res.missing && document.getElementById('dev-active-workflow-preview')) {
                        document.getElementById('dev-active-workflow-preview').innerHTML = buildReportPreview(res.text, boundRun.appId, boundRun.runId);
                    } else if (document.getElementById('dev-active-workflow-preview')) {
                        document.getElementById('dev-active-workflow-preview').innerHTML = '<span style="font-size:0.65rem;color:#fca5a5;">preview unavailable</span>';
                    }
                });
            }
        }
        // ---------------------------------------------

        // --- SAC83 Next-Step Specialist Approval Truth ---
        var approvalSlot = document.getElementById('dev-active-workflow-approval-preview');
        if (approvalSlot && lastLaunchAction && lastLaunchAction.requestId === reqId && (lastLaunchAction.targetAssignmentId === active.id || lastLaunchAction.sourceAssignmentId === active.id)) {
            var targetApproval = approvals.find(function(item) { return item.assignment_id === lastLaunchAction.targetAssignmentId; }) || null;
            
            var appHtml = '<strong style="display:block; margin-top:0.4rem; color:#818cf8;">Next-Step Specialist Approval Truth:</strong>';
            appHtml += '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #818cf8; border-radius:0.15rem; font-size:0.65rem; margin-bottom:0.5rem;">';
            appHtml += 'Source Request ID: <code>' + escapeHtml(lastLaunchAction.requestId.substring(0, 8)) + '</code><br/>';
            if (lastLaunchAction.sourceAssignmentId) {
                appHtml += 'Source Assignment ID: <code>' + escapeHtml(lastLaunchAction.sourceAssignmentId.substring(0, 8)) + '</code><br/>';
            }
            appHtml += 'Target Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>';
            appHtml += 'Launched Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>';
            appHtml += 'Launched Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>';
            
            if (targetApproval) {
                var color = targetApproval.status === 'approved' ? '#6ee7b7' : (targetApproval.status === 'rejected' ? '#fca5a5' : '#fcd34d');
                appHtml += 'Signoff State: <span class="sb-pill" style="color:' + color + '; border:1px solid ' + color + '; font-size:0.65rem; margin-right:0.3rem;">' + escapeHtml(targetApproval.status) + '</span>';
                if (targetApproval.notes) {
                    appHtml += '<span style="color:var(--sb-text-muted);">' + escapeHtml(targetApproval.notes) + '</span><br/>';
                } else {
                    appHtml += '<br/>';
                }
            } else {
                appHtml += 'Signoff State: <span class="sb-pill" style="color:#94a3b8; border:1px dashed #475569; font-size:0.65rem;">pending workflow signoff</span><br/>';
            }
            
            if (exactPacketTruth) {
                appHtml += 'Approval Branch: <span style="color:#34d399;font-weight:600;">[✓] Exact launched-workflow approval branch tracked</span><br/>';
                appHtml += 'Approval Basis: <code>Approval state is read for the launched target assignment, and request, assignment, role, and run remain aligned in the exact workflow-bound branch (SAC83)</code>';
            } else {
                appHtml += 'Approval Branch: <span style="color:#fcd34d;font-weight:600;">[?] Fallback approval branch tracked</span><br/>';
                appHtml += 'Approval Basis: <code>Approval state is visible for a matching assignment, but the current workflow binding has fallen back away from exact launched-workflow approval truth (SAC83)</code>';
            }
            appHtml += '</div>';

            // --- SAC84 Generate Approval Actions ---
            var targetLinkedId = targetApproval ? targetApproval.id : '';
            appHtml += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
            appHtml += '<strong style="display:block; margin-bottom:0.2rem;">Next-Step Approval Action:</strong>';
            appHtml += 'Action Target Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>';
            appHtml += 'Action Target Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>';
            appHtml += 'Action Target Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>';
            appHtml += '<div style="display:flex; gap:0.3rem; margin-bottom:0.3rem;">';
            appHtml += '<button onclick="window.__solaceSignoffWorkflow(\'' + lastLaunchAction.targetAssignmentId + '\', \'' + targetLinkedId + '\', \'approved\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#064e3b;color:#34d399;font-weight:600;border:1px solid #059669;cursor:pointer;">Approve Target</button>';
            appHtml += '<button onclick="window.__solaceSignoffWorkflow(\'' + lastLaunchAction.targetAssignmentId + '\', \'' + targetLinkedId + '\', \'rejected\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#4c0519;color:#fca5a5;border:1px solid #e11d48;cursor:pointer;">Reject Target</button>';
            appHtml += '</div>';
            if (exactPacketTruth) {
                appHtml += 'Action Basis: <code>Approval action will ' + (targetLinkedId ? 'update' : 'create') + ' the approval row for the launched target assignment while request, assignment, role, and run remain aligned in the exact workflow-bound branch (SAC84)</code>';
            } else {
                appHtml += 'Action Basis: <code>Approval action targets the visible matching assignment, but the current workflow binding has fallen back away from exact launched-workflow approval action truth (SAC84)</code>';
            }
            appHtml += '</div>';

            // --- SAC85 Next-Step Approval Result Truth ---
            var lastSignoffResult = window.__solaceLastWorkflowSignoffActionResult;
            if (lastSignoffResult && lastSignoffResult.requestId === reqId && lastSignoffResult.assignmentId === lastLaunchAction.targetAssignmentId) {
                appHtml += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
                appHtml += '<strong style="display:block; margin-bottom:0.2rem; color:#f87171;">Next-Step Approval Mutation Result:</strong>';
                appHtml += '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #f87171; border-radius:0.15rem; font-size:0.65rem;">';
                appHtml += 'Target Assignment ID: <code>' + escapeHtml(lastSignoffResult.assignmentId.substring(0, 8)) + '</code><br/>';
                if (lastSignoffResult.targetRole) {
                    appHtml += 'Result Target Role: <code>' + escapeHtml(lastSignoffResult.targetRole) + '</code><br/>';
                }
                if (lastSignoffResult.runId) {
                    appHtml += 'Result Target Run ID: <code>' + escapeHtml(lastSignoffResult.runId.substring(0, 8)) + '</code><br/>';
                }
                appHtml += 'Requested Status: <code>' + escapeHtml(lastSignoffResult.status) + '</code><br/>';
                appHtml += 'Mutation Mode: <code>' + escapeHtml(lastSignoffResult.mutation) + '</code><br/>';
                
                if (lastSignoffResult.success) {
                    appHtml += 'Mutation Status: <span style="color:#6ee7b7;font-weight:600;">[✓] Target approval successfully written to Back Office</span><br/>';
                    if (exactPacketTruth) {
                        appHtml += 'Result Branch: <span style="color:#34d399;font-weight:600;">[✓] Exact launched-workflow approval result tracked</span><br/>';
                        appHtml += 'Result Basis: <code>Approval action wrote successfully for the launched target assignment, and request, assignment, role, and run remain aligned in the exact workflow-bound branch (SAC85)</code>';
                    } else {
                        appHtml += 'Result Branch: <span style="color:#fcd34d;font-weight:600;">[?] Fallback approval result tracked</span><br/>';
                        appHtml += 'Result Basis: <code>Approval action wrote successfully for a visible matching assignment, but the current workflow binding has fallen back away from exact launched-workflow approval result truth (SAC85)</code>';
                    }
                } else {
                    appHtml += 'Mutation Status: <span style="color:#fca5a5;font-weight:600;">[✗] Target approval write failed</span><br/>';
                    if (exactPacketTruth) {
                        appHtml += 'Result Branch: <span style="color:#fca5a5;font-weight:600;">[!] Exact launched-workflow approval result failed</span><br/>';
                        appHtml += 'Result Basis: <code>Approval action failed for the launched target assignment while request, assignment, role, and run remained aligned in the exact workflow-bound branch (SAC85)</code>';
                    } else {
                        appHtml += 'Result Branch: <span style="color:#fca5a5;font-weight:600;">[!] Fallback approval result failed</span><br/>';
                        appHtml += 'Result Basis: <code>Approval action failed for a visible matching assignment after the current workflow binding had already fallen back away from exact launched-workflow truth (SAC85)</code>';
                    }
                }
                appHtml += '</div></div>';

                // --- SAC86 Next-Step Destination Truth ---
                var targetRouteAction = window.__solaceLastWorkflowRouteAction;
                if (targetRouteAction && targetRouteAction.requestId === reqId && targetRouteAction.sourceAssignmentId === lastLaunchAction.targetAssignmentId) {
                    appHtml += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
                    appHtml += '<strong style="display:block; margin-bottom:0.2rem; color:#a78bfa;">Next-Step Destination Truth:</strong>';
                    appHtml += '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #a78bfa; border-radius:0.15rem; font-size:0.65rem;">';
                    appHtml += 'Source Request ID: <code>' + escapeHtml(reqId.substring(0, 8)) + '</code><br/>';
                    appHtml += 'Source Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>';
                    appHtml += 'Source Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>';
                    appHtml += 'Source Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>';
                    appHtml += 'Destination Target Role: <code>' + escapeHtml(targetRouteAction.targetRole) + '</code><br/>';
                    if (targetRouteAction.assignmentId) {
                        appHtml += 'Destination Assignment ID: <code>' + escapeHtml(targetRouteAction.assignmentId.substring(0, 8)) + '</code><br/>';
                    }
                    appHtml += 'Destination Mutation Mode: <code>' + escapeHtml(targetRouteAction.mutation) + '</code><br/>';
                    if (exactPacketTruth) {
                        appHtml += 'Destination Branch: <span style="color:#34d399;font-weight:600;">[✓] Exact launched-workflow destination branch tracked</span><br/>';
                        appHtml += 'Destination Basis: <code>Workflow routed destination branch ' + escapeHtml(targetRouteAction.mutation) + ' while request, assignment, role, and run remained aligned in the exact workflow-bound branch (SAC86)</code>';
                    } else {
                        appHtml += 'Destination Branch: <span style="color:#fcd34d;font-weight:600;">[?] Fallback destination branch tracked</span><br/>';
                        appHtml += 'Destination Basis: <code>Workflow routed destination branch ' + escapeHtml(targetRouteAction.mutation) + ' for a visible matching assignment, but the current workflow binding has fallen back away from exact launched-workflow destination truth (SAC86)</code>';
                    }
                    appHtml += '</div>';
                    
                    appHtml += '<div style="margin-top:0.3rem; display:flex; gap:0.3rem;">';
                    appHtml += '<button onclick="window.__solaceLaunchWorkflowNextStep(\'' + targetRouteAction.sourceAssignmentId + '\', \'' + escapeHtml(targetRouteAction.targetRole) + '\', \'' + escapeHtml(targetRouteAction.assignmentId || '') + '\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#0f172a;color:#fff;border:1px solid #3b82f6;cursor:pointer;">Launch Executable Destination (' + escapeHtml(targetRouteAction.targetRole) + ')</button>';
                    appHtml += '</div></div>';

                    // --- SAC87 Next-Step Destination Launch Truth ---
                    var nestedLaunchAction = window.__solaceLastWorkflowNestedLaunchAction;
                    if (
                        nestedLaunchAction &&
                        nestedLaunchAction.requestId === reqId &&
                        nestedLaunchAction.sourceAssignmentId === lastLaunchAction.targetAssignmentId &&
                        nestedLaunchAction.targetAssignmentId === targetRouteAction.assignmentId &&
                        nestedLaunchAction.targetRole === targetRouteAction.targetRole
                    ) {
                        appHtml += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
                        appHtml += '<strong style="display:block; margin-bottom:0.2rem; color:#60a5fa;">Next-Step Destination Launch Truth:</strong>';
                        appHtml += '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #60a5fa; border-radius:0.15rem; font-size:0.65rem;">';
                        appHtml += 'Nested Source Request ID: <code>' + escapeHtml(nestedLaunchAction.requestId.substring(0, 8)) + '</code><br/>';
                        appHtml += 'Nested Source Assignment ID: <code>' + escapeHtml(nestedLaunchAction.sourceAssignmentId.substring(0, 8)) + '</code><br/>';
                        if (nestedLaunchAction.sourceRole) {
                            appHtml += 'Nested Source Role: <code>' + escapeHtml(nestedLaunchAction.sourceRole) + '</code><br/>';
                        }
                        if (nestedLaunchAction.sourceRunId) {
                            appHtml += 'Nested Source Run ID: <code>' + escapeHtml(nestedLaunchAction.sourceRunId.substring(0, 8)) + '</code><br/>';
                        }
                        appHtml += 'Nested Target Assignment ID: <code>' + escapeHtml(nestedLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>';
                        appHtml += 'Nested Launched Role: <code>' + escapeHtml(nestedLaunchAction.targetRole) + '</code><br/>';
                        appHtml += 'Nested Launched Run ID: <code>' + escapeHtml(nestedLaunchAction.runId.substring(0, 8)) + '</code><br/>';
                        if (exactPacketTruth) {
                            appHtml += 'Destination Launch Branch: <span style="color:#34d399;font-weight:600;">[✓] Exact launched-workflow destination launch tracked</span><br/>';
                            appHtml += 'Destination Launch Basis: <code>Workflow launched the routed destination assignment while request, source assignment, target assignment, role, and run remained aligned in the exact launched-workflow branch (SAC87)</code>';
                        } else {
                            appHtml += 'Destination Launch Branch: <span style="color:#fcd34d;font-weight:600;">[?] Fallback destination launch tracked</span><br/>';
                            appHtml += 'Destination Launch Basis: <code>Workflow launched a visible matching destination assignment, but the current workflow binding has fallen back away from exact launched-workflow destination launch truth (SAC87)</code>';
                        }
                        appHtml += '</div></div>';
                    } else {
                        appHtml += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
                        appHtml += '<strong style="display:block; margin-bottom:0.2rem; color:#60a5fa;">Next-Step Destination Launch Truth:</strong>';
                        appHtml += '<div style="background:rgba(30,41,59,0.5); padding:0.4rem; border-left:2px solid #60a5fa; border-radius:0.15rem; font-size:0.65rem;">';
                        appHtml += 'Nested Source Request ID: <code>' + escapeHtml(reqId.substring(0, 8)) + '</code><br/>';
                        appHtml += 'Nested Source Assignment ID: <code>' + escapeHtml(lastLaunchAction.targetAssignmentId.substring(0, 8)) + '</code><br/>';
                        appHtml += 'Nested Source Role: <code>' + escapeHtml(lastLaunchAction.targetRole) + '</code><br/>';
                        appHtml += 'Nested Source Run ID: <code>' + escapeHtml(lastLaunchAction.runId.substring(0, 8)) + '</code><br/>';
                        if (targetRouteAction.assignmentId) {
                            appHtml += 'Nested Target Assignment ID: <code>' + escapeHtml(targetRouteAction.assignmentId.substring(0, 8)) + '</code><br/>';
                        }
                        appHtml += 'Nested Launched Role: <code>' + escapeHtml(targetRouteAction.targetRole) + '</code><br/>';
                        appHtml += 'Destination Launch Branch: <span style="color:#fca5a5;font-weight:600;">[ ] Awaiting destination launch truth</span><br/>';
                        appHtml += 'Destination Launch Basis: <code>Workflow routed the destination assignment, but no exact launched destination run has been recorded for this request/source assignment/target assignment branch yet (SAC87)</code>';
                        appHtml += '</div></div>';
                    }
                    // ------------------------------------------------
                } else if (lastSignoffResult.success) {
                    appHtml += '<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #334155;">';
                    appHtml += '<strong style="display:block; margin-bottom:0.2rem; color:#a78bfa;">Route Next-Step Destination:</strong>';
                    appHtml += '<div style="display:flex; gap:0.3rem;">';
                    appHtml += '<button onclick="window.__solaceRouteWorkflowNextStep(\'' + lastLaunchAction.targetAssignmentId + '\', \'design\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#3b82f6;color:#fff;border:none;cursor:pointer;">Route Destination to Design</button>';
                    appHtml += '<button onclick="window.__solaceRouteWorkflowNextStep(\'' + lastLaunchAction.targetAssignmentId + '\', \'coder\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#10b981;color:#fff;border:none;cursor:pointer;">Route Destination to Coder</button>';
                    appHtml += '<button onclick="window.__solaceRouteWorkflowNextStep(\'' + lastLaunchAction.targetAssignmentId + '\', \'qa\')" class="sb-btn sb-btn--sm" style="font-size:0.6rem;padding:0.15rem 0.4rem;background:#f59e0b;color:#fff;border:none;cursor:pointer;">Route Destination to QA</button>';
                    appHtml += '</div></div>';
                }
                // -----------------------------------------
            }
            // ---------------------------------------------

            approvalSlot.innerHTML = appHtml;
        }
        // -------------------------------------------------
      });
    });
  }

  function hydrateDevWorkspace() {
    hydrateActiveWorkflowSelector();
    hydrateActiveWorkflowRoutes();
    hydrateActiveWorkflowResult();
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
        hydrateActiveWorkflowResult();
      });
    } else {
      showRunInspection(appId, runId, reportExists ? 'exists' : null, { events: [], count: 0, chain_valid: false }, true);
      hydrateActiveWorkflowResult();
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
  var WORKFLOW_LAUNCH_BINDING_KEY = 'solace_dev_workflow_launch_binding';

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

  function saveWorkflowLaunchBinding(requestId, assignmentId, appId, runId) {
    try {
      sessionStorage.setItem(WORKFLOW_LAUNCH_BINDING_KEY, JSON.stringify({
        requestId: requestId,
        assignmentId: assignmentId,
        appId: appId,
        runId: runId
      }));
    } catch(e) {}
  }

  function loadWorkflowLaunchBinding() {
    try {
      var raw = sessionStorage.getItem(WORKFLOW_LAUNCH_BINDING_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (parsed && parsed.requestId && parsed.assignmentId && parsed.appId && parsed.runId) {
        return parsed;
      }
    } catch(e) {}
    return null;
  }

  function clearWorkflowLaunchBinding() {
    try { sessionStorage.removeItem(WORKFLOW_LAUNCH_BINDING_KEY); } catch(e) {}
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
    updateSpecialistMemoryReuse(appId, runId);
    updateSpecialistConventionInvocation(appId, runId);
    updateSpecialistConventionDelivery(appId, runId);
    updateSpecialistConventionActivation(appId, runId);
    updateSpecialistConventionEffect(appId, runId);
    updateSpecialistConventionProof(appId, runId);
    updateSpecialistConventionTrust(appId, runId);
    updateSpecialistConventionRelease(appId, runId);
    updateSpecialistConventionRollout(appId, runId);
    updateSpecialistPostReleaseHealth(appId, runId);
    updateSpecialistPostReleaseIncident(appId, runId);
    updateSpecialistPostReleaseClosure(appId, runId);
    updateSpecialistPostReleaseEscalation(appId, runId);
    updateSpecialistPostReleaseQuarantine(appId, runId);
    updateSpecialistPostReleaseRecovery(appId, runId);
    updateSpecialistPostReleaseReturn(appId, runId);
    updateSpecialistPostReleaseSustained(appId, runId);
    updateSpecialistPostReleaseRegression(appId, runId);
    updateSpecialistPostReleaseRegressionResolution(appId, runId);
    updateSpecialistPostReleaseNextPath(appId, runId);
    updateSpecialistPostReleaseNextPathExecution(appId, runId);
    updateSpecialistPostReleaseNextPathAcknowledgment(appId, runId);
    updateSpecialistPostReleaseNextPathOwnership(appId, runId);
    updateSpecialistPostReleaseUpstreamRelease(appId, runId);
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

    Promise.all([
      get('/api/v1/backoffice/solace-dev-manager/assignments').catch(function() { return {items:[]}; }),
      get('/api/v1/backoffice/solace-dev-manager/requests').catch(function() { return {items:[]}; }),
      get('/api/v1/backoffice/solace-dev-manager/artifacts').catch(function() { return {items:[]}; }),
      get('/api/v1/backoffice/solace-dev-manager/approvals').catch(function() { return {items:[]}; })
    ]).then(function(responses) {
      var assignments = (responses[0] && responses[0].items) ? responses[0].items : [];
      var requests = (responses[1] && responses[1].items) ? responses[1].items : [];
      var artifacts = (responses[2] && responses[2].items) ? responses[2].items : [];
      var approvals = (responses[3] && responses[3].items) ? responses[3].items : [];

      var paramsRequestId = window.__solaceActiveRequestId;
      var activeAssgn = null;
      if (paramsRequestId) {
        activeAssgn = assignments.find(function(a) { return a.request_id === paramsRequestId && a.target_role === roleName; });
      } else {
        activeAssgn = assignments.find(function(a) { return a.target_role === roleName && a.status === 'active'; }) || assignments.find(function(a) { return a.target_role === roleName; });
      }
      var reqInfo = null;
      var linkedArtifact = null;
      var linkedApproval = null;
      if (activeAssgn) {
        reqInfo = requests.find(function(r) { return r.id === activeAssgn.request_id; });
        linkedArtifact = artifacts.find(function(item) { return item.assignment_id === activeAssgn.id; }) || null;
        linkedApproval = approvals.find(function(item) { return item.assignment_id === activeAssgn.id; }) || null;
      }

      var statement = '';
      var scopePolicy = 'FAIL_AND_NEW_TASK';
      var evidence = [];

      var basisHtml = '';

      if (activeAssgn && reqInfo) {
        statement = reqInfo.title + ' [' + reqInfo.ticket_type + ']: ' + activeAssgn.details;
        evidence.push('Back Office Request ID: ' + reqInfo.id.substring(0, 8));
        evidence.push('Back Office Assignment ID: ' + activeAssgn.id.substring(0, 8));
        if (linkedArtifact && linkedArtifact.file_path) {
          evidence.push('Back Office Artifact: ' + linkedArtifact.file_path);
        } else {
          evidence.push('/apps/' + appId + '/outbox/runs/' + runId + '/evidence.json');
        }
        if (linkedApproval && linkedApproval.status) {
          evidence.push('Back Office Approval: ' + linkedApproval.status);
        }
        
        if (paramsRequestId) {
          basisHtml = '<code style="background:rgba(99,102,241,0.15);color:#818cf8;">Explicitly selected request (SAC67)</code>';
        } else {
          basisHtml = '<code>runtime-backed dynamic API (SAC66)</code>';
        }
      } else {
        if (paramsRequestId) {
          statement = 'Selected Request has no valid assignment for role: ' + roleName + '. Create or route an assignment for this request.';
        } else {
          statement = 'No active Back Office assignments found for role: ' + roleName + '. Create or select an explicit request to route work into this role.';
        }
        evidence.push('None - API offline, unseeded, or unrouted');
        basisHtml = '<code style="background:rgba(239,68,68,0.1);color:#ef4444;">disconnected / fallback mock</code>';
      }

      var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';

      html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
      html += '<strong style="color:var(--sb-text-muted);">Active Assignment Context:</strong><br/>';
      html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
      html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
      html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
      html += 'Packet Basis: ' + basisHtml + '<br/>';
      if (activeAssgn) {
        html += 'Assignment ID: <code>' + escapeHtml(activeAssgn.id.substring(0, 8)) + '</code><br/>';
      }
      if (reqInfo) {
        html += 'Request ID: <code>' + escapeHtml(reqInfo.id.substring(0, 8)) + '</code><br/>';
      }
      if (linkedApproval) {
        html += 'Approval State: <code>' + escapeHtml(linkedApproval.status) + '</code><br/>';
      }
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
        if (item.indexOf('.md') > -1 || item.indexOf('.json') > -1) {
          html += '<li><code style="color:#818cf8;background:transparent;padding:0;">' + escapeHtml(item) + '</code></li>';
        } else {
          html += '<li>' + escapeHtml(item) + '</li>';
        }
      });
      html += '</ul>';
      html += '</div>';

      html += '</div>';
      
      panel.innerHTML = html;
    });
  }

  // ── SAI15: Worker Inbox/Outbox ──

  function updateWorkerInboxOutbox(appId, runId) {
    var panel = document.getElementById('dev-worker-inbox-outbox');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var color = roleColor(roleName);
    var outboxPath = '/apps/' + appId + '/outbox/runs/' + runId;

    Promise.all([
      get('/api/v1/backoffice/solace-dev-manager/assignments').catch(function(){return {items:[]};}),
      get('/api/v1/backoffice/solace-dev-manager/artifacts').catch(function(){return {items:[]};}),
      get('/api/v1/backoffice/solace-dev-manager/approvals').catch(function(){return {items:[]};})
    ]).then(function(responses) {
      var assignments = (responses[0] && responses[0].items) ? responses[0].items : [];
      var artifacts = (responses[1] && responses[1].items) ? responses[1].items : [];
      var approvals = (responses[2] && responses[2].items) ? responses[2].items : [];
      var activeAssgn = null;
      var paramsRequestId = window.__solaceActiveRequestId;
      if (paramsRequestId) {
        activeAssgn = assignments.find(function(a) { return a.request_id === paramsRequestId && a.target_role === roleName; });
      } else {
        activeAssgn = assignments.find(function(a) { return a.target_role === roleName && a.status === 'active'; }) || assignments.find(function(a) { return a.target_role === roleName; });
      }

      var linkedArtifact = null;
      var linkedApproval = null;
      if (activeAssgn) {
        linkedArtifact = artifacts.find(function(item) { return item.assignment_id === activeAssgn.id; }) || null;
        linkedApproval = approvals.find(function(item) { return item.assignment_id === activeAssgn.id; }) || null;
      }

      var inbox = [];
      var outbox = [];
      var basisHtml = '';

      if (activeAssgn) {
        if (paramsRequestId) {
          basisHtml = '<code style="background:rgba(99,102,241,0.15);color:#818cf8;">Explicitly selected request (SAC67)</code>';
        } else {
          basisHtml = '<code>runtime-backed dynamic API (SAZ66)</code>';
        }
        inbox = ['Back Office Request Parent Object', 'Back Office Assignment Object (' + activeAssgn.id.substring(0,8) + ')'];
        outbox = ['Worker Run Artifacts (' + runId + ')', 'App Outbox / Runs'];
        if (linkedArtifact && linkedArtifact.file_path) {
          outbox.unshift('Back Office Artifact Link (' + linkedArtifact.file_path + ')');
        }
        if (linkedApproval && linkedApproval.status) {
          outbox.push('Back Office Approval Status (' + linkedApproval.status + ')');
        }
      } else {
        basisHtml = '<code style="background:rgba(239,68,68,0.1);color:#ef4444;">disconnected / fallback mock</code>';
        if (roleName === 'manager') {
          inbox = ['User Request / Assignment Context', 'solace-dev-workspace.md'];
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
      }

      var html = '<div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.75rem;color:var(--sb-on-surface);">';

      html += '<div style="background:rgba(99,102,241,0.08);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
      html += '<strong style="color:var(--sb-text-muted);">Active Contract Context:</strong><br/>';
      html += 'App ID: <code>' + escapeHtml(appId) + '</code><br/>';
      html += 'Role: <code>' + escapeHtml(roleName) + '</code><br/>';
      html += 'Run: <code>' + escapeHtml(runId) + '</code><br/>';
      html += 'Packet Basis: ' + basisHtml + '<br/>';
      if (activeAssgn) {
        html += 'Assignment ID: <code>' + escapeHtml(activeAssgn.id.substring(0, 8)) + '</code><br/>';
      }
      if (linkedApproval) {
        html += 'Approval Status: <code>' + escapeHtml(linkedApproval.status) + '</code><br/>';
      }
      html += 'Outbox Root: <code style="font-size:0.65rem;color:#94a3b8;">' + escapeHtml(outboxPath) + '</code>';
      html += '</div>';
      
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.4rem 0.5rem;border-radius:0.25rem;border-left:2px solid ' + color + ';">';
      html += '<strong style="color:var(--sb-text-muted);">Inbox Inputs (read-only context):</strong><br/>';
      html += '<ul style="margin:0.2rem 0 0 1rem;padding:0;color:var(--sb-on-surface);font-family:monospace;font-size:0.7rem;">';
      inbox.forEach(function(item) {
        if (item.indexOf('.md') > -1 || item.indexOf('Back Office') > -1) {
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
        } else if (item.indexOf('.md') > -1 || item.indexOf('Worker Run Artifacts') > -1) {
          html += '<li><code style="color:#818cf8;background:transparent;padding:0;">' + escapeHtml(item) + '</code></li>';
        } else {
          html += '<li>' + escapeHtml(item) + '</li>';
        }
      });
      html += '</ul>';
      html += '</div>';

      html += '</div>';
      
      panel.innerHTML = html;
    });
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

  // ── SAW42: Specialist Memory Reuse ──

  function updateSpecialistMemoryReuse(appId, runId) {
    var panel = document.getElementById('dev-specialist-memory-reuse-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Reuse records derived from SAC41 memory entry target (role-mocked; shown honestly)
    var reuseEntries = [];

    if (roleName === 'qa') {
      reuseEntries = [{
        state: 'Callable',
        memoryId: 'tests/e2e/verified-suite-v3.json',
        specialist: 'solace-qa-agent-v2',
        nextTarget: 'coder',
        reuseBasis: 'End-to-end suite is live in memory store. Automatically queued into the next Coder packet as a verification constraint.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      reuseEntries = [{
        state: 'Limited',
        memoryId: 'tmp/pending-ast-matrix.bin',
        specialist: 'solace-prime-mermaid-coder-v1.2.0',
        nextTarget: 'manager',
        reuseBasis: 'Memory object is only in Draft state. Can be manually invoked by manager for visual inspection, but blocked from autonomous specialist runs.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      reuseEntries = [{
        state: 'Blocked',
        memoryId: 'N/A',
        specialist: 'solace-ui-renderer-v1',
        nextTarget: 'N/A',
        reuseBasis: 'Memory admission was revoked. No reusable objects available for subsequent workers.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      reuseEntries = [{
        state: 'Blocked',
        memoryId: 'N/A',
        specialist: 'Unbound',
        nextTarget: 'N/A',
        reuseBasis: 'No valid memory context to make callable.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var reuseIcon = { 'Callable': '⚡', 'Limited': '⚠️', 'Blocked': '🚫' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    reuseEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (reuseIcon[entry.state] || '●') + ' ' + escapeHtml(entry.memoryId) + '</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Specialist Source:</span> <span style="font-family:monospace;font-size:0.68rem;color:#c084fc;">' + escapeHtml(entry.specialist) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Next Directive Target:</span> <span style="font-family:monospace;font-size:0.68rem;color:#60a5fa;">' + escapeHtml(entry.nextTarget) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.reuseBasis) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.memoryId + entry.nextTarget).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Reuse Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Reuse Basis: <code>visible department-memory entry -> callable convention -> next directive or worker packet</code><br/>';
    html += 'Reuse values are <em>role-derived mocks</em> until runtime packet binder is wired. ';
    html += 'Resolution Bound: <code>SI9 — Conventions as Core Product Object</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAE43: Specialist Convention Invocation ──

  function updateSpecialistConventionInvocation(appId, runId) {
    var panel = document.getElementById('dev-specialist-convention-invocation-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Invocation records derived from SAW42 reuse target (role-mocked; shown honestly)
    var invocationEntries = [];

    if (roleName === 'qa') {
      invocationEntries = [{
        state: 'Invoked',
        conventionTarget: 'tests/e2e/verified-suite-v3.json',
        nextDirective: 'SI-CODER-011: Implement Graph Routing Logic',
        invocationContext: 'Convention successfully injected into Coder inbox packet outbox/coder/inbox/packet-011.json. Execution bound.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      invocationEntries = [{
        state: 'Queued',
        conventionTarget: 'tmp/pending-ast-matrix.bin',
        nextDirective: 'SI-MGR-002: Review AST Matrix Structural Bounds',
        invocationContext: 'Draft memory queued for manual manager invocation. Awaiting SI17 oversight trigger.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      invocationEntries = [{
        state: 'Blocked',
        conventionTarget: 'N/A',
        nextDirective: 'N/A',
        invocationContext: 'No reusable memory exists to invoke. Execution route terminated.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      invocationEntries = [{
        state: 'Blocked',
        conventionTarget: 'N/A',
        nextDirective: 'N/A',
        invocationContext: 'Invalid routing path. Unbound tasks cannot generate callable conventions.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var invokeIcon = { 'Invoked': '📍', 'Queued': '⏳', 'Blocked': '🚫' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    invocationEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (invokeIcon[entry.state] || '●') + ' Routing Step</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Memory Object:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.conventionTarget) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Next Directive:</span> <span style="font-family:monospace;font-size:0.68rem;color:#60a5fa;">' + escapeHtml(entry.nextDirective) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.invocationContext) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.conventionTarget + entry.nextDirective).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Routing Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Invocation Basis: <code>callable department-memory entry -> convention invocation -> next directive or worker packet</code><br/>';
    html += 'Invocation routes are <em>role-derived mocks</em> until runtime fs binding is wired. ';
    html += 'Resolution Bound: <code>SI10 — The Solace Execution Graph</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC44: Specialist Convention Delivery Receipt ──

  function updateSpecialistConventionDelivery(appId, runId) {
    var panel = document.getElementById('dev-specialist-convention-delivery-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Delivery records derived from SAE43 routing target (role-mocked; shown honestly)
    var deliveryEntries = [];

    if (roleName === 'qa') {
      deliveryEntries = [{
        state: 'Acknowledged',
        conventionTarget: 'tests/e2e/verified-suite-v3.json',
        targetPacket: 'outbox/coder/inbox/packet-011.json',
        deliveryBasis: 'Receipt acknowledged by Coder agent runtime payload parser. Target constraint actively executing.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      deliveryEntries = [{
        state: 'Pending',
        conventionTarget: 'tmp/pending-ast-matrix.bin',
        targetPacket: 'outbox/manager/inbox/packet-002.json',
        deliveryBasis: 'Routing dispatched but receipt unacknowledged. Waiting for manager SI17 manual pickup.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      deliveryEntries = [{
        state: 'Rejected',
        conventionTarget: 'N/A',
        targetPacket: 'N/A',
        deliveryBasis: 'No routing invocation to deliver. Path broken.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      deliveryEntries = [{
        state: 'Rejected',
        conventionTarget: 'N/A',
        targetPacket: 'N/A',
        deliveryBasis: 'Invalid capability. Unbound tasks do not receive delivery acknowledgements.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var deliverIcon = { 'Acknowledged': '✔️', 'Pending': '⏳', 'Rejected': '❌' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    deliveryEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (deliverIcon[entry.state] || '●') + ' Target Receipt</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Memory Object:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.conventionTarget) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Target Packet:</span> <span style="font-family:monospace;font-size:0.68rem;color:#f472b6;">' + escapeHtml(entry.targetPacket) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.deliveryBasis) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.conventionTarget + entry.targetPacket).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Delivery Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Delivery Basis: <code>invoked convention -> target packet receipt -> execution binding acknowledgement</code><br/>';
    html += 'Receipt values are <em>role-derived mocks</em> until runtime fs binding is wired. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC45: Specialist Convention Activation & Target Execution ──

  function updateSpecialistConventionActivation(appId, runId) {
    var panel = document.getElementById('dev-specialist-convention-activation-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Activation records derived from SAC44 delivery receipt (role-mocked; shown honestly)
    var activationEntries = [];

    if (roleName === 'qa') {
      activationEntries = [{
        state: 'Active',
        conventionTarget: 'tests/e2e/verified-suite-v3.json',
        targetRuntime: 'outbox/coder/runs/c-run-20260328-999',
        activationBasis: 'Constraint bound to Coder execution loop. Test matrix natively gating task completion.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      activationEntries = [{
        state: 'Queued',
        conventionTarget: 'tmp/pending-ast-matrix.bin',
        targetRuntime: 'outbox/manager/runs/pending-eval',
        activationBasis: 'Manager runtime pending manual bootstrap. Constraint staged but dormant.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      activationEntries = [{
        state: 'Failed',
        conventionTarget: 'N/A',
        targetRuntime: 'N/A',
        activationBasis: 'No delivered payload acknowledged. Runtime constraint binding aborted.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      activationEntries = [{
        state: 'Failed',
        conventionTarget: 'N/A',
        targetRuntime: 'N/A',
        activationBasis: 'Invalid capability. Unbound tasks do not cast execution constraints.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var activeIcon = { 'Active': '⚙️', 'Queued': '⏸️', 'Failed': '❌' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    activationEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (activeIcon[entry.state] || '●') + ' Target Activation</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Memory Object:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.conventionTarget) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Target Runtime:</span> <span style="font-family:monospace;font-size:0.68rem;color:#a855f7;">' + escapeHtml(entry.targetRuntime) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.activationBasis) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.conventionTarget + entry.targetRuntime).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Activation Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Activation Basis: <code>delivered convention -> target runtime binding -> active execution constraint</code><br/>';
    html += 'Activation values are <em>role-derived mocks</em> until intelligence runtime loop is wired. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAF46: Specialist Convention Effect & Constrained Output ──

  function updateSpecialistConventionEffect(appId, runId) {
    var panel = document.getElementById('dev-specialist-convention-effect-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Effect records derived from SAC45 activation target (role-mocked; shown honestly)
    var effectEntries = [];

    if (roleName === 'qa') {
      effectEntries = [{
        state: 'Visible',
        targetRuntime: 'outbox/coder/runs/c-run-20260328-999',
        producedArtifact: 'outbox/coder/runs/c-run-20260328-999/test-matrix-results.json',
        effectBasis: 'Constrained outputs detected matching active conventions. Test assertions enforced structural layout.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      effectEntries = [{
        state: 'Partial',
        targetRuntime: 'outbox/manager/runs/pending-eval',
        producedArtifact: 'tmp/eval-staging-diff.patch',
        effectBasis: 'Runtime execution halted before structural closure. Pre-flight artifacts generated but incomplete.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      effectEntries = [{
        state: 'Absent',
        targetRuntime: 'N/A',
        producedArtifact: 'N/A',
        effectBasis: 'No active runtime identified. Unable to measure constraint efficacy.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      effectEntries = [{
        state: 'Absent',
        targetRuntime: 'N/A',
        producedArtifact: 'N/A',
        effectBasis: 'Invalid capability. Unbound tasks do not yield constrained output telemetry.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var effectIcon = { 'Visible': '✨', 'Partial': '〰️', 'Absent': '❌' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    effectEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (effectIcon[entry.state] || '●') + ' Terminal Output Footprint</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Target Runtime:</span> <span style="font-family:monospace;font-size:0.68rem;color:#a855f7;">' + escapeHtml(entry.targetRuntime) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Produced Artifact:</span> <span style="font-family:monospace;font-size:0.68rem;color:#facc15;">' + escapeHtml(entry.producedArtifact) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.effectBasis) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.targetRuntime + entry.producedArtifact).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Effect Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Effect Basis: <code>active convention -> constrained runtime -> visible artifact or output shift</code><br/>';
    html += 'Effect telemetry is <em>role-derived mocked</em> until final output parser verification is wired. ';
    html += 'Resolution Bound: <code>SI18 — Transparency as a Product Feature</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAG47: Specialist Convention Proof & Evidence Verdict ──

  function updateSpecialistConventionProof(appId, runId) {
    var panel = document.getElementById('dev-specialist-convention-proof-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Proof records derived from SAF46 effect target (role-mocked; shown honestly)
    var proofEntries = [];

    if (roleName === 'qa') {
      proofEntries = [{
        state: 'Verified',
        producedArtifact: 'outbox/coder/runs/c-run-20260328-999/test-matrix-results.json',
        proofStrategy: 'pytest --cov --strict-markers',
        evidenceVerdict: 'Output mathematically proven to satisfy convention constraints. Verification zero-knowledge check passed.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      proofEntries = [{
        state: 'Partial',
        producedArtifact: 'tmp/eval-staging-diff.patch',
        proofStrategy: 'syntax_only_validation',
        evidenceVerdict: 'Artifact syntactically valid but lacks execution proof. Structural constraints unverified.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      proofEntries = [{
        state: 'Missing',
        producedArtifact: 'N/A',
        proofStrategy: 'N/A',
        evidenceVerdict: 'No effect footprint yielded. Evidence verdict cannot be reached.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      proofEntries = [{
        state: 'Missing',
        producedArtifact: 'N/A',
        proofStrategy: 'N/A',
        evidenceVerdict: 'Invalid capability. Unbound tasks bypass evidence verification loops.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var proofIcon = { 'Verified': '🛡️', 'Partial': '⚖️', 'Missing': '❌' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    proofEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (proofIcon[entry.state] || '●') + ' Governing Evidence Verdict</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Produced Artifact:</span> <span style="font-family:monospace;font-size:0.68rem;color:#facc15;">' + escapeHtml(entry.producedArtifact) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Proof Strategy:</span> <span style="font-family:monospace;font-size:0.68rem;color:#10b981;">' + escapeHtml(entry.proofStrategy) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.evidenceVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.producedArtifact + entry.proofStrategy).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Verdict Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Proof Basis: <code>constrained output -> evidence verdict -> governed convention lineage</code><br/>';
    html += 'Proof verdicts are <em>role-derived mocks</em> until cryptographic pipeline binds. ';
    html += 'Resolution Bound: <code>SI19 — Measuring Solace System Efficiency</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAH48: Specialist Convention Trust & Release Readiness ──

  function updateSpecialistConventionTrust(appId, runId) {
    var panel = document.getElementById('dev-specialist-convention-trust-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Trust/Governance records derived from SAG47 evidence verdict (role-mocked; shown honestly)
    var trustEntries = [];

    if (roleName === 'qa') {
      trustEntries = [{
        state: 'Trusted',
        verdictLineage: 'Evidence Verdict [Verified] on outbox/coder/runs/c-run-20260328-999',
        governanceBasis: 'Cryptography bounds verified. No known physical vulnerabilities or structural drift present.',
        decisionVerdict: 'Lineage cleared for immediate promotion and systemic Department Memory admission.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      trustEntries = [{
        state: 'Provisional',
        verdictLineage: 'Evidence Verdict [Partial] on tmp/eval-staging-diff.patch',
        governanceBasis: 'Missing execution bounds validation. Component constrained to local testing sandbox only.',
        decisionVerdict: 'Lineage barred from production. Subject to explicit Human oversight constraint (SI17).',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      trustEntries = [{
        state: 'Blocked',
        verdictLineage: 'Evidence Verdict [Missing]',
        governanceBasis: 'No conclusive proof evaluated by governance mechanisms.',
        decisionVerdict: 'Lineage entirely quarantined. Run is a dead-end execution node with zero intelligence trust.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      trustEntries = [{
        state: 'Blocked',
        verdictLineage: 'N/A',
        governanceBasis: 'Invalid capability matrix.',
        decisionVerdict: 'Governance routing disconnected from worker boundaries.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var trustIcon = { 'Trusted': '🟢', 'Provisional': '🟡', 'Blocked': '🔴' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    trustEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (trustIcon[entry.state] || '●') + ' Governance Readiness Decision</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Proof Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.verdictLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Governance Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.governanceBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.decisionVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.verdictLineage + entry.decisionVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Readiness Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Trust Basis: <code>proof verdict -> governance decision -> release or promotion readiness</code><br/>';
    html += 'Trust states are <em>role-derived mocks</em> pending central hub promotion sync. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAI49: Specialist Convention Release & Manager Signoff ──

  function updateSpecialistConventionRelease(appId, runId) {
    var panel = document.getElementById('dev-specialist-convention-release-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Release Action records derived from SAH48 trust/governance (role-mocked; shown honestly)
    var releaseEntries = [];

    if (roleName === 'qa') {
      releaseEntries = [{
        state: 'Approved',
        trustLineage: 'Governance Decision [Trusted]',
        signoffBasis: 'Human Dev Manager affirmatively signed off on verification matrix and runtime proof.',
        actionVerdict: 'Physical artifact bundle formally bound to release channel and systemic runtime injection.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      releaseEntries = [{
        state: 'Pending',
        trustLineage: 'Governance Decision [Provisional]',
        signoffBasis: 'Lineage suspended in Dev Manager queue pending manual structural override or rejection.',
        actionVerdict: 'Artifact delivery gated indefinitely until SI17 human resolution.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      releaseEntries = [{
        state: 'Denied',
        trustLineage: 'Governance Decision [Blocked]',
        signoffBasis: 'Dead execution branch rejected by explicit system governance bounds.',
        actionVerdict: 'Release pipeline severed. Artifacts permanently blocked from subsequent department invocation.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      releaseEntries = [{
        state: 'Denied',
        trustLineage: 'N/A',
        signoffBasis: 'Invalid capability stack.',
        actionVerdict: 'Missing authority to propose release candidate.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var releaseIcon = { 'Approved': '✔️', 'Pending': '⏳', 'Denied': '❌' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    releaseEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (releaseIcon[entry.state] || '●') + ' Dev Manager Release Action</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Trust Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.trustLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Signoff Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.signoffBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.actionVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.trustLineage + entry.actionVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Action Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Action Basis: <code>trust verdict -> manager signoff -> release or promotion action</code><br/>';
    html += 'Release actions are <em>role-derived mocks</em> pending physical promotion wiring. ';
    html += 'Resolution Bound: <code>SI17 — Human-in-the-Loop as a First-Class System Component</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAJ50: Specialist Convention Rollout & Release Execution ──

  function updateSpecialistConventionRollout(appId, runId) {
    var panel = document.getElementById('dev-specialist-convention-rollout-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Rollout Execution records derived from SAI49 Action (role-mocked; shown honestly)
    var rolloutEntries = [];

    if (roleName === 'qa') {
      rolloutEntries = [{
        state: 'Live',
        actionLineage: 'Manager Signoff [Approved]',
        rolloutBasis: 'Approved lineage successfully applied to active production cluster.',
        executionVerdict: 'Target component successfully deployed and servicing live Solace Intelligence System traffic.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      rolloutEntries = [{
        state: 'Staged',
        actionLineage: 'Manager Signoff [Pending]',
        rolloutBasis: 'Local worker artifact pushed to pre-release mirror environment.',
        executionVerdict: 'Target component operational in staging sandbox pending final human release toggle.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      rolloutEntries = [{
        state: 'Aborted',
        actionLineage: 'Manager Signoff [Denied]',
        rolloutBasis: 'Target deployment aborted cleanly at deployment boundary.',
        executionVerdict: 'No physical system changes executed. Lineage remains isolated and dormant.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      rolloutEntries = [{
        state: 'Aborted',
        actionLineage: 'N/A',
        rolloutBasis: 'Invalid capability stack.',
        executionVerdict: 'Missing authority to execute release candidate.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var rolloutIcon = { 'Live': '🪐', 'Staged': '📦', 'Aborted': '🛑' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    rolloutEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (rolloutIcon[entry.state] || '●') + ' Deployment Execution State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Release Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.actionLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Execution Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.rolloutBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.executionVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.actionLineage + entry.executionVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Rollout Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Rollout Basis: <code>release action -> rollout execution -> live, staged, or aborted state</code><br/>';
    html += 'Rollout executions are <em>role-derived mocks</em> representing absolute systemic deployment conclusion. ';
    html += 'Resolution Bound: <code>SI18 — Transparency as a Product Feature</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAK51: Specialist Post-Release Health & Rollback ──

  function updateSpecialistPostReleaseHealth(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-health-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Post-Release Health records derived from SAJ50 Rollout (role-mocked; shown honestly)
    var healthEntries = [];

    if (roleName === 'qa') {
      healthEntries = [{
        state: 'Healthy',
        rolloutLineage: 'Execution Verdict [Live]',
        healthBasis: 'Continuous heartbeat and semantic probes returning standard operational metrics.',
        postReleaseVerdict: 'Deployed runtime component is stable and providing continuous structural value without regression.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      healthEntries = [{
        state: 'Degraded',
        rolloutLineage: 'Execution Verdict [Staged]',
        healthBasis: 'Metric latency detected in staging sandbox executing parallel ghost traffic.',
        postReleaseVerdict: 'Component exhibiting performance shear. Rollout flagged for remediation before Live promotion.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      healthEntries = [{
        state: 'Rolled Back',
        rolloutLineage: 'Execution Verdict [Aborted/Reverted]',
        healthBasis: 'Post-deployment structural panic. Automated governance bounds severed active connections.',
        postReleaseVerdict: 'Physical rollback executed. Runtime system cleanly reverted to preceding canonical state.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      healthEntries = [{
        state: 'Rolled Back',
        rolloutLineage: 'N/A',
        healthBasis: 'Missing telemetry vector.',
        postReleaseVerdict: 'No metrics exist for unreleased artifacts.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var healthIcon = { 'Healthy': '✅', 'Degraded': '⚠️', 'Rolled Back': '🚑' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    healthEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (healthIcon[entry.state] || '●') + ' Post-Release Telemetry State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Deployment Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.rolloutLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Health Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.healthBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.postReleaseVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.rolloutLineage + entry.postReleaseVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Telemetry Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Health Basis: <code>rollout execution -> ongoing telemetry -> healthy, degraded, or rolled-back state</code><br/>';
    html += 'Health metrics are <em>role-derived mocks</em> simulating continuous post-release accountability. ';
    html += 'Resolution Bound: <code>SI19 — Measuring Solace System Efficiency</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAL52: Specialist Post-Release Incident & Remediation ──

  function updateSpecialistPostReleaseIncident(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-incident-state');
    if (!panel) return;

    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';
    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Remediation records derived from SAK51 Health (role-mocked; shown honestly)
    var remediationEntries = [];

    if (roleName === 'qa') {
      remediationEntries = [{
        state: 'Mitigated',
        healthLineage: 'Telemetry Vector [Healthy]',
        incidentBasis: 'No active incident bounds currently violated.',
        remediationVerdict: 'System nominal. No remediation required.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      remediationEntries = [{
        state: 'In Progress',
        healthLineage: 'Telemetry Vector [Degraded]',
        incidentBasis: 'Active execution shear generating P2 non-fatal alert.',
        remediationVerdict: 'Remediation task dispatched to active execution loop. Temporary capacity constraints applied.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      remediationEntries = [{
        state: 'Unresolved',
        healthLineage: 'Telemetry Vector [Rolled Back]',
        incidentBasis: 'Terminal P0 panic isolated; system structural root cause remains unknown.',
        remediationVerdict: 'Incident stands open pending manual forensic analysis. Asset deployment frozen.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      remediationEntries = [{
        state: 'Unresolved',
        healthLineage: 'N/A',
        incidentBasis: 'Missing telemetry source.',
        remediationVerdict: 'Cannot verify remediation path on untracked asset.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var remediationIcon = { 'Mitigated': '🛡️', 'In Progress': '🚧', 'Unresolved': '🔥' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    remediationEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (remediationIcon[entry.state] || '●') + ' Incident Remediation State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Telemetry Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.healthLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Incident Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.incidentBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.remediationVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.healthLineage + entry.remediationVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Remediation Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Incident Basis: <code>post-release health -> remediation path -> mitigated, in-progress, or unresolved state</code><br/>';
    html += 'Incident states are <em>role-derived mocks</em> simulating operational escalation handling. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC53: Specialist Post-Release Closure & Verification ──

  function updateSpecialistPostReleaseClosure(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-closure-state');
    if (!panel) return;

    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';
    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Verification records derived from SAC52 Incident/Remediation (role-mocked; shown honestly)
    var closureEntries = [];

    if (roleName === 'qa') {
      closureEntries = [{
        state: 'Verified Closed',
        incidentLineage: 'Remediation Vector [Mitigated]',
        closureBasis: 'Continuous regression probes confirm structural stability restored.',
        closureVerdict: 'Incident remediation verifiably closed. System operations actively confirmed nominal over standard thresholds.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      closureEntries = [{
        state: 'Pending Verification',
        incidentLineage: 'Remediation Vector [In Progress]',
        closureBasis: 'Remediation pipeline actively executing. Insufficient telemetry baseline to prove stability.',
        closureVerdict: 'Closure tracking suspended pending successful long-running execution of remediation bounds.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      closureEntries = [{
        state: 'Failed Verification',
        incidentLineage: 'Remediation Vector [Unresolved]',
        closureBasis: 'Remediation attempt produced unmitigated regression in downstream capability bounds.',
        closureVerdict: 'Remediation closure rejected. Initial incident vector remains fundamentally unresolved.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      closureEntries = [{
        state: 'Failed Verification',
        incidentLineage: 'N/A',
        closureBasis: 'Missing incident tracking source.',
        closureVerdict: 'Cannot verify unauthenticated closure paths.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var closureIcon = { 'Verified Closed': '🔒', 'Pending Verification': '⏳', 'Failed Verification': '❌' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    closureEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (closureIcon[entry.state] || '●') + ' Remediation Closure State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Incident Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.incidentLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Verification Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.closureBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.closureVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.incidentLineage + entry.closureVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Closure Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Closure Basis: <code>post-release incident -> remediation verification -> verified-closed, pending-verification, or failed-verification state</code><br/>';
    html += 'Closure states are <em>role-derived mocks</em> simulating definitive incident resolution accountability. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC54: Specialist Post-Release Escalation & Reopen ──

  function updateSpecialistPostReleaseEscalation(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-escalation-state');
    if (!panel) return;

    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';
    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Escalation records derived from SAC53 Closure (role-mocked; shown honestly)
    var escalationEntries = [];

    if (roleName === 'qa') {
      escalationEntries = [{
        state: 'Under Observation',
        closureLineage: 'Verification Check [Pending Verification]',
        escalationBasis: 'Standard passive tracking loop active. Remediation under extended baseline review.',
        escalationVerdict: 'No escalation required. Asset remains safely operational under strict constraint bounds.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      escalationEntries = [{
        state: 'Reopened',
        closureLineage: 'Verification Check [Failed Verification]',
        escalationBasis: 'Closure verification falsified by recurring structural anomaly.',
        escalationVerdict: 'Incident forcibly reopened for secondary structural remediation pass. Artifact demoted.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      escalationEntries = [{
        state: 'Escalated',
        closureLineage: 'Verification Check [Failed Verification]',
        escalationBasis: 'Successive unmitigated system panics triggered maximum automated escalation ceiling.',
        escalationVerdict: 'Incident escalated to absolute override bounds. Total component quarantine enforced pending explicit manual intervention.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      escalationEntries = [{
        state: 'Under Observation',
        closureLineage: 'N/A',
        escalationBasis: 'Missing closure verification context.',
        escalationVerdict: 'Cannot escalate untracked remediation artifacts.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var escalationIcon = { 'Under Observation': '🔭', 'Reopened': '🔄', 'Escalated': '🚨' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    escalationEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (escalationIcon[entry.state] || '●') + ' Incident Escalation State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Closure Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.closureLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Escalation Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.escalationBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.escalationVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.closureLineage + entry.escalationVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Escalation Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Escalation Basis: <code>post-release closure -> reopen or escalation path -> reopened, escalated, or under-observation state</code><br/>';
    html += 'Escalation states are <em>role-derived mocks</em> simulating accountable management paths for failed remediation limits. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC55: Specialist Post-Release Quarantine & Override ──

  function updateSpecialistPostReleaseQuarantine(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-quarantine-state');
    if (!panel) return;

    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';
    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Quarantine records derived from SAC54 Escalation (role-mocked; shown honestly)
    var quarantineEntries = [];

    if (roleName === 'qa') {
      quarantineEntries = [{
        state: 'Constrained Continuation',
        escalationLineage: 'Incident Governor [Under Observation]',
        controlBasis: 'Escalation limits remain within nominal passive inspection variance.',
        controlVerdict: 'Operations permitted under strict continuous observation. No physical quarantine imposed.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      quarantineEntries = [{
        state: 'Manual Override Required',
        escalationLineage: 'Incident Governor [Reopened]',
        controlBasis: 'Forced remediation loops exceeded automated retry limits.',
        controlVerdict: 'Automated remediation frozen. Explicit human override required to resume structural changes.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      quarantineEntries = [{
        state: 'Quarantined',
        escalationLineage: 'Incident Governor [Escalated]',
        controlBasis: 'Severe terminal panic verified. Component exceeds safety threshold parameters.',
        controlVerdict: 'Asset physically quarantined. All operations halted. Rollback isolation locked.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      quarantineEntries = [{
        state: 'Quarantined',
        escalationLineage: 'N/A',
        controlBasis: 'Missing escalation context.',
        controlVerdict: 'Untracked artifacts default to strict perimeter quarantine.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var quarantineIcon = { 'Constrained Continuation': '🌐', 'Manual Override Required': '🔑', 'Quarantined': '🛑' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    quarantineEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (quarantineIcon[entry.state] || '●') + ' Incident Control State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Escalation Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.escalationLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Control Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.controlBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.controlVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.escalationLineage + entry.controlVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Control Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Control Basis: <code>post-release escalation -> control path -> quarantined, manual-override-required, or constrained-continuation state</code><br/>';
    html += 'Control states are <em>role-derived mocks</em> simulating severe operational quarantine application bounds. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAP56: Specialist Post-Release Recovery & Re-entry ──

  function updateSpecialistPostReleaseRecovery(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-recovery-state');
    if (!panel) return;

    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';
    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Recovery authorization records derived from SAO55 Control Bounds (role-mocked; shown honestly)
    var recoveryEntries = [];

    if (roleName === 'qa') {
      recoveryEntries = [{
        state: 'Authorized',
        controlLineage: 'Constraint Bound [Constrained Continuation]',
        recoveryBasis: 'Incident structurally sealed under strict extended oversight without regression.',
        recoveryVerdict: 'System authorized for full programmatic re-entry. Operational perimeter restrictions lifted.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      recoveryEntries = [{
        state: 'Staged Recovery',
        controlLineage: 'Constraint Bound [Manual Override Required]',
        recoveryBasis: 'Remediation override successfully signed. Phased unfreezing initiated.',
        recoveryVerdict: 'System authorized for partial baseline re-entry to prove live stabilization.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      recoveryEntries = [{
        state: 'Blocked',
        controlLineage: 'Constraint Bound [Quarantined]',
        recoveryBasis: 'Terminal component failure limits absolutely active.',
        recoveryVerdict: 'System re-entry categorically denied. Quarantine isolation mathematically intact.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      recoveryEntries = [{
        state: 'Blocked',
        controlLineage: 'N/A',
        recoveryBasis: 'Missing quarantine control context.',
        recoveryVerdict: 'Cannot authorize untracked artifacts for general system re-entry.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var recoveryIcon = { 'Authorized': '✅', 'Staged Recovery': '🪜', 'Blocked': '🚫' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    recoveryEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (recoveryIcon[entry.state] || '●') + ' Recovery & Re-entry State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Control Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.controlLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Recovery Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.recoveryBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.recoveryVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.controlLineage + entry.recoveryVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Authorization Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Recovery Basis: <code>post-release quarantine -> recovery path -> recovery-authorized, re-entry-blocked, or staged-recovery state</code><br/>';
    html += 'Recovery states are <em>role-derived mocks</em> simulating accounted unfreezing loops. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAQ57: Specialist Post-Release Return-to-Service Verification ──

  function updateSpecialistPostReleaseReturn(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-return-state');
    if (!panel) return;

    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';
    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Return-to-service records derived from SAP56 Recovery Authorization (role-mocked; shown honestly)
    var returnEntries = [];

    if (roleName === 'qa') {
      returnEntries = [{
        state: 'Service Restored',
        recoveryLineage: 'Authorization Gate [Authorized]',
        serviceBasis: 'Full constraint limits held securely in wild production for 24h.',
        serviceVerdict: 'Physical re-entry verified. Application service returned to nominal baseline stability with anomaly purged.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      returnEntries = [{
        state: 'Provisional Service',
        recoveryLineage: 'Authorization Gate [Staged Recovery]',
        serviceBasis: 'Initial re-entry limits held. Ongoing dynamic stress telemetry active.',
        serviceVerdict: 'Application routing active but constrained. Provisional release gating still applied to limit exposure radius.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      returnEntries = [{
        state: 'Re-entry Failed',
        recoveryLineage: 'Authorization Gate [Blocked]',
        serviceBasis: 'Terminal component blockade triggered cascading route faults during theoretical recovery simulation.',
        serviceVerdict: 'Restoration aborted defensively. Artifact permanently decommissioned. Escalating to deep architectural rewrite.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      returnEntries = [{
        state: 'Re-entry Failed',
        recoveryLineage: 'N/A',
        serviceBasis: 'Missing recovery authorization context.',
        serviceVerdict: 'Cannot verify service restoration for artifacts possessing no valid recovery permission.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var returnIcon = { 'Service Restored': '✅', 'Provisional Service': '⚠️', 'Re-entry Failed': '💥' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    returnEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (returnIcon[entry.state] || '●') + ' Return-to-Service State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Recovery Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.recoveryLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Observation Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.serviceBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.serviceVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.recoveryLineage + entry.serviceVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Service Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Service Basis: <code>post-release recovery -> service verification path -> returned-to-service, provisional-service, or re-entry-failed state</code><br/>';
    html += 'Service restoration states are <em>role-derived mocks</em> simulating accounted physical production unfreezing. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAR58: Specialist Post-Release Sustained Service Validation ──

  function updateSpecialistPostReleaseSustained(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-sustained-state');
    if (!panel) return;

    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';
    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Sustained-service records derived from SAQ57 Return-to-Service Verification (role-mocked; shown honestly)
    var sustainedEntries = [];

    if (roleName === 'qa') {
      sustainedEntries = [{
        state: 'Stable Service',
        returnLineage: 'Production Survival Gate [Service Restored]',
        sustainedBasis: 'No regression anomalies detected over extended continuous 7-day routing matrix.',
        sustainedVerdict: 'Incident entirely structurally decoupled. Component maintains perfect isolated stability.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      sustainedEntries = [{
        state: 'Regression Watch',
        returnLineage: 'Production Survival Gate [Provisional Service]',
        sustainedBasis: 'Component operational but trailing metric drift indicates mild entropy accumulation.',
        sustainedVerdict: 'System functions within specification bounds but is locked in continuous adversarial observation.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      sustainedEntries = [{
        state: 'Relapse Detected',
        returnLineage: 'Production Survival Gate [Service Restored]',
        sustainedBasis: 'Delayed structural fatigue triggered cascading fault outside initial mitigation horizon.',
        sustainedVerdict: 'Previous remediation physically fractured. Deep architectural decomposition triggered.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      sustainedEntries = [{
        state: 'Relapse Detected',
        returnLineage: 'N/A',
        sustainedBasis: 'Missing return-to-service validation context.',
        sustainedVerdict: 'Long-term stability cannot be verified against untracked artifacts.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var sustainedIcon = { 'Stable Service': '✅', 'Regression Watch': '🔭', 'Relapse Detected': '💥' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    sustainedEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (sustainedIcon[entry.state] || '●') + ' Sustained Service State</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Return Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.returnLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Sustained Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.sustainedBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.sustainedVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.returnLineage + entry.sustainedVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Validation Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Sustained Basis: <code>post-release return -> sustained-service path -> stable-service, regression-watch, or relapse-detected state</code><br/>';
    html += 'Sustained service states are <em>role-derived mocks</em> simulating prolonged network stability bounds. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC59: Specialist Post-Release Regression Response ──

  function updateSpecialistPostReleaseRegression(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-regression-state');
    if (!panel) return;

    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';
    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';

    // Regression-response records derived from SAC58 Sustained Service Validation (role-mocked; shown honestly)
    var responseEntries = [];

    if (roleName === 'qa') {
      responseEntries = [{
        state: 'Rollback Triggered',
        regressionLineage: 'Sustained Baseline [Relapse Detected]',
        responseBasis: 'Cascading fault rapidly destabilised critical data flows beyond live mitigation bounds.',
        responseVerdict: 'Immediate binary state rollback to last known stable commit. Production severed from anomaly.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      responseEntries = [{
        state: 'Live Mitigation',
        regressionLineage: 'Sustained Baseline [Regression Watch]',
        responseBasis: 'Minor latency accumulation identified before hard failure. Component metrics within patching bounds.',
        responseVerdict: 'Hotfix synthesized and deployed under live operational constraints without dropping service routing.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      responseEntries = [{
        state: 'Containment Escalated',
        regressionLineage: 'Sustained Baseline [Relapse Detected]',
        responseBasis: 'Fatal structural failure breached primary containment rings and requires cross-team architectural rebuild.',
        responseVerdict: 'Component physically quarantined. Dependency tree frozen. Escalated to Phase 0 systemic review.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      responseEntries = [{
        state: 'Containment Escalated',
        regressionLineage: 'N/A',
        responseBasis: 'Missing sustained service tracking context.',
        responseVerdict: 'Cannot authorize response paths against unknown regression events.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var responseIcon = { 'Rollback Triggered': '⏪', 'Live Mitigation': '🛠️', 'Containment Escalated': '🛑' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    responseEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (responseIcon[entry.state] || '●') + ' Physical Response Action</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Regression Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.regressionLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Decision Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.responseBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.responseVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.regressionLineage + entry.responseVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Response Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Response Basis: <code>post-release sustained-service -> regression-response path -> rollback-triggered, live-mitigation, or containment-escalated state</code><br/>';
    html += 'Regression response paths are <em>role-derived mocks</em> simulating accounted physical mitigation logic. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC60: Specialist Post-Release Regression Resolution ──

  function updateSpecialistPostReleaseRegressionResolution(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-regression-resolution-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Regression-resolution records derived from SAS59 Regression Response (role-mocked; shown honestly)
    var resolutionEntries = [];

    if (roleName === 'qa') {
      resolutionEntries = [{
        state: 'Resolved After Mitigation',
        responseLineage: 'Physical Response Gate [Live Mitigation]',
        resolutionBasis: 'Dynamic hotfix stabilised baseline metrics for 24h without requiring deep traffic severance.',
        resolutionVerdict: 'Component has successfully survived regression loop. Relapse fully cleared and mitigated.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      resolutionEntries = [{
        state: 'Staged Recovery Reopened',
        responseLineage: 'Physical Response Gate [Rollback Triggered]',
        resolutionBasis: 'Rollback stabilised production. New convention synthesized to retry resolution under partial exposure bounds.',
        resolutionVerdict: 'Artifact granted permission to re-enter Staged Recovery loops. Strict unfreezing gate re-applied.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      resolutionEntries = [{
        state: 'Architecture Reset Required',
        responseLineage: 'Physical Response Gate [Containment Escalated]',
        resolutionBasis: 'Component deemed mathematically unrecoverable under current schema. Total failure confirmed.',
        resolutionVerdict: 'Component purged from active trust matrices. Formal deep rewrite directive issued upstream.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      resolutionEntries = [{
        state: 'Architecture Reset Required',
        responseLineage: 'N/A',
        resolutionBasis: 'Missing regression response tracking context.',
        resolutionVerdict: 'Cannot resolve regressions lacking a valid physical mitigation trajectory.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var resolutionIcon = { 'Resolved After Mitigation': '✅', 'Staged Recovery Reopened': '🔄', 'Architecture Reset Required': '💥' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    resolutionEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (resolutionIcon[entry.state] || '●') + ' Regression Resolution Gate</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Response Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.responseLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Decision Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.resolutionBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.resolutionVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.responseLineage + entry.resolutionVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Resolution Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Resolution Basis: <code>post-release regression-response -> regression-resolution path -> resolved-after-mitigation, staged-recovery-reopened, or architecture-reset-required state</code><br/>';
    html += 'Regression resolution paths are <em>role-derived mocks</em> simulating closure of physical response loops. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC61: Specialist Post-Release Next-Path Decision ──

  function updateSpecialistPostReleaseNextPath(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-next-path-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Next-path records derived from SAC60 Regression Resolution (role-mocked; shown honestly)
    var nextPathEntries = [];

    if (roleName === 'qa') {
      nextPathEntries = [{
        state: 'Clean Exit',
        resolutionLineage: 'Resolution Closure Gate [Resolved After Mitigation]',
        nextPathBasis: 'Anomaly conclusively severed. Incident pipeline fully terminated and locked.',
        nextPathVerdict: 'Return component to standard general-availability routing execution queue. Mission accomplished.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      nextPathEntries = [{
        state: 'Bounded Recovery Re-entry',
        resolutionLineage: 'Resolution Closure Gate [Staged Recovery Reopened]',
        nextPathBasis: 'Component stabilised via rollback but remains flagged for operational jitter.',
        nextPathVerdict: 'Route component explicitly back into phase one constraint testing. Unfreezing loop resets to zero.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      nextPathEntries = [{
        state: 'Architecture Reset Dispatch',
        resolutionLineage: 'Resolution Closure Gate [Architecture Reset Required]',
        nextPathBasis: 'Component permanently purged from production trust matrices due to unresolvable cascading faults.',
        nextPathVerdict: 'Dispatch formal rewrite convention to Dev swarm. Initiate zero-trust rebuild phase immediately.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      nextPathEntries = [{
        state: 'Architecture Reset Dispatch',
        resolutionLineage: 'N/A',
        nextPathBasis: 'Missing regression resolution tracking context.',
        nextPathVerdict: 'Cannot authorize clean exits lacking formal mitigation closure paths.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var nextPathIcon = { 'Clean Exit': '🏁', 'Bounded Recovery Re-entry': '⭕', 'Architecture Reset Dispatch': '💥' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    nextPathEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (nextPathIcon[entry.state] || '●') + ' Terminal Next-Path Gate</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Resolution Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.resolutionLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Terminal Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.nextPathBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.nextPathVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.resolutionLineage + entry.nextPathVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Next-Path Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Next-Path Basis: <code>post-release regression-resolution -> next-path decision -> clean-exit, bounded-recovery-reentry, or architecture-reset-dispatch state</code><br/>';
    html += 'Next-path decisions are <em>role-derived mocks</em> simulating terminal execution routing. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC62: Specialist Post-Release Next-Path Execution ──

  function updateSpecialistPostReleaseNextPathExecution(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-next-path-execution-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Next-path execution records derived from SAC61 Next-Path Decision (role-mocked; shown honestly)
    var executionEntries = [];

    if (roleName === 'qa') {
      executionEntries = [{
        state: 'Execution Confirmed',
        decisionLineage: 'Terminal Routing Gate [Clean Exit]',
        executionBasis: 'General Availability routing node acknowledged command. Traffic flowing smoothly.',
        executionVerdict: 'Terminal path physically executed. Artifact firmly re-integrated into production operations.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      executionEntries = [{
        state: 'Execution Queued',
        decisionLineage: 'Terminal Routing Gate [Bounded Recovery Re-entry]',
        executionBasis: 'Staged Recovery node is currently syncing baseline metrics before accepting new constraint inputs.',
        executionVerdict: 'Command verified and queued by receiving node. Awaiting formal Phase 1 lockdown acknowledgment.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      executionEntries = [{
        state: 'Execution Blocked',
        decisionLineage: 'Terminal Routing Gate [Architecture Reset Dispatch]',
        executionBasis: 'Target Dev Swarm offline or unable to explicitly lock reset manifest. Dispatch rejected.',
        executionVerdict: 'Network blocked terminal reset command. Incident closure suspended pending manual topological override.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      executionEntries = [{
        state: 'Execution Blocked',
        decisionLineage: 'N/A',
        executionBasis: 'Missing next-path decision context.',
        executionVerdict: 'Cannot execute physical routing without a validated upstream incident closure command.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var executionIcon = { 'Execution Confirmed': '⚡', 'Execution Queued': '⏳', 'Execution Blocked': '🛑' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    executionEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (executionIcon[entry.state] || '●') + ' Terminal Execution Gate</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Decision Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.decisionLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Network Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.executionBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.executionVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.decisionLineage + entry.executionVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Execution Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Execution Basis: <code>post-release next-path decision -> next-path execution -> execution-confirmed, execution-queued, or execution-blocked state</code><br/>';
    html += 'Next-path execution checks are <em>role-derived mocks</em> simulating physical network acknowledgment. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC63: Specialist Post-Release Next-Path Acknowledgment ──

  function updateSpecialistPostReleaseNextPathAcknowledgment(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-next-path-acknowledgment-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Next-path acknowledgment records derived from SAC62 Next-Path Execution (role-mocked; shown honestly)
    var acknowledgmentEntries = [];

    if (roleName === 'qa') {
      acknowledgmentEntries = [{
        state: 'Routing Acknowledged',
        executionLineage: 'Terminal Execution Gate [Execution Confirmed]',
        acknowledgmentBasis: 'Target swarm explicitly claimed ownership of the component state handoff.',
        acknowledgmentVerdict: 'Downstream node successfully ingested artifact. Incident routing loop permanently closed.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      acknowledgmentEntries = [{
        state: 'Routing Deferred',
        executionLineage: 'Terminal Execution Gate [Execution Queued]',
        acknowledgmentBasis: 'Target subsystem is currently at capacity or processing higher-priority constraint baselines.',
        acknowledgmentVerdict: 'Target node deferred immediate handoff. Handoff command held in queue until subsystem clears.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      acknowledgmentEntries = [{
        state: 'Routing Rejected',
        executionLineage: 'Terminal Execution Gate [Execution Blocked]',
        acknowledgmentBasis: 'Target architecture builder explicitly rejected the component due to schema mismatches or terminal entropy.',
        acknowledgmentVerdict: 'Subsystem refused ownership. Incident must escalate back to manual review board for manual re-routing.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      acknowledgmentEntries = [{
        state: 'Routing Rejected',
        executionLineage: 'N/A',
        acknowledgmentBasis: 'Missing next-path execution context.',
        acknowledgmentVerdict: 'Cannot verify target routing subsystem handoff without a valid upstream execution command.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var acknowledgmentIcon = { 'Routing Acknowledged': '🤝', 'Routing Deferred': '💤', 'Routing Rejected': '🚫' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    acknowledgmentEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (acknowledgmentIcon[entry.state] || '●') + ' Target Acknowledgment Gate</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Execution Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.executionLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Subsystem Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.acknowledgmentBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.acknowledgmentVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.executionLineage + entry.acknowledgmentVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Acknowledgment Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Acknowledgment Basis: <code>post-release next-path execution -> next-path acknowledgment -> routing-acknowledged, routing-deferred, or routing-rejected state</code><br/>';
    html += 'Next-path acknowledgment states are <em>role-derived mocks</em> simulating target subsystem ownership reception. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAC64: Specialist Post-Release Next-Path Ownership ──

  function updateSpecialistPostReleaseNextPathOwnership(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-next-path-ownership-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Next-path ownership records derived from SAC63 Next-Path Acknowledgment (role-mocked; shown honestly)
    var ownershipEntries = [];

    if (roleName === 'qa') {
      ownershipEntries = [{
        state: 'Ownership Settled',
        acknowledgmentLineage: 'Target Acknowledgment Gate [Routing Acknowledged]',
        ownershipBasis: 'General Availability pool successfully linked internal artifact pointers and assumed load-bearing duty.',
        ownershipVerdict: 'Architectural settlement complete. Upstream nodes are explicitly authorized to drop local memory buffers.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      ownershipEntries = [{
        state: 'Ownership Pending',
        acknowledgmentLineage: 'Target Acknowledgment Gate [Routing Deferred]',
        ownershipBasis: 'Staged Recovery queue holds the artifact but the target environment is not yet live-routing traffic to it.',
        ownershipVerdict: 'Settlement suspended. Upstream nodes must retain memory buffers until target cluster officially activates the artifact.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      ownershipEntries = [{
        state: 'Ownership Bounced',
        acknowledgmentLineage: 'Target Acknowledgment Gate [Routing Rejected]',
        ownershipBasis: 'Dev Swarm builder explicitly refused to cache or integrate the dispatched artifact state.',
        ownershipVerdict: 'Settlement failed. Artifact ownership bounced back to upstream Incident Management queue. Relapse loop re-opened.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      ownershipEntries = [{
        state: 'Ownership Bounced',
        acknowledgmentLineage: 'N/A',
        ownershipBasis: 'Missing next-path acknowledgment context.',
        ownershipVerdict: 'Cannot verify permanent residency settlement without a validated upstream acknowledgment handoff.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var ownershipIcon = { 'Ownership Settled': '🏰', 'Ownership Pending': '⛺', 'Ownership Bounced': '🏓' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    ownershipEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (ownershipIcon[entry.state] || '●') + ' Target Settlement Gate</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Acknowledgment Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.acknowledgmentLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Residency Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.ownershipBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.ownershipVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.acknowledgmentLineage + entry.ownershipVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Settlement Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Ownership Basis: <code>post-release next-path acknowledgment -> next-path ownership -> ownership-settled, ownership-pending, or ownership-bounced state</code><br/>';
    html += 'Next-path ownership states are <em>role-derived mocks</em> simulating explicit architectural settlement verification. ';
    html += 'Resolution Bound: <code>SI21 — The Solace Intelligence System</code>.';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
  }

  // ── SAY65: Specialist Post-Release Upstream Release ──

  // ── SAC65: Specialist Post-Release Upstream Release ──

  function updateSpecialistPostReleaseUpstreamRelease(appId, runId) {
    var panel = document.getElementById('dev-specialist-post-release-upstream-release-state');
    if (!panel) return;

    var role = DEV_ROLES.find(function(r) { return r.id === appId; });
    var roleName = role ? role.key : 'unknown';
    var viewerRole = 'solace-dev-manager';
    var selectedWorker = appId || 'unknown';
    var selectedRun = runId || 'latest';

    // Upstream release records derived from SAC64 Next-Path Ownership (role-mocked; shown honestly)
    var releaseEntries = [];

    if (roleName === 'qa') {
      releaseEntries = [{
        state: 'Custody Released',
        ownershipLineage: 'Target Settlement Gate [Ownership Settled]',
        releaseBasis: 'Target settlement achieved. Local fallback buffers and quarantine metadata officially purged.',
        releaseVerdict: 'Upstream incident tracking explicitly cleanly terminated. Full architectural memory flushed.',
        color: '#10b981',
        bg: 'rgba(16,185,129,0.1)'
      }];
    } else if (roleName === 'coder') {
      releaseEntries = [{
        state: 'Custody Retained',
        ownershipLineage: 'Target Settlement Gate [Ownership Pending]',
        releaseBasis: 'Target queue accepted handoff but has not booted artifact natively. Backup buffers remain locked.',
        releaseVerdict: 'Upstream memory explicitly retained. Incident tracking paused pending target operational activation.',
        color: '#f59e0b',
        bg: 'rgba(245,158,11,0.1)'
      }];
    } else if (roleName === 'design') {
      releaseEntries = [{
        state: 'Custody Re-armed',
        ownershipLineage: 'Target Settlement Gate [Ownership Bounced]',
        releaseBasis: 'Target explicitly refused residency. Artifact was physically bounced back to local incident loop.',
        releaseVerdict: 'Upstream memory physically re-armed. Investigation and mitigation loops fully forcefully restarted.',
        color: '#ef4444',
        bg: 'rgba(239,68,68,0.1)'
      }];
    } else {
      releaseEntries = [{
        state: 'Custody Re-armed',
        ownershipLineage: 'N/A',
        releaseBasis: 'Missing next-path ownership context.',
        releaseVerdict: 'Cannot clear upstream local memory buffers without explicitly confirmed architectural residency downstream.',
        color: '#64748b',
        bg: 'rgba(100,116,139,0.1)'
      }];
    }

    var releaseIcon = { 'Custody Released': '🌬️', 'Custody Retained': '🔒', 'Custody Re-armed': '⚔️' };

    var html = '<div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--sb-on-surface);">';

    releaseEntries.forEach(function(entry) {
      html += '<div style="background:var(--sb-surface-alt,#1e293b);padding:0.45rem 0.55rem;border-radius:0.3rem;border-left:2px solid ' + entry.color + ';display:flex;flex-direction:column;gap:0.35rem;">';

      // Header
      html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
      html += '<strong style="color:var(--sb-on-surface);font-size:0.73rem;">' + (releaseIcon[entry.state] || '●') + ' Upstream Release Gate</strong>';
      html += '<code style="color:' + entry.color + ';background:' + entry.bg + ';padding:0.1rem 0.4rem;text-transform:uppercase;font-size:0.63rem;">' + escapeHtml(entry.state) + '</code>';
      html += '</div>';

      // Context
      html += '<div style="display:flex;flex-direction:column;gap:0.1rem;">';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Settlement Lineage:</span> <span style="font-family:monospace;font-size:0.68rem;color:#38bdf8;">' + escapeHtml(entry.ownershipLineage) + '</span></div>';
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Local Basis:</span> <span style="font-family:monospace;font-size:0.68rem;color:#cbd5e1;">' + escapeHtml(entry.releaseBasis) + '</span></div>';
      html += '</div>';

      // Object description
      html += '<div style="background:#0f172a;border-radius:0.2rem;padding:0.3rem 0.4rem;font-size:0.65rem;color:#cbd5e1;line-height:1.4;">';
      html += '<code>' + escapeHtml(entry.releaseVerdict) + '</code>';
      html += '</div>';

      // ALCOA+ hash
      var alcoa = btoa(entry.state + entry.ownershipLineage + entry.releaseVerdict).substring(0, 16);
      html += '<div><span style="color:var(--sb-text-muted);font-weight:600;font-size:0.63rem;">Release Hash:</span> <code style="font-size:0.6rem;color:#64748b;">' + alcoa + '</code></div>';

      html += '</div>';
    });

    html += '<div style="margin-top:0.1rem;font-size:0.63rem;color:#64748b;">';
    html += '<strong style="color:var(--sb-text-muted);">Audit Constraints:</strong> ';
    html += 'Viewer Role: <code>' + escapeHtml(viewerRole) + '</code><br/>';
    html += 'Selected Worker: <code>' + escapeHtml(selectedWorker) + '</code><br/>';
    html += 'Selected Run: <code>' + escapeHtml(selectedRun) + '</code><br/>';
    html += 'Upstream Release Basis: <code>post-release next-path ownership -> upstream release -> custody-released, custody-retained, or custody-rearmed state</code><br/>';
    html += 'Upstream release states are <em>role-derived mocks</em> simulating explicit local memory buffer flushes. ';
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
