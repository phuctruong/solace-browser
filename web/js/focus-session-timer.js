/* Focus Session Timer — Task 122 */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var panel = document.getElementById('fst-panel');
  var status = document.getElementById('fst-status');
  var form = document.getElementById('fst-form');
  var modeSelect = document.getElementById('fst-mode');
  var durationSelect = document.getElementById('fst-duration');
  var taskInput = document.getElementById('fst-task');

  var FOCUS_DURATIONS = [15, 20, 25, 30, 45, 60, 90, 120];

  function setStatus(msg) { status.textContent = msg; }

  function authHeaders() {
    return { 'Authorization': 'Bearer ' + (window.__solace_token || '') };
  }

  function loadModes() {
    fetch('/api/v1/focus-timer/modes')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        modeSelect.innerHTML = (data.modes || []).map(function (m) {
          return '<option value="' + escHtml(m) + '">' + escHtml(m.replace('_', ' ')) + '</option>';
        }).join('');
        FOCUS_DURATIONS.forEach(function (d) {
          var opt = document.createElement('option');
          opt.value = d;
          opt.textContent = d + ' min';
          durationSelect.appendChild(opt);
        });
      })
      .catch(function (e) { setStatus('Error loading modes: ' + escHtml(String(e))); });
  }

  function renderSessions(sessions) {
    if (!sessions.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No sessions recorded.</p>';
      return;
    }
    panel.innerHTML = sessions.map(function (s) {
      var badge = s.completed
        ? '<span class="fst-badge-done">Done</span>'
        : '<span class="fst-badge-active">Active</span>';
      var duration = s.actual_duration_mins !== null ? escHtml(s.actual_duration_mins) + ' min' : 'In progress';
      return '<div class="fst-item">'
        + '<div class="fst-item-id">' + escHtml(s.session_id) + ' ' + badge + '</div>'
        + '<div class="fst-item-meta">Mode: ' + escHtml(s.mode)
        + ' | Planned: ' + escHtml(s.planned_duration_mins) + ' min'
        + ' | Actual: ' + duration
        + ' | Started: ' + escHtml(s.started_at) + '</div>'
        + '</div>';
    }).join('');
  }

  function renderStats(data) {
    panel.innerHTML = '<div class="fst-stat-grid">'
      + '<div class="fst-stat-card"><div class="fst-stat-value">' + escHtml(data.total_sessions) + '</div><div class="fst-stat-label">Total Sessions</div></div>'
      + '<div class="fst-stat-card"><div class="fst-stat-value">' + escHtml(data.completed_count) + '</div><div class="fst-stat-label">Completed</div></div>'
      + '<div class="fst-stat-card"><div class="fst-stat-value">' + escHtml(data.total_focus_mins) + '</div><div class="fst-stat-label">Total Minutes</div></div>'
      + '<div class="fst-stat-card"><div class="fst-stat-value">' + escHtml(data.avg_duration_mins) + '</div><div class="fst-stat-label">Avg Duration (min)</div></div>'
      + '</div>';
  }

  function loadSessions() {
    fetch('/api/v1/focus-timer/sessions', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderSessions(data.sessions || []);
        setStatus('Sessions loaded: ' + (data.total || 0));
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadStats() {
    fetch('/api/v1/focus-timer/stats', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderStats(data);
        setStatus('Stats loaded.');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function showModes() {
    fetch('/api/v1/focus-timer/modes')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        panel.innerHTML = '<p class="fst-item-meta">Modes: ' + escHtml((data.modes || []).join(', ')) + '</p>';
        setStatus('Modes loaded.');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var mode = modeSelect.value;
    var dur = parseInt(durationSelect.value, 10);
    var task = taskInput.value.trim();
    fetch('/api/v1/focus-timer/sessions', {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
      body: JSON.stringify({ mode: mode, planned_duration_mins: dur, task_description: task })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.session) {
          taskInput.value = '';
          setStatus('Session started: ' + escHtml(data.session.session_id));
          loadSessions();
        } else {
          setStatus('Error: ' + escHtml(data.error || 'unknown'));
        }
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  document.getElementById('btn-fst-end').addEventListener('click', function () {
    fetch('/api/v1/focus-timer/sessions/end', {
      method: 'POST',
      headers: authHeaders()
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.session) {
          setStatus('Session ended: ' + escHtml(data.session.actual_duration_mins) + ' min actual.');
          loadSessions();
        } else {
          setStatus('Error: ' + escHtml(data.error || 'no active session'));
        }
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  document.getElementById('btn-fst-sessions').addEventListener('click', loadSessions);
  document.getElementById('btn-fst-stats').addEventListener('click', loadStats);
  document.getElementById('btn-fst-modes').addEventListener('click', showModes);

  loadModes();
  loadSessions();
})();
