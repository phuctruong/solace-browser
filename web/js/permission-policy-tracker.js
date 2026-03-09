(function () {
  'use strict';

  var results = document.getElementById('ppe-results');
  var status = document.getElementById('ppe-status');
  var policyTypeSelect = document.getElementById('ppe-policy-type');

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message, ok) {
    status.className = ok ? 'ppe-status ppe-success' : 'ppe-status';
    status.textContent = message;
  }

  function api(method, path, body) {
    var options = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (body) {
      options.body = JSON.stringify(body);
    }
    return fetch(path, options).then(function (response) {
      return response.json().then(function (data) {
        return { ok: response.ok, data: data };
      });
    });
  }

  function renderCode(data) {
    results.innerHTML = '<pre class="ppe-code">' + escHtml(JSON.stringify(data, null, 2)) + '</pre>';
  }

  function renderEvents(items) {
    if (!items.length) {
      renderCode({ events: [] });
      return;
    }
    results.innerHTML = items.map(function (item) {
      return '<article class="ppe-item">'
        + '<strong>' + escHtml(item.event_id) + '</strong>'
        + '<div class="ppe-meta"><span>' + escHtml(item.policy_type) + '</span><span>' + escHtml(item.action) + '</span><span>Violation ' + escHtml(item.is_violation) + '</span></div>'
        + '<div class="ppe-meta"><span>URL hash ' + escHtml(item.url_hash) + '</span><span>Origin hash ' + escHtml(item.origin_hash) + '</span></div>'
        + '<button class="ppe-danger" type="button" data-delete-id="' + escHtml(item.event_id) + '">Delete</button>'
        + '</article>';
    }).join('');
  }

  function loadTypes() {
    api('GET', '/api/v1/permission-policy/policy-types').then(function (response) {
      var items = response.data.policy_types || [];
      policyTypeSelect.innerHTML = items.map(function (item) {
        return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
      }).join('');
      renderCode(response.data);
      setStatus('Loaded policy types.', response.ok);
    });
  }

  function loadEvents() {
    api('GET', '/api/v1/permission-policy/events').then(function (response) {
      renderEvents(response.data.events || []);
      setStatus('Loaded events.', response.ok);
    });
  }

  function loadStats() {
    api('GET', '/api/v1/permission-policy/stats').then(function (response) {
      renderCode(response.data);
      setStatus('Loaded stats.', response.ok);
    });
  }

  document.getElementById('ppe-form').addEventListener('submit', function (event) {
    event.preventDefault();
    api('POST', '/api/v1/permission-policy/events', {
      policy_type: policyTypeSelect.value,
      action: document.getElementById('ppe-action').value,
      url: document.getElementById('ppe-url').value,
      origin: document.getElementById('ppe-origin').value,
      is_violation: document.getElementById('ppe-violation').checked
    }).then(function (response) {
      renderCode(response.data);
      setStatus(response.ok ? 'Event recorded.' : (response.data.error || 'Request failed.'), response.ok);
      if (response.ok) {
        loadEvents();
      }
    });
  });

  results.addEventListener('click', function (event) {
    var target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    var eventId = target.getAttribute('data-delete-id');
    if (!eventId) {
      return;
    }
    api('DELETE', '/api/v1/permission-policy/events/' + encodeURIComponent(eventId)).then(function (response) {
      setStatus(response.ok ? 'Event deleted.' : (response.data.error || 'Delete failed.'), response.ok);
      if (response.ok) {
        loadEvents();
      }
    });
  });

  document.getElementById('ppe-load-events').addEventListener('click', loadEvents);
  document.getElementById('ppe-load-stats').addEventListener('click', loadStats);
  document.getElementById('ppe-load-types').addEventListener('click', loadTypes);

  loadTypes();
  loadEvents();
})();
