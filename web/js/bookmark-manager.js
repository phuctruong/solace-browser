(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var API = '/api/v1/bookmarks';
  var authToken = '';

  function setStatus(msg, ok) {
    var el = document.getElementById('bm-status');
    el.textContent = msg;
    el.style.color = ok === false ? 'var(--hub-danger)' : 'var(--hub-success)';
  }

  function loadTags() {
    fetch(API + '/tags')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var bar = document.getElementById('bm-tags-bar');
        bar.innerHTML = '';
        if (!data.tags) return;
        data.tags.forEach(function (tag) {
          var btn = document.createElement('button');
          btn.className = 'bm-tag-filter';
          btn.textContent = escHtml(tag);
          btn.addEventListener('click', function () {
            document.getElementById('bm-search').value = tag;
            loadBookmarks(tag);
          });
          bar.appendChild(btn);
        });
      });
  }

  function loadBookmarks(searchQ) {
    var url = searchQ ? API + '/search?q=' + encodeURIComponent(searchQ) : API;
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderTable(data.bookmarks || []);
      });
  }

  function renderTable(bookmarks) {
    var tbody = document.getElementById('bm-tbody');
    tbody.innerHTML = '';
    bookmarks.forEach(function (b) {
      var tr = document.createElement('tr');
      var tags = (b.tags || []).map(function (t) {
        return '<span class="bm-tag-pill">' + escHtml(t) + '</span>';
      }).join('');
      tr.innerHTML = '<td>' + escHtml(b.title || '') + '</td>' +
        '<td class="bm-hash">' + escHtml((b.url_hash || '').slice(0, 16)) + '…</td>' +
        '<td>' + tags + '</td>' +
        '<td>' + escHtml((b.created_at || '').slice(0, 10)) + '</td>' +
        '<td><button class="bm-btn bm-btn-danger" data-id="' + escHtml(b.bookmark_id) + '">Delete</button></td>';
      tbody.appendChild(tr);
    });
    tbody.querySelectorAll('[data-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        deleteBookmark(btn.getAttribute('data-id'));
      });
    });
  }

  function addBookmark() {
    var url = document.getElementById('bm-url').value.trim();
    var title = document.getElementById('bm-title').value.trim();
    var tagsRaw = document.getElementById('bm-tags').value.trim();
    var tags = tagsRaw ? tagsRaw.split(',').map(function (t) { return t.trim(); }).filter(Boolean) : [];
    if (!url) { setStatus('URL required', false); return; }
    fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken },
      body: JSON.stringify({ url: url, title: title, tags: tags }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (res.ok) {
          setStatus('Bookmark added', true);
          document.getElementById('bm-url').value = '';
          document.getElementById('bm-title').value = '';
          document.getElementById('bm-tags').value = '';
          loadBookmarks();
          loadTags();
        } else {
          setStatus(res.d.error || 'Error', false);
        }
      });
  }

  function deleteBookmark(id) {
    fetch(API + '/' + id, {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadBookmarks(); loadTags(); setStatus('Deleted', true); });
  }

  document.getElementById('bm-add-btn').addEventListener('click', addBookmark);
  document.getElementById('bm-search').addEventListener('input', function () {
    loadBookmarks(this.value.trim());
  });

  loadBookmarks();
  loadTags();
})();
