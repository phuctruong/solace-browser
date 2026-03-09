(function () {
  'use strict';

  var API_REGISTRATIONS = '/api/v1/sw-tracker/registrations';
  var API_STATS = '/api/v1/sw-tracker/stats';
  var API_EVENTS = '/api/v1/sw-tracker/sw-events';

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message) {
    var el = document.getElementById('swr-status');
    if (el) el.textContent = message;
  }

  function loadEvents() {
    fetch(API_EVENTS)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var eventSelect = document.getElementById('swr-event-type');
        var stateSelect = document.getElementById('swr-state');
        if (eventSelect) {
          eventSelect.innerHTML = (data.sw_events || []).map(function (item) {
            return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
          }).join('');
        }
        if (stateSelect) {
          stateSelect.innerHTML = (data.states || []).map(function (item) {
            return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
          }).join('');
        }
      })
      .catch(function (error) { setStatus('Event load failed: ' + error.message); });
  }

  function loadStats() {
    fetch(API_STATS)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var el = document.getElementById('swr-stats');
        if (!el) return;
        el.innerHTML = [
          ['Total Registrations', data.total_registrations || 0],
          ['HTTPS Count', data.https_count || 0],
          ['Activated', (data.by_state || {}).activated || 0]
        ].map(function (entry) {
          return '<div class="swr-stat"><span>' + escHtml(entry[0]) + '</span><strong>' + escHtml(entry[1]) + '</strong></div>';
        }).join('');
      })
      .catch(function (error) { setStatus('Stats load failed: ' + error.message); });
  }

  function loadRegistrations() {
    fetch(API_REGISTRATIONS)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var el = document.getElementById('swr-registrations');
        var registrations = data.registrations || [];
        if (!el) return;
        if (!registrations.length) {
          el.innerHTML = '<div class="swr-row"><div class="swr-meta">No registrations recorded.</div></div>';
          return;
        }
        el.innerHTML = registrations.map(function (registration) {
          return '<article class="swr-row">' +
            '<div class="swr-row-head"><div><div class="swr-tag">' + escHtml(registration.event_type) + ' / ' + escHtml(registration.state) + '</div><div class="swr-meta">' + escHtml(registration.reg_id) + '</div></div>' +
            '<button class="swr-delete" data-id="' + escHtml(registration.reg_id) + '">Delete</button></div>' +
            '<div class="swr-meta">scope ' + escHtml(String(registration.scope_hash || '').slice(0, 16)) + '…</div>' +
            '<div class="swr-meta">script ' + escHtml(String(registration.script_hash || '').slice(0, 16)) + '…</div>' +
          '</article>';
        }).join('');
        el.querySelectorAll('[data-id]').forEach(function (button) {
          button.addEventListener('click', function () {
            deleteRegistration(button.getAttribute('data-id'));
          });
        });
      })
      .catch(function (error) { setStatus('Registration load failed: ' + error.message); });
  }

  function deleteRegistration(regId) {
    fetch(API_REGISTRATIONS + '/' + encodeURIComponent(regId), { method: 'DELETE' })
      .then(function (response) { return response.json(); })
      .then(function () {
        setStatus('Deleted ' + regId);
        loadRegistrations();
        loadStats();
      })
      .catch(function (error) { setStatus('Delete failed: ' + error.message); });
  }

  function bindForm() {
    var form = document.getElementById('swr-form');
    if (!form) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      fetch(API_REGISTRATIONS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: document.getElementById('swr-event-type').value,
          state: document.getElementById('swr-state').value,
          scope_url: document.getElementById('swr-scope-url').value.trim(),
          script_url: document.getElementById('swr-script-url').value.trim(),
          is_https: document.getElementById('swr-https').checked
        })
      })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (data.reg_id) {
            form.reset();
            setStatus('Recorded ' + data.reg_id);
            loadRegistrations();
            loadStats();
            return;
          }
          setStatus(data.error || 'Unable to record registration');
        })
        .catch(function (error) { setStatus('Save failed: ' + error.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadEvents();
    loadStats();
    loadRegistrations();
    bindForm();
  });
})();
