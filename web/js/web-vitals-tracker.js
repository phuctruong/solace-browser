// Diagram: 02-dashboard-login
(function () {
  'use strict';

  var results = document.getElementById('wvm-results');
  var status = document.getElementById('wvm-status');
  var metricSelect = document.getElementById('wvm-metric-type');

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message, ok) {
    status.className = ok ? 'wvm-status wvm-success' : 'wvm-status';
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
    results.innerHTML = '<pre class="wvm-code">' + escHtml(JSON.stringify(data, null, 2)) + '</pre>';
  }

  function renderMeasurements(items) {
    if (!items.length) {
      renderCode({ measurements: [] });
      return;
    }
    results.innerHTML = items.map(function (item) {
      return '<article class="wvm-item">'
        + '<strong>' + escHtml(item.measurement_id) + '</strong>'
        + '<div class="wvm-meta"><span>' + escHtml(item.metric_type) + '</span><span>' + escHtml(item.value_ms) + '</span><span>' + escHtml(item.rating) + '</span><span>' + escHtml(item.navigation_type) + '</span></div>'
        + '<div class="wvm-meta"><span>URL hash ' + escHtml(item.url_hash) + '</span><span>' + escHtml(item.recorded_at) + '</span></div>'
        + '<button class="wvm-danger" type="button" data-delete-id="' + escHtml(item.measurement_id) + '">Delete</button>'
        + '</article>';
    }).join('');
  }

  function loadMetadata() {
    api('GET', '/api/v1/web-vitals/metric-types').then(function (response) {
      var items = response.data.metric_types || [];
      metricSelect.innerHTML = items.map(function (item) {
        return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
      }).join('');
      renderCode(response.data);
      setStatus('Loaded metric metadata.', response.ok);
    });
  }

  function loadMeasurements() {
    api('GET', '/api/v1/web-vitals/measurements').then(function (response) {
      renderMeasurements(response.data.measurements || []);
      setStatus('Loaded measurements.', response.ok);
    });
  }

  function loadStats() {
    api('GET', '/api/v1/web-vitals/stats').then(function (response) {
      renderCode(response.data);
      setStatus('Loaded stats.', response.ok);
    });
  }

  document.getElementById('wvm-form').addEventListener('submit', function (event) {
    event.preventDefault();
    api('POST', '/api/v1/web-vitals/measurements', {
      metric_type: metricSelect.value,
      url: document.getElementById('wvm-url').value,
      value_ms: document.getElementById('wvm-value-ms').value,
      rating: document.getElementById('wvm-rating').value,
      navigation_type: document.getElementById('wvm-navigation-type').value
    }).then(function (response) {
      renderCode(response.data);
      setStatus(response.ok ? 'Measurement recorded.' : (response.data.error || 'Request failed.'), response.ok);
      if (response.ok) {
        loadMeasurements();
      }
    });
  });

  results.addEventListener('click', function (event) {
    var target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    var measurementId = target.getAttribute('data-delete-id');
    if (!measurementId) {
      return;
    }
    api('DELETE', '/api/v1/web-vitals/measurements/' + encodeURIComponent(measurementId)).then(function (response) {
      setStatus(response.ok ? 'Measurement deleted.' : (response.data.error || 'Delete failed.'), response.ok);
      if (response.ok) {
        loadMeasurements();
      }
    });
  });

  document.getElementById('wvm-load-measurements').addEventListener('click', loadMeasurements);
  document.getElementById('wvm-load-stats').addEventListener('click', loadStats);
  document.getElementById('wvm-load-metadata').addEventListener('click', loadMetadata);

  loadMetadata();
  loadMeasurements();
})();
