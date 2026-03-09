(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var authToken = '';
  var TIMER_TYPES = ['focus', 'break', 'unrestricted'];
  var tickInterval = null;

  function initTypes() {
    var sel = document.getElementById('st-type');
    TIMER_TYPES.forEach(function (t) {
      var opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t.charAt(0).toUpperCase() + t.slice(1);
      sel.appendChild(opt);
    });
  }

  function setStatus(msg, ok) {
    var el = document.getElementById('st-status');
    el.textContent = msg;
    el.style.color = ok === false ? 'var(--hub-danger)' : 'var(--hub-success)';
  }

  function loadCurrent() {
    fetch('/api/v1/session-timer/current', {
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.ok ? r.json() : { active: false }; })
      .then(function (data) {
        var display = document.getElementById('st-active-display');
        var startBtn = document.getElementById('st-start');
        var stopBtn = document.getElementById('st-stop');
        if (data.active && data.session) {
          display.classList.add('running');
          var s = data.session;
          display.textContent = s.session_type.toUpperCase() + ' — ' +
            (s.elapsed_minutes || 0) + ' / ' + (s.goal_minutes || '?') + ' min';
          startBtn.disabled = true;
          stopBtn.disabled = false;
          if (!tickInterval) {
            tickInterval = setInterval(loadCurrent, 30000);
          }
        } else {
          display.classList.remove('running');
          display.textContent = 'No active session';
          startBtn.disabled = false;
          stopBtn.disabled = true;
          if (tickInterval) { clearInterval(tickInterval); tickInterval = null; }
        }
      });
  }

  function startSession() {
    var sessionType = document.getElementById('st-type').value;
    var goalMinutes = parseInt(document.getElementById('st-goal').value, 10) || 25;
    fetch('/api/v1/session-timer/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken },
      body: JSON.stringify({ session_type: sessionType, goal_minutes: goalMinutes }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (res.ok) {
          setStatus('Session started', true);
          loadCurrent();
          loadStats();
        } else {
          setStatus(res.d.error || 'Error', false);
        }
      });
  }

  function stopSession() {
    fetch('/api/v1/session-timer/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken },
      body: JSON.stringify({}),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (res.ok) {
          setStatus('Session stopped — ' + (res.d.session && res.d.session.duration_minutes) + ' min', true);
          loadCurrent();
          loadHistory();
          loadStats();
        } else {
          setStatus(res.d.error || 'Error', false);
        }
      });
  }

  function loadHistory() {
    fetch('/api/v1/session-timer/history', {
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.ok ? r.json() : { history: [] }; })
      .then(function (data) {
        var tbody = document.getElementById('st-tbody');
        tbody.innerHTML = '';
        (data.history || []).slice(-20).reverse().forEach(function (s) {
          var tr = document.createElement('tr');
          tr.innerHTML = '<td>' + escHtml(s.session_type || '') + '</td>' +
            '<td>' + escHtml(String(s.duration_minutes || 0)) + '</td>' +
            '<td>' + escHtml(String(s.goal_minutes || '')) + '</td>' +
            '<td class="st-hash">' + escHtml((s.domain_hash || '').slice(0, 12)) + (s.domain_hash ? '…' : '') + '</td>' +
            '<td>' + escHtml((s.started_at || '').slice(0, 16)) + '</td>';
          tbody.appendChild(tr);
        });
      });
  }

  function loadStats() {
    fetch('/api/v1/session-timer/stats', {
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (data) {
        var row = document.getElementById('st-stats-row');
        row.innerHTML = '';
        var fields = [
          { label: 'Today (min)', value: data.today_minutes || 0 },
          { label: 'This Week (min)', value: data.this_week_minutes || 0 },
          { label: 'Total Sessions', value: data.session_count || 0 },
        ];
        fields.forEach(function (f) {
          var c = document.createElement('div');
          c.className = 'st-stat-card';
          c.innerHTML = '<div class="st-stat-value">' + escHtml(String(f.value)) + '</div>' +
            '<div class="st-stat-label">' + escHtml(f.label) + '</div>';
          row.appendChild(c);
        });
      });
  }

  document.getElementById('st-start').addEventListener('click', startSession);
  document.getElementById('st-stop').addEventListener('click', stopSession);

  initTypes();
  loadCurrent();
  loadHistory();
  loadStats();
})();
