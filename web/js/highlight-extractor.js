// Diagram: 02-dashboard-login
/* highlight-extractor.js — Highlight Extractor | Task 135 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_HIGHLIGHTS = '/api/v1/highlights/highlights';
  var API_BY_PAGE    = '/api/v1/highlights/highlights/by-page';
  var API_STATS      = '/api/v1/highlights/stats';
  var API_COLORS     = '/api/v1/highlights/colors';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('hlt-status');
    if (el) el.textContent = msg;
  }

  function authHeader() {
    return { Authorization: 'Bearer ' + (window._solaceToken || '') };
  }

  function loadColors() {
    fetch(API_COLORS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('hlt-color');
        if (sel) {
          sel.innerHTML = (data.colors || []).map(function (c) {
            return '<option value="' + escHtml(c) + '">' + escHtml(c) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading colors: ' + err.message); });
  }

  function loadHighlights() {
    fetch(API_HIGHLIGHTS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderHighlights(data.highlights || [], document.getElementById('hlt-list'));
      })
      .catch(function (err) { setStatus('Error loading highlights: ' + err.message); });
  }

  function renderHighlights(highlights, el) {
    if (!el) return;
    if (highlights.length === 0) { el.innerHTML = '<p>No highlights yet.</p>'; return; }
    el.innerHTML = highlights.slice().reverse().map(function (h) {
      return '<div class="hlt-item">' +
        '<div>' +
          '<span class="hlt-color-dot" style="background:' + escHtml(h.color) + '"></span>' +
          escHtml(h.highlight_id) + ' — ' + escHtml(h.color) +
        '</div>' +
        '<button class="hlt-btn hlt-btn-danger" data-id="' + escHtml(h.highlight_id) + '">Delete</button>' +
        '</div>';
    }).join('');
    el.querySelectorAll('button[data-id]').forEach(function (btn) {
      btn.addEventListener('click', function () { deleteHighlight(btn.getAttribute('data-id')); });
    });
  }

  function loadStats() {
    fetch(API_STATS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('hlt-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="hlt-stat-card"><div class="hlt-stat-value">' + escHtml(String(data.total_highlights || 0)) + '</div><div class="hlt-stat-label">Total Highlights</div></div>' +
          '<div class="hlt-stat-card"><div class="hlt-stat-value">' + escHtml(String(data.total_pages || 0)) + '</div><div class="hlt-stat-label">Pages</div></div>';
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function deleteHighlight(id) {
    fetch(API_HIGHLIGHTS + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeader(),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadHighlights(); loadStats(); setStatus('Highlight deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadColors();
    loadHighlights();
    loadStats();

    var form = document.getElementById('hlt-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var payload = {
          page_url: document.getElementById('hlt-page-url').value.trim(),
          text: document.getElementById('hlt-text').value.trim(),
          color: document.getElementById('hlt-color').value,
          note: document.getElementById('hlt-note').value.trim(),
          position: document.getElementById('hlt-position').value.trim(),
        };
        fetch(API_HIGHLIGHTS, {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeader()),
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Highlight saved: ' + data.highlight.highlight_id);
            form.reset();
            loadHighlights();
            loadStats();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }

    var filterBtn = document.getElementById('hlt-filter-btn');
    if (filterBtn) {
      filterBtn.addEventListener('click', function () {
        var ph = document.getElementById('hlt-filter-hash').value.trim();
        if (!ph) { loadHighlights(); return; }
        fetch(API_BY_PAGE + '?page_hash=' + encodeURIComponent(ph), { headers: authHeader() })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            renderHighlights(data.highlights || [], document.getElementById('hlt-list'));
            setStatus('Showing ' + (data.total || 0) + ' highlights for page.');
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
