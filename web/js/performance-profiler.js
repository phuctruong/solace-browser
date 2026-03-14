// Diagram: 02-dashboard-login
(function () {
  'use strict';

  var API_SESSIONS = '/api/v1/profiler/sessions';
  var API_AGGREGATES = '/api/v1/profiler/aggregates';
  var TOKEN_KEY = 'solace_session_token';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function setStatus(msg, isError) {
    var el = document.getElementById('pp-status');
    if (el) {
      el.textContent = msg;
      el.style.color = isError ? 'var(--hub-error)' : 'var(--hub-text-muted)';
    }
  }

  function loadAggregates() {
    fetch(API_AGGREGATES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('pp-aggregates');
        if (!el) return;
        var aggs = data.aggregates || {};
        var keys = Object.keys(aggs);
        if (!keys.length) {
          el.innerHTML = '<div class="empty-state">No aggregate data yet.</div>';
          return;
        }
        el.innerHTML = keys.map(function (mt) {
          var a = aggs[mt];
          return '<div class="pp-agg-card">' +
            '<div class="pp-agg-type">' + escHtml(mt) + '</div>' +
            '<div class="pp-agg-stats">' +
            '<span>Count: ' + escHtml(String(a.count || 0)) + '</span>' +
            '<span>Avg: ' + escHtml(String(a.avg_value || 0)) + '</span>' +
            '<span>Max: ' + escHtml(String(a.max_value || 0)) + '</span>' +
            '<span>Min: ' + escHtml(String(a.min_value || 0)) + '</span>' +
            '</div></div>';
        }).join('');
      })
      .catch(function (err) { setStatus('Failed to load aggregates: ' + err, true); });
  }

  function deleteSession(sessionId) {
    if (!confirm('Delete profiling session ' + sessionId + '?')) return;
    fetch(API_SESSIONS + '/' + encodeURIComponent(sessionId), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + getToken() },
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          setStatus('Error: ' + (res.data.error || 'unknown'), true);
          return;
        }
        setStatus('Session deleted.');
        loadSessions();
        loadAggregates();
      })
      .catch(function (err) { setStatus('Request failed: ' + err, true); });
  }

  function loadSessions() {
    fetch(API_SESSIONS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('pp-sessions');
        if (!el) return;
        var sessions = data.sessions || [];
        if (!sessions.length) {
          el.innerHTML = '<div class="empty-state">No profiling sessions yet.</div>';
          return;
        }
        el.innerHTML = sessions.map(function (s) {
          return '<div class="pp-session-card" data-id="' + escHtml(s.session_id || '') + '">' +
            '<div class="pp-session-id">' + escHtml(s.session_id || '') + '</div>' +
            '<div class="pp-session-meta">' +
            '<span>Page: <code>' + escHtml((s.page_hash || '').substring(0, 16)) + '…</code></span>' +
            '<span>Metrics: ' + escHtml(String(s.metric_count || 0)) + '</span>' +
            '<span>Duration: ' + escHtml(String(s.total_duration_ms || 0)) + 'ms</span>' +
            '<span>' + escHtml(s.started_at || '') + '</span>' +
            '</div>' +
            '<div class="pp-session-actions">' +
            '<button class="btn-delete btn-pp-delete" data-id="' + escHtml(s.session_id || '') + '">Delete</button>' +
            '</div></div>';
        }).join('');
        el.querySelectorAll('.btn-pp-delete').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteSession(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Failed to load sessions: ' + err, true); });
  }

  function createSession() {
    var pageHash = (document.getElementById('pp-page-hash') || {}).value || '';
    if (!pageHash || pageHash.length !== 64) {
      setStatus('page_hash must be 64 hex characters', true);
      return;
    }
    fetch(API_SESSIONS, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + getToken(),
      },
      body: JSON.stringify({ page_hash: pageHash }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          setStatus('Error: ' + (res.data.error || 'unknown'), true);
          return;
        }
        setStatus('Session created: ' + ((res.data.session || {}).session_id || ''));
        document.getElementById('pp-page-hash').value = '';
        loadSessions();
      })
      .catch(function (err) { setStatus('Request failed: ' + err, true); });
  }

  function init() {
    loadSessions();
    loadAggregates();

    var btnRefresh = document.getElementById('btn-pp-refresh');
    if (btnRefresh) btnRefresh.addEventListener('click', function () { loadSessions(); loadAggregates(); });

    var btnCreate = document.getElementById('btn-pp-create');
    if (btnCreate) btnCreate.addEventListener('click', createSession);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
