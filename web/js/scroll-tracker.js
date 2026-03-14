// Diagram: 02-dashboard-login
/* scroll-tracker.js — Scroll Tracker | Task 105 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_EVENTS     = '/api/v1/scroll-tracker/events';
  var API_STATS      = '/api/v1/scroll-tracker/stats';
  var API_DIRECTIONS = '/api/v1/scroll-tracker/directions';

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
        var el = document.getElementById('st-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="st-stat-card"><div class="st-stat-label">Total Events</div><div class="st-stat-value">' + escHtml(String(data.total_events)) + '</div></div>' +
          '<div class="st-stat-card"><div class="st-stat-label">Avg Depth %</div><div class="st-stat-value">' + escHtml(String(data.avg_depth_pct)) + '</div></div>';
      });
  }

  function loadEvents() {
    fetch(API_EVENTS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('st-events-list');
        if (!el) return;
        if (!data.events || data.events.length === 0) {
          el.innerHTML = '<p class="st-empty">No scroll events recorded.</p>';
          return;
        }
        var html = '';
        var shown = data.events.slice(-50);
        shown.forEach(function (ev) {
          html += '<div class="st-row">';
          html += '<span class="st-dir-badge">' + escHtml(ev.direction) + '</span>';
          html += '<span>' + escHtml(String(ev.depth_pct)) + '%</span>';
          html += '<div class="st-depth-bar" style="width:' + escHtml(String(ev.depth_pct)) + 'px"></div>';
          html += '<span style="color:var(--hub-text-muted);font-size:0.8rem;margin-left:auto">' + escHtml(ev.recorded_at) + '</span>';
          html += '</div>';
        });
        el.innerHTML = html;
      });
  }

  function loadDirections() {
    fetch(API_DIRECTIONS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('st-directions');
        if (!el) return;
        var html = '';
        (data.directions || []).forEach(function (d) {
          html += '<span class="st-badge">' + escHtml(d) + '</span>';
        });
        el.innerHTML = html;
      });
  }

  function init() {
    loadStats();
    loadEvents();
    loadDirections();

    var clearBtn = document.getElementById('st-clear-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        fetch(API_EVENTS, { method: 'DELETE' })
          .then(function () { loadEvents(); loadStats(); });
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
}());
