(function () {
  'use strict';

  var API_EVENTS = '/api/v1/push-tracker/events';
  var API_STATS = '/api/v1/push-tracker/stats';
  var API_TYPES = '/api/v1/push-tracker/event-types';

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message) {
    var el = document.getElementById('pnt-status');
    if (el) el.textContent = message;
  }

  function loadTypes() {
    fetch(API_TYPES)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var select = document.getElementById('pnt-event-type');
        if (!select) return;
        select.innerHTML = (data.event_types || []).map(function (item) {
          return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
        }).join('');
      })
      .catch(function (error) { setStatus('Event type load failed: ' + error.message); });
  }

  function loadStats() {
    fetch(API_STATS)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var el = document.getElementById('pnt-stats');
        if (!el) return;
        el.innerHTML = [
          ['Total Events', data.total_events || 0],
          ['Subscriptions', data.subscription_count || 0],
          ['Grant Rate', data.permission_grant_rate || '0.00']
        ].map(function (entry) {
          return '<div class="pnt-stat"><span>' + escHtml(entry[0]) + '</span><strong>' + escHtml(entry[1]) + '</strong></div>';
        }).join('');
      })
      .catch(function (error) { setStatus('Stats load failed: ' + error.message); });
  }

  function loadEvents() {
    fetch(API_EVENTS)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var el = document.getElementById('pnt-events');
        var events = data.events || [];
        if (!el) return;
        if (!events.length) {
          el.innerHTML = '<div class="pnt-row"><div class="pnt-meta">No events recorded.</div></div>';
          return;
        }
        el.innerHTML = events.map(function (event) {
          return '<article class="pnt-row">' +
            '<div class="pnt-row-head"><div><div class="pnt-tag">' + escHtml(event.event_type) + '</div><div class="pnt-meta">' + escHtml(event.event_id) + '</div></div>' +
            '<button class="pnt-delete" data-id="' + escHtml(event.event_id) + '">Delete</button></div>' +
            '<div class="pnt-meta">origin ' + escHtml(String(event.origin_hash || '').slice(0, 16)) + '…</div>' +
            '<div class="pnt-meta">endpoint ' + escHtml(String(event.endpoint_hash || 'none').slice(0, 16)) + '…</div>' +
          '</article>';
        }).join('');
        el.querySelectorAll('[data-id]').forEach(function (button) {
          button.addEventListener('click', function () {
            deleteEvent(button.getAttribute('data-id'));
          });
        });
      })
      .catch(function (error) { setStatus('Event load failed: ' + error.message); });
  }

  function deleteEvent(eventId) {
    fetch(API_EVENTS + '/' + encodeURIComponent(eventId), { method: 'DELETE' })
      .then(function (response) { return response.json(); })
      .then(function () {
        setStatus('Deleted ' + eventId);
        loadEvents();
        loadStats();
      })
      .catch(function (error) { setStatus('Delete failed: ' + error.message); });
  }

  function bindForm() {
    var form = document.getElementById('pnt-form');
    if (!form) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      fetch(API_EVENTS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: document.getElementById('pnt-event-type').value,
          origin: document.getElementById('pnt-origin').value.trim(),
          endpoint: document.getElementById('pnt-endpoint').value.trim() || null,
          is_https: document.getElementById('pnt-https').checked
        })
      })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (data.event_id) {
            form.reset();
            setStatus('Recorded ' + data.event_id);
            loadEvents();
            loadStats();
            return;
          }
          setStatus(data.error || 'Unable to record event');
        })
        .catch(function (error) { setStatus('Save failed: ' + error.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadTypes();
    loadStats();
    loadEvents();
    bindForm();
  });
})();
