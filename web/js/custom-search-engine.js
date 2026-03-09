/* Custom Search Engine — Task 121 */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var panel = document.getElementById('cse-panel');
  var status = document.getElementById('cse-status');
  var form = document.getElementById('cse-form');
  var nameInput = document.getElementById('cse-name');
  var urlInput = document.getElementById('cse-url');
  var categorySelect = document.getElementById('cse-category');

  function setStatus(msg) { status.textContent = msg; }

  function loadCategories() {
    fetch('/api/v1/custom-search/categories')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var cats = data.categories || [];
        categorySelect.innerHTML = cats.map(function (c) {
          return '<option value="' + escHtml(c) + '">' + escHtml(c) + '</option>';
        }).join('');
      })
      .catch(function (e) { setStatus('Error loading categories: ' + escHtml(String(e))); });
  }

  function renderEngines(engines) {
    if (!engines.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No search engines added yet.</p>';
      return;
    }
    panel.innerHTML = engines.map(function (e) {
      var activeClass = e.is_active ? ' cse-item-active' : '';
      var activeBadge = e.is_active ? '<span class="cse-badge">Active</span>' : '';
      return '<div class="cse-item' + activeClass + '">'
        + '<div>'
        + '<div class="cse-item-id">' + escHtml(e.engine_id) + ' ' + activeBadge + '</div>'
        + '<div class="cse-item-meta">Category: ' + escHtml(e.category)
        + ' | Added: ' + escHtml(e.added_at) + '</div>'
        + '</div>'
        + '<div class="cse-item-actions">'
        + '<button class="cse-btn cse-btn-activate" data-activate="' + escHtml(e.engine_id) + '">Activate</button>'
        + '<button class="cse-btn cse-btn-danger" data-delete="' + escHtml(e.engine_id) + '">Delete</button>'
        + '</div>'
        + '</div>';
    }).join('');

    panel.querySelectorAll('[data-delete]').forEach(function (btn) {
      btn.addEventListener('click', function () { deleteEngine(btn.getAttribute('data-delete')); });
    });
    panel.querySelectorAll('[data-activate]').forEach(function (btn) {
      btn.addEventListener('click', function () { activateEngine(btn.getAttribute('data-activate')); });
    });
  }

  function loadEngines() {
    fetch('/api/v1/custom-search/engines', {
      headers: { 'Authorization': 'Bearer ' + (window.__solace_token || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderEngines(data.engines || []);
        setStatus('Engines loaded: ' + (data.total || 0));
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadActive() {
    fetch('/api/v1/custom-search/active', {
      headers: { 'Authorization': 'Bearer ' + (window.__solace_token || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.engine) {
          panel.innerHTML = '<div class="cse-item cse-item-active">'
            + '<div><div class="cse-item-id">' + escHtml(data.engine.engine_id) + ' <span class="cse-badge">Active</span></div>'
            + '<div class="cse-item-meta">Category: ' + escHtml(data.engine.category) + '</div></div>'
            + '</div>';
          setStatus('Active engine found.');
        } else {
          panel.innerHTML = '<p style="color:var(--hub-muted)">No active engine set.</p>';
          setStatus('No active engine.');
        }
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function activateEngine(engineId) {
    fetch('/api/v1/custom-search/engines/' + encodeURIComponent(engineId) + '/activate', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + (window.__solace_token || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        setStatus('Engine activated.');
        loadEngines();
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function deleteEngine(engineId) {
    fetch('/api/v1/custom-search/engines/' + encodeURIComponent(engineId), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window.__solace_token || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        setStatus('Engine deleted.');
        loadEngines();
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var name = nameInput.value.trim();
    var urlTemplate = urlInput.value.trim();
    var category = categorySelect.value;
    if (!name || !urlTemplate) { setStatus('Name and URL template required.'); return; }
    fetch('/api/v1/custom-search/engines', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + (window.__solace_token || '')
      },
      body: JSON.stringify({ name: name, url_template: urlTemplate, category: category })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.engine) {
          nameInput.value = '';
          urlInput.value = '';
          setStatus('Engine added: ' + escHtml(data.engine.engine_id));
          loadEngines();
        } else {
          setStatus('Error: ' + escHtml(data.error || 'unknown'));
        }
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  document.getElementById('btn-cse-list').addEventListener('click', loadEngines);
  document.getElementById('btn-cse-categories').addEventListener('click', function () {
    fetch('/api/v1/custom-search/categories')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        panel.innerHTML = '<p class="cse-item-meta">Categories: ' + escHtml((data.categories || []).join(', ')) + '</p>';
        setStatus('Categories loaded.');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });
  document.getElementById('btn-cse-active').addEventListener('click', loadActive);

  loadCategories();
  loadEngines();
})();
