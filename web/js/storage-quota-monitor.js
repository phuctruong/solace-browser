// Diagram: 02-dashboard-login
(function () {
  'use strict';

  var results = document.getElementById('sqm-results');
  var status = document.getElementById('sqm-status');
  var form = document.getElementById('sqm-form');
  var typeSelect = document.getElementById('sqm-storage-type');

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message, ok) {
    status.className = ok ? 'sqm-status sqm-success' : 'sqm-status';
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

  function renderSnapshots(items) {
    if (!items.length) {
      results.innerHTML = '<div class="sqm-code">No snapshots recorded yet.</div>';
      return;
    }
    results.innerHTML = items.map(function (item) {
      return '<article class="sqm-item">'
        + '<strong>' + escHtml(item.snapshot_id) + '</strong>'
        + '<div class="sqm-meta">'
        + '<span>' + escHtml(item.storage_type) + '</span>'
        + '<span>Usage ' + escHtml(item.usage_pct) + '%</span>'
        + '<span>Used ' + escHtml(item.used_bytes) + ' bytes</span>'
        + '</div>'
        + '<div class="sqm-meta">'
        + '<span>URL hash ' + escHtml(item.url_hash) + '</span>'
        + '<span>' + escHtml(item.recorded_at) + '</span>'
        + '</div>'
        + '<button class="sqm-danger" data-delete-id="' + escHtml(item.snapshot_id) + '" type="button">Delete</button>'
        + '</article>';
    }).join('');
  }

  function renderCode(data) {
    results.innerHTML = '<pre class="sqm-code">' + escHtml(JSON.stringify(data, null, 2)) + '</pre>';
  }

  function loadTypes() {
    api('GET', '/api/v1/storage-quota/storage-types').then(function (response) {
      var types = response.data.storage_types || [];
      typeSelect.innerHTML = types.map(function (item) {
        return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
      }).join('');
      renderCode(response.data);
      setStatus('Loaded storage types.', response.ok);
    });
  }

  function loadSnapshots() {
    api('GET', '/api/v1/storage-quota/snapshots').then(function (response) {
      renderSnapshots(response.data.snapshots || []);
      setStatus('Loaded snapshots.', response.ok);
    });
  }

  function loadStats() {
    api('GET', '/api/v1/storage-quota/stats').then(function (response) {
      renderCode(response.data);
      setStatus('Loaded stats.', response.ok);
    });
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    api('POST', '/api/v1/storage-quota/snapshots', {
      storage_type: typeSelect.value,
      url: document.getElementById('sqm-url').value,
      used_bytes: Number(document.getElementById('sqm-used-bytes').value),
      quota_bytes: Number(document.getElementById('sqm-quota-bytes').value)
    }).then(function (response) {
      renderCode(response.data);
      setStatus(response.ok ? 'Snapshot recorded.' : (response.data.error || 'Request failed.'), response.ok);
      if (response.ok) {
        loadSnapshots();
      }
    });
  });

  results.addEventListener('click', function (event) {
    var target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    var snapshotId = target.getAttribute('data-delete-id');
    if (!snapshotId) {
      return;
    }
    api('DELETE', '/api/v1/storage-quota/snapshots/' + encodeURIComponent(snapshotId)).then(function (response) {
      setStatus(response.ok ? 'Snapshot deleted.' : (response.data.error || 'Delete failed.'), response.ok);
      if (response.ok) {
        loadSnapshots();
      }
    });
  });

  document.getElementById('sqm-load-snapshots').addEventListener('click', loadSnapshots);
  document.getElementById('sqm-load-stats').addEventListener('click', loadStats);
  document.getElementById('sqm-load-types').addEventListener('click', loadTypes);

  loadTypes();
  loadSnapshots();
})();
