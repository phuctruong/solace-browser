// Diagram: 02-dashboard-login
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function apiGet(path) {
    return fetch(path).then(function (r) { return r.json(); });
  }

  function apiPost(path, body) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function apiDelete(path) {
    return fetch(path, { method: 'DELETE' }).then(function (r) { return r.json(); });
  }

  function updateBadge(settings) {
    var badge = document.getElementById('ps-status-badge');
    if (!badge) return;
    if (settings.enabled && settings.type !== 'direct') {
      badge.textContent = 'Active (' + settings.type + ')';
      badge.className = 'ps-badge ps-badge-active';
    } else {
      badge.textContent = 'Disabled (direct)';
      badge.className = 'ps-badge ps-badge-disabled';
    }
    if (settings.test_status === 'error') {
      badge.textContent = 'Error';
      badge.className = 'ps-badge ps-badge-error';
    }
  }

  function loadSettings() {
    apiGet('/api/v1/proxy/settings').then(function (data) {
      updateBadge(data);
      var t = document.getElementById('ps-type');
      var h = document.getElementById('ps-host');
      var p = document.getElementById('ps-port');
      var u = document.getElementById('ps-username');
      if (t) t.value = data.type || 'direct';
      if (h) h.value = data.host || '';
      if (p) p.value = data.port || '';
      if (u) u.value = data.username || '';
    });
  }

  function loadPresets() {
    apiGet('/api/v1/proxy/presets').then(function (data) {
      var container = document.getElementById('ps-presets');
      if (!container) return;
      var presets = data.presets || [];
      container.innerHTML = presets.map(function (p) {
        return '<button class="ps-preset-btn" onclick="window._psApplyPreset(\'' +
          escHtml(p.type) + '\',\'' + escHtml(p.host || '') + '\',' +
          (p.port || 'null') + ')">' + escHtml(p.name) + '</button>';
      }).join('');
    });
  }

  window._psApplyPreset = function (type, host, port) {
    var t = document.getElementById('ps-type');
    var h = document.getElementById('ps-host');
    var p = document.getElementById('ps-port');
    if (t) t.value = type;
    if (h) h.value = host || '';
    if (p) p.value = port || '';
  };

  var form = document.getElementById('ps-form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var type = document.getElementById('ps-type').value;
      var host = document.getElementById('ps-host').value.trim();
      var portVal = document.getElementById('ps-port').value;
      var user = document.getElementById('ps-username').value.trim();
      var pass = document.getElementById('ps-password').value;
      var body = { type: type, enabled: type !== 'direct' };
      if (host) body.host = host;
      if (portVal) body.port = parseInt(portVal, 10);
      if (user) body.username = user;
      if (pass) body.password = pass;
      var status = document.getElementById('ps-form-status');
      apiPost('/api/v1/proxy/settings', body).then(function (data) {
        if (status) {
          status.textContent = data.status === 'updated' ? 'Saved.' : ('Error: ' + escHtml(data.error || 'unknown'));
        }
        loadSettings();
      });
    });
  }

  var testBtn = document.getElementById('ps-test-btn');
  if (testBtn) {
    testBtn.addEventListener('click', function () {
      var status = document.getElementById('ps-form-status');
      apiPost('/api/v1/proxy/test', {}).then(function (data) {
        if (status) {
          status.textContent = data.status === 'ok'
            ? 'Connection OK, latency: ' + escHtml(String(data.latency_ms)) + 'ms'
            : 'Test failed: ' + escHtml(data.error || 'unknown');
        }
        loadSettings();
      });
    });
  }

  var resetBtn = document.getElementById('ps-reset-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', function () {
      var status = document.getElementById('ps-form-status');
      apiDelete('/api/v1/proxy/settings').then(function (data) {
        if (status) {
          status.textContent = data.status === 'reset' ? 'Reset to direct.' : ('Error: ' + escHtml(data.error || 'unknown'));
        }
        loadSettings();
      });
    });
  }

  loadSettings();
  loadPresets();
}());
