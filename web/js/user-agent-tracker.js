// Diagram: 02-dashboard-login
(function () {
  'use strict';

  var results = document.getElementById('uat-results');
  var status = document.getElementById('uat-status');
  var platformSelect = document.getElementById('uat-platform');

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message, ok) {
    status.className = ok ? 'uat-status uat-success' : 'uat-status';
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
    results.innerHTML = '<pre class="uat-code">' + escHtml(JSON.stringify(data, null, 2)) + '</pre>';
  }

  function renderSnapshots(items) {
    if (!items.length) {
      renderCode({ snapshots: [] });
      return;
    }
    results.innerHTML = items.map(function (item) {
      return '<article class="uat-item">'
        + '<strong>' + escHtml(item.snapshot_id) + '</strong>'
        + '<div class="uat-meta"><span>' + escHtml(item.platform) + '</span><span>' + escHtml(item.browser) + '</span><span>Mobile ' + escHtml(item.is_mobile) + '</span><span>Spoofed ' + escHtml(item.is_spoofed) + '</span></div>'
        + '<div class="uat-meta"><span>UA hash ' + escHtml(item.ua_hash) + '</span><span>' + escHtml(item.recorded_at) + '</span></div>'
        + '<button class="uat-danger" type="button" data-delete-id="' + escHtml(item.snapshot_id) + '">Delete</button>'
        + '</article>';
    }).join('');
  }

  function loadPlatforms() {
    api('GET', '/api/v1/user-agent/platforms').then(function (response) {
      var items = response.data.platforms || [];
      platformSelect.innerHTML = items.map(function (item) {
        return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
      }).join('');
      renderCode(response.data);
      setStatus('Loaded platform metadata.', response.ok);
    });
  }

  function loadSnapshots() {
    api('GET', '/api/v1/user-agent/snapshots').then(function (response) {
      renderSnapshots(response.data.snapshots || []);
      setStatus('Loaded snapshots.', response.ok);
    });
  }

  function loadStats() {
    api('GET', '/api/v1/user-agent/stats').then(function (response) {
      renderCode(response.data);
      setStatus('Loaded stats.', response.ok);
    });
  }

  document.getElementById('uat-form').addEventListener('submit', function (event) {
    event.preventDefault();
    api('POST', '/api/v1/user-agent/snapshots', {
      platform: platformSelect.value,
      browser: document.getElementById('uat-browser').value,
      user_agent: document.getElementById('uat-user-agent').value,
      is_mobile: document.getElementById('uat-mobile').checked,
      is_spoofed: document.getElementById('uat-spoofed').checked
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
    api('DELETE', '/api/v1/user-agent/snapshots/' + encodeURIComponent(snapshotId)).then(function (response) {
      setStatus(response.ok ? 'Snapshot deleted.' : (response.data.error || 'Delete failed.'), response.ok);
      if (response.ok) {
        loadSnapshots();
      }
    });
  });

  document.getElementById('uat-load-snapshots').addEventListener('click', loadSnapshots);
  document.getElementById('uat-load-stats').addEventListener('click', loadStats);
  document.getElementById('uat-load-platforms').addEventListener('click', loadPlatforms);

  loadPlatforms();
  loadSnapshots();
})();
