/* Request Interceptor — Task 161. IIFE. No eval(). escHtml required. */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function msg(text) {
    var el = document.getElementById('ric-msg');
    if (el) el.textContent = text;
  }

  function statusBadgeClass(sc) {
    if (sc >= 200 && sc < 300) return 'ric-badge-2xx';
    if (sc >= 400 && sc < 500) return 'ric-badge-4xx';
    if (sc >= 500) return 'ric-badge-5xx';
    return '';
  }

  function loadStats() {
    fetch('/api/v1/request-interceptor/stats', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('ric-stats');
        if (!el) return;
        var sc = d.by_status_class || {};
        el.innerHTML = '<div class="ric-stats-grid">' +
          '<div class="ric-stat"><div class="ric-stat-val">' + escHtml(d.total_logs) + '</div><div class="ric-stat-lbl">Total Logs</div></div>' +
          '<div class="ric-stat"><div class="ric-stat-val">' + escHtml(d.avg_response_ms) + 'ms</div><div class="ric-stat-lbl">Avg Response</div></div>' +
          '<div class="ric-stat"><div class="ric-stat-val">' + escHtml(sc['2xx'] || 0) + '</div><div class="ric-stat-lbl">2xx Success</div></div>' +
          '<div class="ric-stat"><div class="ric-stat-val">' + escHtml((sc['4xx'] || 0) + (sc['5xx'] || 0)) + '</div><div class="ric-stat-lbl">Errors</div></div>' +
          '</div>';
      })
      .catch(function (e) { msg('Stats error: ' + e.message); });
  }

  function loadLogs() {
    fetch('/api/v1/request-interceptor/logs', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var panel = document.getElementById('ric-panel');
        if (!panel) return;
        if (!d.logs || d.logs.length === 0) { panel.innerHTML = '<p>No logs recorded.</p>'; return; }
        panel.innerHTML = d.logs.map(function (l) {
          var badgeClass = statusBadgeClass(l.status_code);
          return '<div class="ric-item">' +
            '<div><div class="ric-item-meta">' +
            '<span class="ric-badge">' + escHtml(l.method) + '</span> ' +
            '<span class="ric-badge ' + badgeClass + '">' + escHtml(l.status_code) + '</span> ' +
            escHtml(l.response_ms) + 'ms</div>' +
            '<div class="ric-item-id">' + escHtml(l.log_id) + '</div></div>' +
            '<div class="ric-actions"><button class="ric-btn ric-btn-del" data-id="' + escHtml(l.log_id) + '">Delete</button></div>' +
            '</div>';
        }).join('');
        panel.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteLog(btn.dataset.id); });
        });
      })
      .catch(function (e) { msg('Load error: ' + e.message); });
  }

  function deleteLog(id) {
    fetch('/api/v1/request-interceptor/logs/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadLogs(); loadStats(); })
      .catch(function (e) { msg('Delete error: ' + e.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadStats();
    loadLogs();

    var form = document.getElementById('ric-form');
    if (form) {
      form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        var payload = {
          url: document.getElementById('ric-url').value,
          origin: document.getElementById('ric-origin').value,
          method: document.getElementById('ric-method').value,
          status_code: parseInt(document.getElementById('ric-status').value, 10),
          response_ms: parseInt(document.getElementById('ric-response-ms').value, 10),
          request_size_bytes: parseInt(document.getElementById('ric-req-size').value, 10),
          response_size_bytes: parseInt(document.getElementById('ric-res-size').value, 10),
        };
        fetch('/api/v1/request-interceptor/logs', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + (window._solaceToken || '')
          },
          body: JSON.stringify(payload)
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.log) { msg('Logged: ' + d.log.log_id); loadLogs(); loadStats(); }
            else { msg('Error: ' + (d.error || 'unknown')); }
          })
          .catch(function (e) { msg('Submit error: ' + e.message); });
      });
    }
  });
}());
