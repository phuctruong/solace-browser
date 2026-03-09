/* geo-location-tracker.js — Geo Location Tracker | Task 103 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_PERMS     = '/api/v1/geo-tracker/permissions';
  var API_STATS     = '/api/v1/geo-tracker/stats';
  var API_DECISIONS = '/api/v1/geo-tracker/decisions';

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
        var el = document.getElementById('glt-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="glt-stat-card"><div class="glt-stat-label">Total Events</div><div class="glt-stat-value">' + escHtml(String(data.total_events)) + '</div></div>' +
          '<div class="glt-stat-card"><div class="glt-stat-label">Grant Rate %</div><div class="glt-stat-value">' + escHtml(String(data.grant_rate)) + '</div></div>';
      });
  }

  function loadList() {
    fetch(API_PERMS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('glt-list');
        if (!el) return;
        if (!data.permissions || data.permissions.length === 0) {
          el.innerHTML = '<p class="glt-empty">No permission records.</p>';
          return;
        }
        var html = '';
        data.permissions.forEach(function (p) {
          var decClass = 'glt-decision-' + escHtml(p.decision);
          html += '<div class="glt-row">';
          html += '<span class="glt-decision-badge ' + decClass + '">' + escHtml(p.decision) + '</span>';
          html += '<span>' + escHtml(p.accuracy_level) + '</span>';
          html += '<span style="color:var(--hub-text-muted);font-size:0.8rem;margin-left:auto">' + escHtml(p.recorded_at) + '</span>';
          html += '</div>';
        });
        el.innerHTML = html;
      });
  }

  function loadDecisions() {
    fetch(API_DECISIONS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('glt-decisions');
        if (!el) return;
        var html = '';
        (data.decisions || []).forEach(function (d) {
          html += '<span class="glt-badge">' + escHtml(d) + '</span>';
        });
        el.innerHTML = html;
      });
  }

  function init() {
    loadStats();
    loadList();
    loadDecisions();
  }

  document.addEventListener('DOMContentLoaded', init);
}());
