(function () {
  'use strict';

  var results = document.getElementById('rte-results');
  var status = document.getElementById('rte-status');
  var typeSelect = document.getElementById('rte-resource-type');

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message, ok) {
    status.className = ok ? 'rte-status rte-success' : 'rte-status';
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
    results.innerHTML = '<pre class="rte-code">' + escHtml(JSON.stringify(data, null, 2)) + '</pre>';
  }

  function renderEntries(items) {
    if (!items.length) {
      renderCode({ entries: [] });
      return;
    }
    results.innerHTML = items.map(function (item) {
      return '<article class="rte-item">'
        + '<strong>' + escHtml(item.entry_id) + '</strong>'
        + '<div class="rte-meta"><span>' + escHtml(item.resource_type) + '</span><span>' + escHtml(item.duration_ms) + ' ms</span><span>Transfer ' + escHtml(item.transfer_size_bytes) + '</span><span>Cache ' + escHtml(item.cache_hit) + '</span></div>'
        + '<div class="rte-meta"><span>URL hash ' + escHtml(item.url_hash) + '</span><span>Page hash ' + escHtml(item.page_url_hash) + '</span></div>'
        + '<button class="rte-danger" type="button" data-delete-id="' + escHtml(item.entry_id) + '">Delete</button>'
        + '</article>';
    }).join('');
  }

  function loadTypes() {
    api('GET', '/api/v1/resource-timing/resource-types').then(function (response) {
      var items = response.data.resource_types || [];
      typeSelect.innerHTML = items.map(function (item) {
        return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
      }).join('');
      renderCode(response.data);
      setStatus('Loaded resource types.', response.ok);
    });
  }

  function loadEntries() {
    api('GET', '/api/v1/resource-timing/entries').then(function (response) {
      renderEntries(response.data.entries || []);
      setStatus('Loaded entries.', response.ok);
    });
  }

  function loadStats() {
    api('GET', '/api/v1/resource-timing/stats').then(function (response) {
      renderCode(response.data);
      setStatus('Loaded stats.', response.ok);
    });
  }

  document.getElementById('rte-form').addEventListener('submit', function (event) {
    event.preventDefault();
    api('POST', '/api/v1/resource-timing/entries', {
      resource_type: typeSelect.value,
      url: document.getElementById('rte-url').value,
      page_url: document.getElementById('rte-page-url').value,
      duration_ms: document.getElementById('rte-duration-ms').value,
      transfer_size_bytes: Number(document.getElementById('rte-transfer-size').value),
      cache_hit: document.getElementById('rte-cache-hit').checked
    }).then(function (response) {
      renderCode(response.data);
      setStatus(response.ok ? 'Entry recorded.' : (response.data.error || 'Request failed.'), response.ok);
      if (response.ok) {
        loadEntries();
      }
    });
  });

  results.addEventListener('click', function (event) {
    var target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    var entryId = target.getAttribute('data-delete-id');
    if (!entryId) {
      return;
    }
    api('DELETE', '/api/v1/resource-timing/entries/' + encodeURIComponent(entryId)).then(function (response) {
      setStatus(response.ok ? 'Entry deleted.' : (response.data.error || 'Delete failed.'), response.ok);
      if (response.ok) {
        loadEntries();
      }
    });
  });

  document.getElementById('rte-load-entries').addEventListener('click', loadEntries);
  document.getElementById('rte-load-stats').addEventListener('click', loadStats);
  document.getElementById('rte-load-types').addEventListener('click', loadTypes);

  loadTypes();
  loadEntries();
})();
