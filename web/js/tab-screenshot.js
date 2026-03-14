// Diagram: 02-dashboard-login
/* tab-screenshot.js — Tab Screenshot | Task 076 | IIFE pattern | no dangerous eval */
(function () {
  'use strict';

  var API_BASE = '/api/v1/tab-screenshot';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatBytes(n) {
    if (n < 1024) { return n + ' B'; }
    if (n < 1048576) { return (n / 1024).toFixed(1) + ' KB'; }
    return (n / 1048576).toFixed(1) + ' MB';
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleString();
    } catch (_) {
      return escHtml(iso);
    }
  }

  function showMsg(msg) {
    var el = document.getElementById('ts-capture-msg');
    el.textContent = msg;
    el.hidden = false;
  }

  function loadStats() {
    fetch(API_BASE + '/stats')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        document.getElementById('ts-stat-count').textContent = data.count;
        document.getElementById('ts-stat-size').textContent = formatBytes(data.total_size_bytes || 0);
      })
      .catch(function (err) { console.error('stats error', err); });
  }

  function loadGallery() {
    fetch(API_BASE + '/gallery')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var gallery = document.getElementById('ts-gallery');
        var items = data.screenshots || [];
        if (items.length === 0) {
          gallery.innerHTML = '<p class="ts-loading">No screenshots yet.</p>';
          return;
        }
        var html = '';
        items.forEach(function (s) {
          html += '<div class="ts-gallery-item" data-id="' + escHtml(s.screenshot_id) + '">';
          html += '<div class="ts-gallery-item-hash">' + escHtml(s.url_hash.slice(0, 16)) + '…</div>';
          html += '<div class="ts-gallery-item-meta">';
          html += '<strong>' + escHtml(s.format.toUpperCase()) + '</strong> · ' + formatBytes(s.size_bytes || 0);
          html += '</div>';
          html += '<div class="ts-gallery-item-meta">' + formatDate(s.captured_at) + '</div>';
          html += '<button class="ts-btn ts-btn-danger ts-delete-btn" data-id="' + escHtml(s.screenshot_id) + '">Delete</button>';
          html += '</div>';
        });
        gallery.innerHTML = html;
        gallery.querySelectorAll('.ts-delete-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteScreenshot(btn.getAttribute('data-id'));
          });
        });
      })
      .catch(function (err) { console.error('gallery error', err); });
  }

  function deleteScreenshot(id) {
    fetch(API_BASE + '/' + encodeURIComponent(id), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () { loadGallery(); loadStats(); })
      .catch(function (err) { console.error('delete error', err); });
  }

  function captureScreenshot() {
    var url = document.getElementById('ts-url').value.trim();
    var title = document.getElementById('ts-title').value.trim();
    var format = document.getElementById('ts-format').value;
    fetch(API_BASE + '/capture', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, title: title, format: format, size_bytes: 0 }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showMsg('Captured: ' + (data.screenshot_id || ''));
        loadGallery();
        loadStats();
      })
      .catch(function (err) { console.error('capture error', err); });
  }

  document.getElementById('ts-capture-btn').addEventListener('click', captureScreenshot);

  loadStats();
  loadGallery();
}());
