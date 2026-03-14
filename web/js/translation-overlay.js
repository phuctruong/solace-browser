// Diagram: 02-dashboard-login
/* translation-overlay.js — Translation Overlay | Task 092 | IIFE + escHtml */
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

  function loadHistory() {
    var list = document.getElementById('to-history');
    fetch('/api/v1/translation/history', {
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = '';
        (d.history || []).forEach(function (t) {
          items += '<div class="to-item">' +
            '<div class="to-item-langs">' + escHtml(t.source_lang) + ' → ' + escHtml(t.target_lang) + '</div>' +
            '<div class="to-item-meta">Chars: ' + escHtml(String(t.char_count)) +
            ' | ' + escHtml(t.created_at) + '</div></div>';
        });
        list.innerHTML = items || '<p class="to-loading">No history yet.</p>';
      })
      .catch(function () { list.textContent = 'Failed to load history.'; });
  }

  function loadStats() {
    var stats = document.getElementById('to-stats');
    fetch('/api/v1/translation/stats', {
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        stats.innerHTML = '<strong>Total:</strong> ' + escHtml(String(d.total));
      })
      .catch(function () { stats.textContent = 'Failed to load stats.'; });
  }

  document.getElementById('to-translate-btn').addEventListener('click', function () {
    var sourceLang = document.getElementById('to-source-lang').value;
    var targetLang = document.getElementById('to-target-lang').value;
    var charCount = parseInt(document.getElementById('to-char-count').value, 10) || 0;
    var msg = document.getElementById('to-translate-msg');
    var placeholder = 'placeholder-' + Date.now();
    Promise.all([sha256Hex(placeholder), sha256Hex('result-' + placeholder)]).then(function (hashes) {
      return fetch('/api/v1/translation/translate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + (window._solaceToken || ''),
        },
        body: JSON.stringify({
          source_lang: sourceLang,
          target_lang: targetLang,
          text_hash: hashes[0],
          result_hash: hashes[1],
          char_count: charCount,
        }),
      });
    }).then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status === 'translated') {
          showMsg(msg, 'Translation recorded!', false);
          loadHistory();
          loadStats();
        } else {
          showMsg(msg, d.error || 'Error', true);
        }
      })
      .catch(function () { showMsg(msg, 'Network error', true); });
  });

  document.getElementById('to-clear-btn').addEventListener('click', function () {
    fetch('/api/v1/translation/history', {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function () { loadHistory(); loadStats(); });
  });

  loadHistory();
  loadStats();
}());
