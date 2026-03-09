/* media-player-tracker.js — Media Player Tracker | Task 100 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_EVENTS = '/api/v1/media-tracker/events';
  var API_STATS  = '/api/v1/media-tracker/stats';
  var API_TYPES  = '/api/v1/media-tracker/event-types';

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
        var el = document.getElementById('mpt-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="mpt-stat-card"><div class="mpt-stat-label">Total Events</div><div class="mpt-stat-value">' + escHtml(String(data.total_events)) + '</div></div>' +
          '<div class="mpt-stat-card"><div class="mpt-stat-label">Play Seconds</div><div class="mpt-stat-value">' + escHtml(String(data.total_play_seconds)) + '</div></div>';
      });
  }

  function loadEvents() {
    fetch(API_EVENTS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('mpt-events-list');
        if (!el) return;
        if (!data.events || data.events.length === 0) {
          el.innerHTML = '<p class="mpt-empty">No events recorded.</p>';
          return;
        }
        var html = '';
        data.events.forEach(function (ev) {
          html += '<div class="mpt-event-row">';
          html += '<span class="mpt-event-type">' + escHtml(ev.event_type) + '</span>';
          html += '<span>' + escHtml(ev.media_type) + '</span>';
          html += '<span class="mpt-text-muted">' + escHtml(ev.recorded_at) + '</span>';
          html += '</div>';
        });
        el.innerHTML = html;
      });
  }

  function loadEventTypes() {
    fetch(API_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('mpt-event-types');
        if (!el) return;
        var html = '';
        (data.event_types || []).forEach(function (t) {
          html += '<span class="mpt-badge">' + escHtml(t) + '</span>';
        });
        el.innerHTML = html;
      });
  }

  function init() {
    loadStats();
    loadEvents();
    loadEventTypes();

    var clearBtn = document.getElementById('mpt-clear-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        fetch(API_EVENTS, { method: 'DELETE' })
          .then(function () { loadEvents(); loadStats(); });
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
}());
