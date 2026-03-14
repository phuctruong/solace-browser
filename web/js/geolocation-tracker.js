// Diagram: 02-dashboard-login
/* Geolocation Tracker — Task 162. IIFE. No eval(). escHtml required. */
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
    var el = document.getElementById('geo-msg');
    if (el) el.textContent = text;
  }

  function badgeClass(evType) {
    if (evType === 'permission_granted' || evType === 'position_acquired') return 'geo-badge-granted';
    if (evType === 'permission_denied' || evType === 'permission_revoked') return 'geo-badge-denied';
    return '';
  }

  function loadStats() {
    fetch('/api/v1/geo-tracker/geo-stats', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('geo-stats');
        if (!el) return;
        el.innerHTML = '<div class="geo-stats-grid">' +
          '<div class="geo-stat"><div class="geo-stat-val">' + escHtml(d.total_events) + '</div><div class="geo-stat-lbl">Total Events</div></div>' +
          '<div class="geo-stat"><div class="geo-stat-val">' + escHtml(d.grant_rate) + '</div><div class="geo-stat-lbl">Grant Rate</div></div>' +
          '<div class="geo-stat"><div class="geo-stat-val">' + escHtml(d.https_count) + '</div><div class="geo-stat-lbl">HTTPS</div></div>' +
          '<div class="geo-stat"><div class="geo-stat-val">' + escHtml(d.by_event_type ? (d.by_event_type['permission_granted'] || 0) : 0) + '</div><div class="geo-stat-lbl">Granted</div></div>' +
          '</div>';
      })
      .catch(function (e) { msg('Stats error: ' + e.message); });
  }

  function loadEvents() {
    fetch('/api/v1/geo-tracker/events', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var panel = document.getElementById('geo-panel');
        if (!panel) return;
        if (!d.events || d.events.length === 0) { panel.innerHTML = '<p>No events recorded.</p>'; return; }
        panel.innerHTML = d.events.map(function (e) {
          var bClass = badgeClass(e.event_type);
          var httpsTag = e.is_https ? '<span class="geo-https">HTTPS</span> ' : '';
          var acc = e.accuracy_meters !== null && e.accuracy_meters !== undefined ? escHtml(e.accuracy_meters) + 'm' : 'N/A';
          return '<div class="geo-item">' +
            '<div><div class="geo-item-meta">' + httpsTag +
            '<span class="geo-badge ' + bClass + '">' + escHtml(e.event_type) + '</span> acc: ' + acc + '</div>' +
            '<div class="geo-item-id">' + escHtml(e.event_id) + '</div></div>' +
            '<div class="geo-actions"><button class="geo-btn geo-btn-del" data-id="' + escHtml(e.event_id) + '">Delete</button></div>' +
            '</div>';
        }).join('');
        panel.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteEvent(btn.dataset.id); });
        });
      })
      .catch(function (e) { msg('Load error: ' + e.message); });
  }

  function deleteEvent(id) {
    fetch('/api/v1/geo-tracker/events/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadEvents(); loadStats(); })
      .catch(function (e) { msg('Delete error: ' + e.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadStats();
    loadEvents();

    var form = document.getElementById('geo-form');
    if (form) {
      form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        var accVal = document.getElementById('geo-accuracy').value;
        var payload = {
          url: document.getElementById('geo-url').value,
          event_type: document.getElementById('geo-event-type').value,
          accuracy_meters: accVal ? parseInt(accVal, 10) : null,
          is_https: document.getElementById('geo-https').checked,
        };
        fetch('/api/v1/geo-tracker/events', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + (window._solaceToken || '')
          },
          body: JSON.stringify(payload)
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.event) { msg('Recorded: ' + d.event.event_id); loadEvents(); loadStats(); }
            else { msg('Error: ' + (d.error || 'unknown')); }
          })
          .catch(function (e) { msg('Submit error: ' + e.message); });
      });
    }
  });
}());
