// Diagram: 02-dashboard-login
/* Font Inspector — Task 158. IIFE. No eval(). escHtml required. */
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
    var el = document.getElementById('fns-msg');
    if (el) el.textContent = text;
  }

  function loadStats() {
    fetch('/api/v1/font-inspector/stats', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('fns-stats');
        if (!el) return;
        el.innerHTML = '<div class="fns-stats-grid">' +
          '<div class="fns-stat"><div class="fns-stat-val">' + escHtml(d.total_scans) + '</div><div class="fns-stat-lbl">Total Scans</div></div>' +
          '<div class="fns-stat"><div class="fns-stat-val">' + escHtml(d.avg_font_count) + '</div><div class="fns-stat-lbl">Avg Fonts</div></div>' +
          '<div class="fns-stat"><div class="fns-stat-val">' + escHtml(d.avg_load_time_ms) + 'ms</div><div class="fns-stat-lbl">Avg Load</div></div>' +
          '<div class="fns-stat"><div class="fns-stat-val">' + escHtml(d.variable_font_count) + '</div><div class="fns-stat-lbl">Variable Fonts</div></div>' +
          '</div>';
      })
      .catch(function (e) { msg('Stats error: ' + e.message); });
  }

  function loadScans() {
    fetch('/api/v1/font-inspector/scans', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var panel = document.getElementById('fns-panel');
        if (!panel) return;
        if (!d.scans || d.scans.length === 0) { panel.innerHTML = '<p>No scans recorded.</p>'; return; }
        panel.innerHTML = d.scans.map(function (s) {
          return '<div class="fns-item">' +
            '<div><div class="fns-item-meta"><span class="fns-badge">' + escHtml(s.category) + '</span> ' +
            escHtml(s.font_count) + ' fonts | ' + escHtml(s.load_time_ms) + 'ms</div>' +
            '<div class="fns-item-id">' + escHtml(s.scan_id) + '</div></div>' +
            '<div class="fns-actions"><button class="fns-btn fns-btn-del" data-id="' + escHtml(s.scan_id) + '">Delete</button></div>' +
            '</div>';
        }).join('');
        panel.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteScan(btn.dataset.id); });
        });
      })
      .catch(function (e) { msg('Load error: ' + e.message); });
  }

  function deleteScan(id) {
    fetch('/api/v1/font-inspector/scans/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadScans(); loadStats(); })
      .catch(function (e) { msg('Delete error: ' + e.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadStats();
    loadScans();

    var form = document.getElementById('fns-form');
    if (form) {
      form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        var payload = {
          url: document.getElementById('fns-url').value,
          font_name: document.getElementById('fns-font-name').value,
          category: document.getElementById('fns-category').value,
          font_count: parseInt(document.getElementById('fns-font-count').value, 10),
          load_time_ms: parseInt(document.getElementById('fns-load-time').value, 10),
          is_variable_font: document.getElementById('fns-variable').checked,
          has_web_font: document.getElementById('fns-webfont').checked,
        };
        fetch('/api/v1/font-inspector/scans', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + (window._solaceToken || '')
          },
          body: JSON.stringify(payload)
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.scan) { msg('Recorded: ' + d.scan.scan_id); loadScans(); loadStats(); }
            else { msg('Error: ' + (d.error || 'unknown')); }
          })
          .catch(function (e) { msg('Submit error: ' + e.message); });
      });
    }
  });
}());
