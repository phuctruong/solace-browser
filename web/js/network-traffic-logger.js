// Diagram: 02-dashboard-login
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
  var METHODS = [];

  function initMethods() {
    fetch('/api/v1/network-log/methods')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        METHODS = data.methods || [];
        var sel = document.getElementById('ntl-method-filter');
        METHODS.forEach(function (m) {
          var opt = document.createElement('option');
          opt.value = m;
          opt.textContent = m;
          sel.appendChild(opt);
        });
      });
  }

  function loadSummary() {
    fetch('/api/v1/network-log/summary', {
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (data) {
        var cards = document.getElementById('ntl-summary');
        cards.innerHTML = '';
        if (!data.by_method) return;
        var total = document.createElement('div');
        total.className = 'ntl-card';
        total.innerHTML = '<div class="ntl-card-value">' + escHtml(String(data.total || 0)) + '</div>' +
          '<div class="ntl-card-label">Total</div>';
        cards.appendChild(total);
        Object.keys(data.by_method).forEach(function (m) {
          if (!data.by_method[m]) return;
          var c = document.createElement('div');
          c.className = 'ntl-card';
          c.innerHTML = '<div class="ntl-card-value">' + escHtml(String(data.by_method[m])) + '</div>' +
            '<div class="ntl-card-label">' + escHtml(m) + '</div>';
          cards.appendChild(c);
        });
      });
  }

  function loadRequests() {
    fetch('/api/v1/network-log/requests', {
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.ok ? r.json() : { requests: [] }; })
      .then(function (data) {
        var methodFilter = document.getElementById('ntl-method-filter').value;
        var statusFilter = document.getElementById('ntl-status-filter').value.trim();
        var requests = (data.requests || []).filter(function (req) {
          if (methodFilter && req.method !== methodFilter) return false;
          if (statusFilter && String(req.status_code) !== statusFilter) return false;
          return true;
        });
        var tbody = document.getElementById('ntl-tbody');
        tbody.innerHTML = '';
        requests.forEach(function (req) {
          var tr = document.createElement('tr');
          tr.innerHTML = '<td class="ntl-method">' + escHtml(req.method || '') + '</td>' +
            '<td class="ntl-hash">' + escHtml((req.url_hash || '').slice(0, 16)) + '…</td>' +
            '<td>' + escHtml(String(req.status_code || '')) + '</td>' +
            '<td>' + escHtml(String(req.duration_ms || 0)) + '</td>' +
            '<td>' + escHtml((req.recorded_at || '').slice(0, 19)) + '</td>';
          tbody.appendChild(tr);
        });
      });
  }

  function clearLog() {
    fetch('/api/v1/network-log/clear', {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        document.getElementById('ntl-status').textContent = 'Log cleared';
        loadRequests();
        loadSummary();
      });
  }

  document.getElementById('ntl-refresh').addEventListener('click', function () {
    loadRequests();
    loadSummary();
  });
  document.getElementById('ntl-clear').addEventListener('click', clearLog);
  document.getElementById('ntl-method-filter').addEventListener('change', loadRequests);
  document.getElementById('ntl-status-filter').addEventListener('input', loadRequests);

  initMethods();
  loadRequests();
  loadSummary();
})();
