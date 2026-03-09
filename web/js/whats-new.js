/* whats-new.js — What's New Panel | Task 041 | IIFE pattern | no dangerous eval */
(function () {
  'use strict';

  var API_BASE = '/api/v1/whats-new';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function typeBadge(type) {
    return '<span class="wn-type-badge wn-type-' + escHtml(type) + '">' + escHtml(type) + '</span>';
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (_) {
      return escHtml(iso);
    }
  }

  function renderEntries(entries) {
    var container = document.getElementById('wn-entries');
    if (!entries || entries.length === 0) {
      container.innerHTML = '<p class="wn-empty">No entries found.</p>';
      return;
    }
    var html = '';
    entries.forEach(function (entry) {
      var seenClass = entry.seen ? ' wn-entry--seen' : '';
      html += '<article class="wn-entry' + seenClass + '" data-id="' + escHtml(entry.entry_id) + '">';
      html += '<div class="wn-entry-header">';
      html += '<span class="wn-version">v' + escHtml(entry.version) + '</span>';
      html += typeBadge(entry.type);
      html += '<time class="wn-date">' + formatDate(entry.released_at) + '</time>';
      html += '</div>';
      html += '<h2 class="wn-entry-title">' + escHtml(entry.title) + '</h2>';
      html += '<p class="wn-entry-desc">' + escHtml(entry.description) + '</p>';
      if (!entry.seen) {
        html += '<button class="wn-seen-btn" data-id="' + escHtml(entry.entry_id) + '">Mark as seen</button>';
      }
      html += '</article>';
    });
    container.innerHTML = html;

    container.querySelectorAll('.wn-seen-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        markSeen(btn.getAttribute('data-id'));
      });
    });
  }

  function markSeen(entryId) {
    fetch(API_BASE + '/' + encodeURIComponent(entryId) + '/seen', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadEntries(); loadUnseenCount(); })
      .catch(function (err) { console.error('mark-seen error', err); });
  }

  function loadEntries() {
    var filterType = document.getElementById('wn-filter-type').value;
    fetch(API_BASE)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var entries = data.entries || [];
        if (filterType) {
          entries = entries.filter(function (e) { return e.type === filterType; });
        }
        renderEntries(entries);
      })
      .catch(function (err) {
        document.getElementById('wn-entries').innerHTML = '<p class="wn-error">Failed to load entries.</p>';
        console.error('load-entries error', err);
      });
  }

  function loadUnseenCount() {
    fetch(API_BASE + '/unseen-count')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var badge = document.getElementById('wn-unseen-badge');
        var count = data.unseen_count || 0;
        badge.textContent = String(count);
        badge.hidden = count === 0;
      })
      .catch(function (err) { console.error('unseen-count error', err); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadEntries();
    loadUnseenCount();
    document.getElementById('wn-filter-type').addEventListener('change', loadEntries);
  });
}());
