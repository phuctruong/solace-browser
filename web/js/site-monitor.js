// Diagram: 02-dashboard-login
/* site-monitor.js — Task 119 | IIFE + escHtml | no eval() | no CDN */
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function authHeaders() {
    var token = window.__SOLACE_TOKEN__ || '';
    return token ? { 'Authorization': 'Bearer ' + token } : {};
  }

  function setStatus(msg, isErr) {
    var el = document.getElementById('sm-status');
    if (!el) return;
    el.textContent = msg;
    el.className = 'sm-status ' + (isErr ? 'err' : 'ok');
  }

  var _monitors = [];

  function loadStatuses() {
    fetch('/api/v1/site-monitor/statuses')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('sm-status');
        if (!sel) return;
        sel.innerHTML = (data.statuses || []).map(function (s) {
          return '<option value="' + escHtml(s) + '">' + escHtml(s) + '</option>';
        }).join('');
      });
  }

  function loadMonitors() {
    fetch('/api/v1/site-monitor/monitors', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _monitors = data.monitors || [];
        var sel = document.getElementById('sm-monitor-select');
        if (sel) {
          sel.innerHTML = _monitors.map(function (m) {
            return '<option value="' + escHtml(m.monitor_id) + '">' + escHtml(m.name || m.monitor_id) + '</option>';
          }).join('') || '<option value="">— no monitors —</option>';
        }
        var el = document.getElementById('sm-monitors-list');
        if (!el) return;
        if (_monitors.length === 0) {
          el.innerHTML = '<p class="sm-item-meta">No monitors yet.</p>';
          return;
        }
        el.innerHTML = _monitors.map(function (m) {
          return '<div class="sm-item">' +
            '<div>' +
              '<div>' + escHtml(m.name || m.monitor_id) + ' <span class="sm-item-meta">(' + escHtml(m.monitor_id) + ')</span></div>' +
              '<div class="sm-item-meta">Interval: ' + escHtml(String(m.check_interval_mins)) + ' mins | Checks: ' + escHtml(String(m.check_count)) + '</div>' +
            '</div>' +
            '<button class="sm-btn sm-btn-danger" data-id="' + escHtml(m.monitor_id) + '">Delete</button>' +
          '</div>';
        }).join('');
      });
  }

  function loadChecks() {
    fetch('/api/v1/site-monitor/checks', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('sm-checks-list');
        if (!el) return;
        var checks = data.checks || [];
        if (checks.length === 0) {
          el.innerHTML = '<p class="sm-item-meta">No checks yet.</p>';
          return;
        }
        el.innerHTML = checks.slice(-20).reverse().map(function (c) {
          var badgeCls = c.status === 'up' ? 'sm-badge-up' : (c.status === 'down' ? 'sm-badge-down' : '');
          return '<div class="sm-item">' +
            '<div>' +
              '<span class="sm-badge ' + escHtml(badgeCls) + '">' + escHtml(c.status) + '</span>' +
              ' <span class="sm-item-meta">' + escHtml(c.check_id) + '</span>' +
              '<div class="sm-item-meta">HTTP ' + escHtml(String(c.http_code)) + ' | ' + escHtml(String(c.response_ms)) + 'ms | ' + escHtml(c.checked_at) + '</div>' +
            '</div>' +
          '</div>';
        }).join('');
      });
  }

  function init() {
    loadStatuses();
    loadMonitors();
    loadChecks();

    var monitorForm = document.getElementById('sm-monitor-form');
    if (monitorForm) {
      monitorForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var url = document.getElementById('sm-url').value;
        var name = document.getElementById('sm-name').value;
        var interval = parseInt(document.getElementById('sm-interval').value, 10);
        fetch('/api/v1/site-monitor/monitors', {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
          body: JSON.stringify({ url: url, name: name, check_interval_mins: interval }),
        })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
            if (res.ok) { setStatus('Monitor added: ' + res.data.monitor.monitor_id, false); loadMonitors(); monitorForm.reset(); }
            else { setStatus('Error: ' + (res.data.error || 'unknown'), true); }
          });
      });
    }

    var checkForm = document.getElementById('sm-check-form');
    if (checkForm) {
      checkForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var monitorId = document.getElementById('sm-monitor-select').value;
        var status = document.getElementById('sm-status').value;
        var httpCode = parseInt(document.getElementById('sm-http-code').value, 10);
        var responseMs = parseInt(document.getElementById('sm-response-ms').value, 10);
        fetch('/api/v1/site-monitor/checks', {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
          body: JSON.stringify({ monitor_id: monitorId, status: status, http_code: httpCode, response_ms: responseMs }),
        })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
            if (res.ok) { setStatus('Check recorded: ' + res.data.check.check_id, false); loadMonitors(); loadChecks(); checkForm.reset(); }
            else { setStatus('Error: ' + (res.data.error || 'unknown'), true); }
          });
      });
    }

    var monitorsList = document.getElementById('sm-monitors-list');
    if (monitorsList) {
      monitorsList.addEventListener('click', function (e) {
        var btn = e.target.closest('button[data-id]');
        if (!btn) return;
        var id = btn.getAttribute('data-id');
        fetch('/api/v1/site-monitor/monitors/' + encodeURIComponent(id), {
          method: 'DELETE',
          headers: authHeaders(),
        })
          .then(function (r) { return r.json(); })
          .then(function () { loadMonitors(); loadChecks(); });
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
