/* privacy-dashboard.js — Privacy Dashboard | Task 077 | IIFE pattern | no dangerous eval */
(function () {
  'use strict';

  var API_BASE = '/api/v1/privacy';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleString();
    } catch (_) {
      return escHtml(iso);
    }
  }

  function showMsg(msg) {
    var el = document.getElementById('pd-report-msg');
    el.textContent = msg;
    el.hidden = false;
  }

  function loadSummary() {
    fetch(API_BASE + '/summary')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        document.getElementById('pd-score').textContent = data.privacy_score !== undefined ? data.privacy_score : '—';
        document.getElementById('pd-count').textContent = data.event_count !== undefined ? data.event_count : '—';
        var by = data.by_type || {};
        document.getElementById('pd-trackers').textContent = by.tracker_blocked !== undefined ? by.tracker_blocked : '—';
        document.getElementById('pd-cookies').textContent = by.cookie_cleared !== undefined ? by.cookie_cleared : '—';
      })
      .catch(function (err) { console.error('summary error', err); });
  }

  function loadEvents() {
    fetch(API_BASE + '/events')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('pd-events');
        var events = data.events || [];
        if (events.length === 0) {
          container.innerHTML = '<p class="pd-loading">No events recorded.</p>';
          return;
        }
        var html = '';
        events.slice().reverse().forEach(function (e) {
          html += '<div class="pd-event-row">';
          html += '<span class="pd-event-type">' + escHtml(e.event_type) + '</span>';
          html += ' <span class="pd-event-meta">domain: ' + escHtml(e.domain_hash ? e.domain_hash.slice(0, 12) + '…' : 'n/a') + '</span>';
          html += ' <span class="pd-event-meta">' + formatDate(e.occurred_at) + '</span>';
          html += '</div>';
        });
        container.innerHTML = html;
      })
      .catch(function (err) { console.error('events error', err); });
  }

  function reportEvent() {
    var eventType = document.getElementById('pd-event-type').value;
    var domain = document.getElementById('pd-domain').value.trim();
    var details = document.getElementById('pd-details').value.trim();
    fetch(API_BASE + '/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_type: eventType, domain: domain, details: details }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showMsg('Recorded: ' + (data.event_id || ''));
        loadSummary();
        loadEvents();
      })
      .catch(function (err) { console.error('report error', err); });
  }

  function clearEvents() {
    fetch(API_BASE + '/events', { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () { loadSummary(); loadEvents(); })
      .catch(function (err) { console.error('clear error', err); });
  }

  document.getElementById('pd-report-btn').addEventListener('click', reportEvent);
  document.getElementById('pd-clear-btn').addEventListener('click', clearEvents);

  loadSummary();
  loadEvents();
}());
