/* image-optimizer.js — Task 120 | IIFE + escHtml | no eval() | no CDN */
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
    var el = document.getElementById('io-status');
    if (!el) return;
    el.textContent = msg;
    el.className = 'io-status ' + (isErr ? 'err' : 'ok');
  }

  function loadFormats() {
    fetch('/api/v1/image-optimizer/formats')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var formats = data.formats || [];
        var row = document.getElementById('io-formats-row');
        if (row) {
          row.innerHTML = formats.map(function (f) {
            return '<span class="io-badge">' + escHtml(f) + '</span>';
          }).join('');
        }
        var sel = document.getElementById('io-format');
        if (sel) {
          sel.innerHTML = formats.map(function (f) {
            return '<option value="' + escHtml(f) + '">' + escHtml(f) + '</option>';
          }).join('');
        }
      });
  }

  function loadStats() {
    fetch('/api/v1/image-optimizer/stats', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('io-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="io-stat-card"><div class="io-stat-label">Total Reports</div><div class="io-stat-value">' + escHtml(String(data.total_reports || 0)) + '</div></div>' +
          '<div class="io-stat-card"><div class="io-stat-label">Total Savings</div><div class="io-stat-value">' + escHtml(String(data.total_savings_bytes || 0)) + 'B</div></div>' +
          '<div class="io-stat-card"><div class="io-stat-label">Avg Savings</div><div class="io-stat-value">' + escHtml(String(data.avg_savings_pct || '0.00')) + '%</div></div>';
      });
  }

  function loadReports() {
    fetch('/api/v1/image-optimizer/reports', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('io-reports-list');
        if (!el) return;
        var reports = data.reports || [];
        if (reports.length === 0) {
          el.innerHTML = '<p class="io-item-meta">No reports yet.</p>';
          return;
        }
        el.innerHTML = reports.map(function (r) {
          return '<div class="io-item">' +
            '<div>' +
              '<div>' + escHtml(r.report_id) + '</div>' +
              '<div class="io-item-meta">Format: ' + escHtml(r.format) + ' | Savings: ' + escHtml(r.savings_pct) + '% | ' + escHtml(r.reported_at) + '</div>' +
              '<div class="io-item-meta">Issues: ' + escHtml((r.issues || []).join(', ') || 'none') + '</div>' +
            '</div>' +
            '<button class="io-btn io-btn-danger" data-id="' + escHtml(r.report_id) + '">Delete</button>' +
          '</div>';
        }).join('');
      });
  }

  function init() {
    loadFormats();
    loadStats();
    loadReports();

    var form = document.getElementById('io-report-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var pageUrl = document.getElementById('io-page-url').value;
        var imageUrl = document.getElementById('io-image-url').value;
        var fmt = document.getElementById('io-format').value;
        var originalSize = parseInt(document.getElementById('io-original-size').value, 10);
        var optimizedSize = parseInt(document.getElementById('io-optimized-size').value, 10);
        fetch('/api/v1/image-optimizer/reports', {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
          body: JSON.stringify({
            page_url: pageUrl,
            image_url: imageUrl,
            format: fmt,
            issues: [],
            original_size_bytes: originalSize,
            optimized_size_bytes: optimizedSize,
          }),
        })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
            if (res.ok) { setStatus('Report recorded: ' + res.data.report.report_id, false); loadStats(); loadReports(); form.reset(); }
            else { setStatus('Error: ' + (res.data.error || 'unknown'), true); }
          });
      });
    }

    var list = document.getElementById('io-reports-list');
    if (list) {
      list.addEventListener('click', function (e) {
        var btn = e.target.closest('button[data-id]');
        if (!btn) return;
        var id = btn.getAttribute('data-id');
        fetch('/api/v1/image-optimizer/reports/' + encodeURIComponent(id), {
          method: 'DELETE',
          headers: authHeaders(),
        })
          .then(function (r) { return r.json(); })
          .then(function () { loadStats(); loadReports(); });
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
