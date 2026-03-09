/* Download Manager v2 — Task 086 */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var panel = document.getElementById('dm-panel');
  var status = document.getElementById('dm-status');

  function setStatus(msg) {
    status.textContent = msg;
  }

  function renderQueue(items) {
    if (!items.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No downloads queued.</p>';
      return;
    }
    panel.innerHTML = items.map(function (d) {
      return '<div class="dm-item">'
        + '<div class="dm-item-info">'
        + '<span class="dm-item-id">' + escHtml(d.download_id) + '</span>'
        + '<span class="dm-item-meta">Type: ' + escHtml(d.file_type) + ' | Status: ' + escHtml(d.status) + ' | Size: ' + escHtml(d.size_bytes) + ' bytes</span>'
        + '</div>'
        + '<button class="dm-btn dm-btn-danger" data-id="' + escHtml(d.download_id) + '" data-action="remove">Remove</button>'
        + '</div>';
    }).join('');
  }

  function renderHistory(items) {
    if (!items.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No completed downloads.</p>';
      return;
    }
    panel.innerHTML = items.map(function (d) {
      return '<div class="dm-item">'
        + '<div class="dm-item-info">'
        + '<span class="dm-item-id">' + escHtml(d.download_id) + '</span>'
        + '<span class="dm-item-meta">Type: ' + escHtml(d.file_type) + ' | Completed: ' + escHtml(d.completed_at || '') + '</span>'
        + '</div>'
        + '</div>';
    }).join('');
  }

  function renderTypes(types) {
    panel.innerHTML = '<p class="dm-item-meta">File types: ' + escHtml(types.join(', ')) + '</p>';
  }

  function loadQueue() {
    fetch('/api/v1/downloads/queue')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderQueue(data.queue || []);
        setStatus('Queue loaded: ' + (data.total || 0) + ' items');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadHistory() {
    fetch('/api/v1/downloads/history')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderHistory(data.history || []);
        setStatus('History loaded: ' + (data.total || 0) + ' items');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadTypes() {
    fetch('/api/v1/downloads/file-types')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderTypes(data.file_types || []);
        setStatus('File types loaded');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  document.getElementById('btn-dm-queue').addEventListener('click', loadQueue);
  document.getElementById('btn-dm-history').addEventListener('click', loadHistory);
  document.getElementById('btn-dm-types').addEventListener('click', loadTypes);

  panel.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-action="remove"]');
    if (!btn) { return; }
    var dlId = btn.getAttribute('data-id');
    fetch('/api/v1/downloads/queue/' + encodeURIComponent(dlId), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () { loadQueue(); })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  loadQueue();
})();
