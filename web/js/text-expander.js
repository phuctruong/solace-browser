// Diagram: 02-dashboard-login
/* Text Expander — Task 123 */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var panel = document.getElementById('txe-panel');
  var status = document.getElementById('txe-status');
  var form = document.getElementById('txe-form');
  var abbrevInput = document.getElementById('txe-abbrev');
  var contentInput = document.getElementById('txe-content');
  var categorySelect = document.getElementById('txe-category');
  var tagsInput = document.getElementById('txe-tags');

  function setStatus(msg) { status.textContent = msg; }

  function authHeaders() {
    return { 'Authorization': 'Bearer ' + (window.__solace_token || '') };
  }

  function loadCategories() {
    fetch('/api/v1/text-expander/categories')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        categorySelect.innerHTML = (data.categories || []).map(function (c) {
          return '<option value="' + escHtml(c) + '">' + escHtml(c.replace('_', ' ')) + '</option>';
        }).join('');
      })
      .catch(function (e) { setStatus('Error loading categories: ' + escHtml(String(e))); });
  }

  function renderSnippets(snippets) {
    if (!snippets.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No snippets added yet.</p>';
      return;
    }
    panel.innerHTML = snippets.map(function (s) {
      var tags = (s.tags || []).map(function (t) { return escHtml(t); }).join(', ');
      return '<div class="txe-item">'
        + '<div>'
        + '<div class="txe-item-id">' + escHtml(s.snippet_id) + ' <span class="txe-use-count">' + escHtml(s.use_count) + ' uses</span></div>'
        + '<div class="txe-item-meta">Category: ' + escHtml(s.category)
        + (tags ? ' | Tags: ' + tags : '') + '</div>'
        + '</div>'
        + '<button class="txe-btn txe-btn-danger" data-delete="' + escHtml(s.snippet_id) + '">Delete</button>'
        + '</div>';
    }).join('');

    panel.querySelectorAll('[data-delete]').forEach(function (btn) {
      btn.addEventListener('click', function () { deleteSnippet(btn.getAttribute('data-delete')); });
    });
  }

  function renderStats(data) {
    panel.innerHTML = '<div class="txe-stat-grid">'
      + '<div class="txe-stat-card"><div class="txe-stat-value">' + escHtml(data.total_snippets) + '</div><div class="txe-stat-label">Snippets</div></div>'
      + '<div class="txe-stat-card"><div class="txe-stat-value">' + escHtml(data.total_expansions) + '</div><div class="txe-stat-label">Total Expansions</div></div>'
      + '<div class="txe-stat-card"><div class="txe-stat-value">' + escHtml(data.top_snippet_id || '—') + '</div><div class="txe-stat-label">Top Snippet</div></div>'
      + '</div>';
  }

  function loadSnippets() {
    fetch('/api/v1/text-expander/snippets', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderSnippets(data.snippets || []);
        setStatus('Snippets loaded: ' + (data.total || 0));
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadStats() {
    fetch('/api/v1/text-expander/stats', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderStats(data);
        setStatus('Stats loaded.');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function showCategories() {
    fetch('/api/v1/text-expander/categories')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        panel.innerHTML = '<p class="txe-item-meta">Categories: ' + escHtml((data.categories || []).join(', ')) + '</p>';
        setStatus('Categories loaded.');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function deleteSnippet(snippetId) {
    fetch('/api/v1/text-expander/snippets/' + encodeURIComponent(snippetId), {
      method: 'DELETE',
      headers: authHeaders()
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        setStatus('Snippet deleted.');
        loadSnippets();
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var abbrev = abbrevInput.value.trim();
    var content = contentInput.value.trim();
    var category = categorySelect.value;
    var rawTags = tagsInput.value.trim();
    var tags = rawTags ? rawTags.split(',').map(function (t) { return t.trim(); }).filter(Boolean) : [];
    if (!abbrev || !content) { setStatus('Abbreviation and content required.'); return; }
    if (tags.length > 5) { setStatus('Max 5 tags allowed.'); return; }
    fetch('/api/v1/text-expander/snippets', {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
      body: JSON.stringify({ abbreviation: abbrev, content: content, category: category, tags: tags })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.snippet) {
          abbrevInput.value = '';
          contentInput.value = '';
          tagsInput.value = '';
          setStatus('Snippet added: ' + escHtml(data.snippet.snippet_id));
          loadSnippets();
        } else {
          setStatus('Error: ' + escHtml(data.error || 'unknown'));
        }
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  document.getElementById('btn-txe-snippets').addEventListener('click', loadSnippets);
  document.getElementById('btn-txe-stats').addEventListener('click', loadStats);
  document.getElementById('btn-txe-categories').addEventListener('click', showCategories);

  loadCategories();
  loadSnippets();
})();
