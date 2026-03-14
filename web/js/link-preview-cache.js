// Diagram: 02-dashboard-login
/* link-preview-cache.js — Link Preview Cache | Task 101 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_LIST  = '/api/v1/link-preview/list';
  var API_STATS = '/api/v1/link-preview/stats';
  var API_FLUSH = '/api/v1/link-preview/flush';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function loadStats() {
    fetch(API_STATS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('lpc-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="lpc-stat-card"><div class="lpc-stat-label">Entries</div><div class="lpc-stat-value">' + escHtml(String(data.total_entries)) + '</div></div>' +
          '<div class="lpc-stat-card"><div class="lpc-stat-label">Total Hits</div><div class="lpc-stat-value">' + escHtml(String(data.total_hits)) + '</div></div>' +
          '<div class="lpc-stat-card"><div class="lpc-stat-label">Avg Hits</div><div class="lpc-stat-value">' + escHtml(String(data.avg_hits)) + '</div></div>';
      });
  }

  function loadList() {
    fetch(API_LIST)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('lpc-list');
        if (!el) return;
        if (!data.previews || data.previews.length === 0) {
          el.innerHTML = '<p class="lpc-empty">No cached previews.</p>';
          return;
        }
        var html = '';
        data.previews.forEach(function (p) {
          html += '<div class="lpc-row">';
          html += '<div class="lpc-row-label">URL Hash</div><div class="lpc-row-value">' + escHtml(p.url_hash) + '</div>';
          html += '<div class="lpc-row-label">Hits</div><div class="lpc-row-value">' + escHtml(String(p.hit_count)) + '</div>';
          html += '</div>';
        });
        el.innerHTML = html;
      });
  }

  function init() {
    loadStats();
    loadList();

    var flushBtn = document.getElementById('lpc-flush-btn');
    if (flushBtn) {
      flushBtn.addEventListener('click', function () {
        fetch(API_FLUSH, { method: 'POST' })
          .then(function () { loadList(); loadStats(); });
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
}());
