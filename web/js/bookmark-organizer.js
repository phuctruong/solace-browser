/* bookmark-organizer.js — Bookmark Organizer | Task 136 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_BOOKMARKS = '/api/v1/bookmarks/bookmarks';
  var API_SEARCH    = '/api/v1/bookmarks/bookmarks/search';
  var API_STATS     = '/api/v1/bookmarks/stats';
  var API_FOLDERS   = '/api/v1/bookmarks/folders';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('bmk-status');
    if (el) el.textContent = msg;
  }

  function authHeader() {
    return { Authorization: 'Bearer ' + (window._solaceToken || '') };
  }

  function loadFolders() {
    fetch(API_FOLDERS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('bmk-folder');
        if (sel) {
          sel.innerHTML = (data.folders || []).map(function (f) {
            return '<option value="' + escHtml(f) + '">' + escHtml(f) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading folders: ' + err.message); });
  }

  function loadBookmarks() {
    fetch(API_BOOKMARKS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderBookmarks(data.bookmarks || [], document.getElementById('bmk-list'));
      })
      .catch(function (err) { setStatus('Error loading bookmarks: ' + err.message); });
  }

  function renderBookmarks(bookmarks, el) {
    if (!el) return;
    if (bookmarks.length === 0) { el.innerHTML = '<p>No bookmarks yet.</p>'; return; }
    el.innerHTML = bookmarks.slice().reverse().map(function (b) {
      var tagsHtml = (b.tags || []).map(function (t) {
        return '<span class="bmk-tag">' + escHtml(t) + '</span>';
      }).join('');
      return '<div class="bmk-item">' +
        '<div>' +
          '<span class="bmk-folder-badge">' + escHtml(b.folder) + '</span>' +
          escHtml(b.bookmark_id) + ' ' + tagsHtml +
        '</div>' +
        '<button class="bmk-btn bmk-btn-danger" data-id="' + escHtml(b.bookmark_id) + '">Delete</button>' +
        '</div>';
    }).join('');
    el.querySelectorAll('button[data-id]').forEach(function (btn) {
      btn.addEventListener('click', function () { deleteBookmark(btn.getAttribute('data-id')); });
    });
  }

  function loadStats() {
    fetch(API_STATS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('bmk-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="bmk-stat-card"><div class="bmk-stat-value">' + escHtml(String(data.total_bookmarks || 0)) + '</div><div class="bmk-stat-label">Total Bookmarks</div></div>' +
          '<div class="bmk-stat-card"><div class="bmk-stat-value">' + escHtml(String(data.total_tags || 0)) + '</div><div class="bmk-stat-label">Total Tags</div></div>';
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function deleteBookmark(id) {
    fetch(API_BOOKMARKS + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeader(),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadBookmarks(); loadStats(); setStatus('Bookmark deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadFolders();
    loadBookmarks();
    loadStats();

    var form = document.getElementById('bmk-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var tagsRaw = document.getElementById('bmk-tags').value.trim();
        var tags = tagsRaw ? tagsRaw.split(',').map(function (t) { return t.trim(); }).filter(Boolean) : [];
        var payload = {
          url: document.getElementById('bmk-url').value.trim(),
          title: document.getElementById('bmk-title').value.trim(),
          folder: document.getElementById('bmk-folder').value,
          tags: tags,
        };
        fetch(API_BOOKMARKS, {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeader()),
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Bookmark saved: ' + data.bookmark.bookmark_id);
            form.reset();
            loadBookmarks();
            loadStats();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }

    var searchBtn = document.getElementById('bmk-search-btn');
    if (searchBtn) {
      searchBtn.addEventListener('click', function () {
        var q = document.getElementById('bmk-search-q').value.trim();
        var url = API_SEARCH + (q ? '?q=' + encodeURIComponent(q) : '');
        fetch(url, { headers: authHeader() })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            renderBookmarks(data.bookmarks || [], document.getElementById('bmk-list'));
            setStatus('Found ' + (data.total || 0) + ' bookmarks.');
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
