// Diagram: 02-dashboard-login
/* code-snippet-saver.js — Code Snippet Saver | Task 095 | IIFE + escHtml */
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

  function renderSnippets(snippets) {
    var list = document.getElementById('cs-list');
    var items = '';
    snippets.forEach(function (s) {
      items += '<div class="cs-item"><div>' +
        '<div class="cs-item-lang">' + escHtml(s.language) + '</div>' +
        '<div class="cs-item-meta">Tags: ' + escHtml((s.tags || []).join(', ') || 'none') +
        ' | ' + escHtml(s.created_at) + '</div>' +
        '</div>' +
        '<button class="cs-btn cs-btn-danger" data-id="' + escHtml(s.snippet_id) + '">Delete</button>' +
        '</div>';
    });
    list.innerHTML = items || '<p class="cs-loading">No snippets yet.</p>';
    list.querySelectorAll('[data-id]').forEach(function (btn) {
      btn.addEventListener('click', function () { deleteSnippet(btn.dataset.id); });
    });
  }

  function loadSnippets(language) {
    var url = '/api/v1/snippets';
    if (language) {
      url = '/api/v1/snippets/by-language?language=' + encodeURIComponent(language);
    }
    fetch(url, {
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) { renderSnippets(d.snippets || []); })
      .catch(function () { document.getElementById('cs-list').textContent = 'Failed to load snippets.'; });
  }

  function deleteSnippet(snippetId) {
    fetch('/api/v1/snippets/' + encodeURIComponent(snippetId), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function () { loadSnippets(); });
  }

  document.getElementById('cs-save-btn').addEventListener('click', function () {
    var language = document.getElementById('cs-language').value;
    var code = document.getElementById('cs-code').value.trim() || 'empty';
    var desc = document.getElementById('cs-desc').value.trim() || 'empty';
    var sourceUrl = document.getElementById('cs-source-url').value.trim() || 'unknown';
    var tagsRaw = document.getElementById('cs-tags').value.trim();
    var tags = tagsRaw ? tagsRaw.split(',').map(function (t) { return t.trim(); }).filter(Boolean) : [];
    var msg = document.getElementById('cs-save-msg');
    Promise.all([sha256Hex(code), sha256Hex(desc), sha256Hex(sourceUrl)]).then(function (hashes) {
      return fetch('/api/v1/snippets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + (window._solaceToken || ''),
        },
        body: JSON.stringify({
          language: language,
          code_hash: hashes[0],
          description_hash: hashes[1],
          source_url_hash: hashes[2],
          tags: tags,
        }),
      });
    }).then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status === 'saved') {
          showMsg(msg, 'Snippet saved!', false);
          loadSnippets();
        } else {
          showMsg(msg, d.error || 'Error', true);
        }
      })
      .catch(function () { showMsg(msg, 'Network error', true); });
  });

  document.getElementById('cs-filter-btn').addEventListener('click', function () {
    var lang = document.getElementById('cs-filter-lang').value;
    loadSnippets(lang);
  });

  loadSnippets();
}());
