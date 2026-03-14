// Diagram: 02-dashboard-login
/* reading-mode.js — Reading Mode | Task 094 | IIFE + escHtml */
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showMsg(el, text, isError) {
    el.textContent = text;
    el.style.color = isError ? 'var(--hub-danger)' : 'var(--hub-success)';
    el.hidden = false;
    setTimeout(function () { el.hidden = true; }, 4000);
  }

  function sha256Hex(str) {
    var encoder = new TextEncoder();
    var data = encoder.encode(str);
    return crypto.subtle.digest('SHA-256', data).then(function (buf) {
      return Array.from(new Uint8Array(buf)).map(function (b) {
        return b.toString(16).padStart(2, '0');
      }).join('');
    });
  }

  function loadSessions() {
    var list = document.getElementById('rm-list');
    fetch('/api/v1/reading-mode/sessions', {
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = '';
        (d.sessions || []).forEach(function (s) {
          items += '<div class="rm-item"><div>' +
            '<div>' + escHtml(s.session_id) + '</div>' +
            '<div class="rm-item-meta">Words: ' + escHtml(String(s.word_count)) +
            ' | Est. ' + escHtml(String(s.reading_time_mins)) + ' min | ' +
            escHtml(s.created_at) + '</div>' +
            '</div>' +
            '<button class="rm-btn rm-btn-danger" data-id="' + escHtml(s.session_id) + '">Delete</button>' +
            '</div>';
        });
        list.innerHTML = items || '<p class="rm-loading">No sessions yet.</p>';
        list.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteSession(btn.dataset.id); });
        });
      })
      .catch(function () { list.textContent = 'Failed to load sessions.'; });
  }

  function deleteSession(sessionId) {
    fetch('/api/v1/reading-mode/sessions/' + encodeURIComponent(sessionId), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function () { loadSessions(); });
  }

  document.getElementById('rm-save-settings-btn').addEventListener('click', function () {
    var theme = document.getElementById('rm-theme').value;
    var fontSize = parseInt(document.getElementById('rm-font-size').value, 10);
    var columnWidth = document.getElementById('rm-column-width').value;
    var msg = document.getElementById('rm-settings-msg');
    fetch('/api/v1/reading-mode/settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + (window._solaceToken || ''),
      },
      body: JSON.stringify({ theme: theme, font_size: fontSize, column_width: columnWidth }),
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status === 'updated') {
          showMsg(msg, 'Settings saved!', false);
        } else {
          showMsg(msg, d.error || 'Error', true);
        }
      })
      .catch(function () { showMsg(msg, 'Network error', true); });
  });

  document.getElementById('rm-create-btn').addEventListener('click', function () {
    var url = document.getElementById('rm-url').value.trim() || 'unknown';
    var title = document.getElementById('rm-title').value.trim() || 'unknown';
    var wordCount = parseInt(document.getElementById('rm-word-count').value, 10) || 0;
    var msg = document.getElementById('rm-create-msg');
    Promise.all([sha256Hex(url), sha256Hex(title)]).then(function (hashes) {
      return fetch('/api/v1/reading-mode/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + (window._solaceToken || ''),
        },
        body: JSON.stringify({ url_hash: hashes[0], title_hash: hashes[1], word_count: wordCount }),
      });
    }).then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status === 'created') {
          showMsg(msg, 'Session started!', false);
          loadSessions();
        } else {
          showMsg(msg, d.error || 'Error', true);
        }
      })
      .catch(function () { showMsg(msg, 'Network error', true); });
  });

  loadSessions();
}());
