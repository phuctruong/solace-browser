// Diagram: 02-dashboard-login
/* web-archiver.js — Web Archiver | Task 110 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_ARCHIVES = '/api/v1/web-archiver/archives';
  var API_SEARCH   = '/api/v1/web-archiver/archives/search';
  var API_FORMATS  = '/api/v1/web-archiver/formats';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('wa-status');
    if (el) el.textContent = msg;
  }

  function loadFormats() {
    fetch(API_FORMATS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var formats = data.formats || [];
        var badgesEl = document.getElementById('wa-formats-row');
        var selectEl = document.getElementById('wa-format');
        if (badgesEl) {
          badgesEl.innerHTML = formats.map(function (f) {
            return '<span class="wa-badge">' + escHtml(f) + '</span>';
          }).join('');
        }
        if (selectEl) {
          selectEl.innerHTML = formats.map(function (f) {
            return '<option value="' + escHtml(f) + '">' + escHtml(f.toUpperCase()) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading formats: ' + err.message); });
  }

  function renderArchives(archives) {
    var el = document.getElementById('wa-archives-list');
    if (!el) return;
    if (!archives || archives.length === 0) {
      el.innerHTML = '<p class="wa-empty">No archives found.</p>';
      return;
    }
    el.innerHTML = archives.map(function (a) {
      return '<div class="wa-row">' +
        '<div class="wa-row-meta">' +
        '<span class="wa-format-tag">' + escHtml(a.format) + '</span>' +
        '<span>' + escHtml(a.archive_id) + '</span>' +
        '<span class="wa-hash">url_hash: ' + escHtml((a.url_hash || '').slice(0, 16)) + '&hellip;</span>' +
        '<span>' + escHtml(String(a.size_bytes)) + ' bytes</span>' +
        '</div>' +
        '<button class="wa-btn wa-btn-danger" data-id="' + escHtml(a.archive_id) + '">Delete</button>' +
        '</div>';
    }).join('');

    el.querySelectorAll('[data-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        deleteArchive(btn.getAttribute('data-id'));
      });
    });
  }

  function loadArchives() {
    fetch(API_ARCHIVES)
      .then(function (r) { return r.json(); })
      .then(function (data) { renderArchives(data.archives || []); })
      .catch(function (err) { setStatus('Error loading archives: ' + err.message); });
  }

  function deleteArchive(archiveId) {
    fetch(API_ARCHIVES + '/' + encodeURIComponent(archiveId), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setStatus('Deleted: ' + archiveId);
        loadArchives();
      })
      .catch(function (err) { setStatus('Delete error: ' + err.message); });
  }

  function initArchiveForm() {
    var form = document.getElementById('wa-archive-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var url = document.getElementById('wa-url').value.trim();
      var title = document.getElementById('wa-title').value.trim();
      var format = document.getElementById('wa-format').value;
      var sizeBytes = parseInt(document.getElementById('wa-size').value, 10) || 0;
      fetch(API_ARCHIVES, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, title: title, format: format, size_bytes: sizeBytes, content: '' }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'archived') {
            setStatus('Archived: ' + data.archive.archive_id);
            loadArchives();
          } else {
            setStatus('Error: ' + (data.error || 'unknown'));
          }
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  function initSearchForm() {
    var form = document.getElementById('wa-search-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = document.getElementById('wa-search-q').value.trim();
      fetch(API_SEARCH + '?q=' + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          renderArchives(data.archives || []);
          setStatus('Found ' + (data.total || 0) + ' result(s).');
        })
        .catch(function (err) { setStatus('Search error: ' + err.message); });
    });

    var showAll = document.getElementById('wa-show-all');
    if (showAll) {
      showAll.addEventListener('click', function () { loadArchives(); });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadFormats();
    loadArchives();
    initArchiveForm();
    initSearchForm();
  });
})();
