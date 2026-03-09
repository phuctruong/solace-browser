(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function authHeaders() {
    var token = window.__SOLACE_TOKEN__ || '';
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token };
  }

  function loadActionTypes() {
    fetch('/api/v1/shortcuts/action-types')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('shc-action-type');
        var badgesEl = document.getElementById('shc-action-types');
        var types = data.action_types || [];
        types.forEach(function (at) {
          var opt = document.createElement('option');
          opt.value = at;
          opt.textContent = at;
          sel.appendChild(opt);
        });
        badgesEl.innerHTML = types.map(function (at) {
          return '<span class="shc-badge">' + escHtml(at) + '</span>';
        }).join('');
      });
  }

  function loadStats() {
    fetch('/api/v1/shortcuts/stats', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('shc-stats');
        el.innerHTML = [
          ['Total', data.total_shortcuts],
          ['Enabled', data.enabled_count],
          ['Most Used', data.most_used || '—'],
        ].map(function (pair) {
          return '<div class="shc-stat-card"><div class="shc-stat-value">' + escHtml(String(pair[1])) +
            '</div><div class="shc-stat-label">' + escHtml(pair[0]) + '</div></div>';
        }).join('');
      });
  }

  function loadList() {
    fetch('/api/v1/shortcuts/shortcuts', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('shc-list');
        var shortcuts = data.shortcuts || [];
        if (!shortcuts.length) {
          el.innerHTML = '<p style="color:var(--hub-text-muted)">No shortcuts yet.</p>';
          return;
        }
        el.innerHTML = shortcuts.map(function (s) {
          var enabledBadge = s.is_enabled
            ? '<span class="shc-item-badge shc-item-badge-enabled">enabled</span>'
            : '<span class="shc-item-badge">disabled</span>';
          return '<div class="shc-item">' +
            '<div class="shc-item-meta">' +
            '<span class="shc-key">' + escHtml(s.key_combo) + '</span>' +
            '<span class="shc-item-badge">' + escHtml(s.action_type) + '</span>' +
            enabledBadge +
            (s.description ? '<span>' + escHtml(s.description) + '</span>' : '') +
            '</div>' +
            '<button class="shc-delete-btn" data-id="' + escHtml(s.shortcut_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('.shc-delete-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteShortcut(btn.getAttribute('data-id'));
          });
        });
      });
  }

  function deleteShortcut(id) {
    fetch('/api/v1/shortcuts/shortcuts/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(function () { refresh(); });
  }

  function refresh() {
    loadStats();
    loadList();
  }

  document.getElementById('shc-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var actionType = document.getElementById('shc-action-type').value;
    var keyCombo = document.getElementById('shc-key-combo').value;
    var description = document.getElementById('shc-description').value;
    var isEnabled = document.getElementById('shc-is-enabled').checked;
    fetch('/api/v1/shortcuts/shortcuts', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ action_type: actionType, key_combo: keyCombo, description: description, is_enabled: isEnabled }),
    }).then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.shortcut_id) { refresh(); }
        else { alert('Error: ' + (data.error || 'unknown')); }
      });
  });

  loadActionTypes();
  refresh();
}());
