// Diagram: 02-dashboard-login
/* Automation Recorder — Task 090 */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var panel = document.getElementById('ar-panel');
  var status = document.getElementById('ar-status');
  var isRecording = false;

  function setStatus(msg) { status.textContent = msg; }

  function renderAutomations(automations) {
    if (!automations.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No automations recorded yet.</p>';
      return;
    }
    panel.innerHTML = automations.map(function (a) {
      return '<div class="ar-item">'
        + '<div class="ar-item-id">' + escHtml(a.automation_id) + '</div>'
        + '<div class="ar-item-name">' + escHtml(a.name) + '</div>'
        + '<div class="ar-item-meta">Actions: ' + escHtml(a.action_count)
        + ' | Duration: ' + escHtml(a.duration_seconds) + 's'
        + ' | Recorded: ' + escHtml(a.stopped_at || '') + '</div>'
        + '</div>';
    }).join('');
  }

  function renderActionTypes(types) {
    panel.innerHTML = '<p class="ar-item-meta">Action types: ' + escHtml(types.join(', ')) + '</p>';
  }

  function loadAutomations() {
    fetch('/api/v1/automation-recorder/automations')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderAutomations(data.automations || []);
        setStatus('Automations: ' + (data.total || 0));
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadActionTypes() {
    fetch('/api/v1/automation-recorder/action-types')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderActionTypes(data.action_types || []);
        setStatus('Action types loaded');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  document.getElementById('btn-ar-start').addEventListener('click', function () {
    fetch('/api/v1/automation-recorder/start', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.automation_id) {
          isRecording = true;
          setStatus('Recording: ' + escHtml(data.automation_id));
        } else {
          setStatus('Error: ' + escHtml(data.error || 'unknown'));
        }
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  document.getElementById('btn-ar-stop').addEventListener('click', function () {
    fetch('/api/v1/automation-recorder/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        isRecording = false;
        setStatus('Stopped: ' + escHtml(data.automation_id || '') + ' (' + escHtml(data.action_count || 0) + ' actions)');
        loadAutomations();
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  document.getElementById('btn-ar-list').addEventListener('click', loadAutomations);
  document.getElementById('btn-ar-types').addEventListener('click', loadActionTypes);

  loadAutomations();
})();
