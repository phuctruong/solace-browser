// Diagram: 02-dashboard-login
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

  function loadContentTypes() {
    fetch('/api/v1/clipboard/content-types')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('clp-content-type');
        (data.content_types || []).forEach(function (ct) {
          var opt = document.createElement('option');
          opt.value = ct;
          opt.textContent = ct;
          sel.appendChild(opt);
        });
      });
  }

  function loadStats() {
    fetch('/api/v1/clipboard/stats', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('clp-stats');
        el.innerHTML = [
          ['Total Entries', data.total_entries],
          ['Sensitive', data.sensitive_count],
          ['Total Chars', data.total_chars],
        ].map(function (pair) {
          return '<div class="clp-stat-card"><div class="clp-stat-value">' + escHtml(String(pair[1])) +
            '</div><div class="clp-stat-label">' + escHtml(pair[0]) + '</div></div>';
        }).join('');
      });
  }

  function loadList() {
    fetch('/api/v1/clipboard/entries', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('clp-list');
        var entries = data.entries || [];
        if (!entries.length) {
          el.innerHTML = '<p style="color:var(--hub-text-muted)">No entries yet.</p>';
          return;
        }
        el.innerHTML = entries.map(function (e) {
          var sensitive = e.is_sensitive
            ? '<span class="clp-badge clp-badge-sensitive">sensitive</span>' : '';
          return '<div class="clp-item">' +
            '<div class="clp-item-meta">' +
            '<span class="clp-badge">' + escHtml(e.content_type) + '</span>' +
            sensitive +
            '<span>' + escHtml(e.char_count) + ' chars</span>' +
            '<span style="color:var(--hub-text-muted);font-size:0.75rem">' + escHtml(e.copied_at) + '</span>' +
            '</div>' +
            '<button class="clp-delete-btn" data-id="' + escHtml(e.entry_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('.clp-delete-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteEntry(btn.getAttribute('data-id'));
          });
        });
      });
  }

  function deleteEntry(id) {
    fetch('/api/v1/clipboard/entries/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(function () { refresh(); });
  }

  function clearAll() {
    if (!confirm('Clear all clipboard entries?')) return;
    fetch('/api/v1/clipboard/entries', { method: 'DELETE', headers: authHeaders() })
      .then(function () { refresh(); });
  }

  function refresh() {
    loadStats();
    loadList();
  }

  document.getElementById('clp-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var contentType = document.getElementById('clp-content-type').value;
    var charCount = parseInt(document.getElementById('clp-char-count').value, 10) || 0;
    var content = document.getElementById('clp-content').value;
    var sourceUrl = document.getElementById('clp-source-url').value || undefined;
    fetch('/api/v1/clipboard/entries', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ content_type: contentType, char_count: charCount, content: content, source_url: sourceUrl }),
    }).then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.entry_id) { refresh(); }
        else { alert('Error: ' + (data.error || 'unknown')); }
      });
  });

  document.getElementById('clp-clear-btn').addEventListener('click', clearAll);

  loadContentTypes();
  refresh();
}());
