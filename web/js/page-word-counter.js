/* page-word-counter.js — Page Word Counter | Task 134 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_COUNTS       = '/api/v1/word-counter/counts';
  var API_STATS        = '/api/v1/word-counter/stats';
  var API_CONTENT_TYPES = '/api/v1/word-counter/content-types';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('pwc-status');
    if (el) el.textContent = msg;
  }

  function authHeader() {
    return { Authorization: 'Bearer ' + (window._solaceToken || '') };
  }

  function loadContentTypes() {
    fetch(API_CONTENT_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('pwc-content-type');
        if (sel) {
          sel.innerHTML = (data.content_types || []).map(function (t) {
            return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading content types: ' + err.message); });
  }

  function loadCounts() {
    fetch(API_COUNTS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('pwc-list');
        if (!el) return;
        var counts = data.counts || [];
        if (counts.length === 0) { el.innerHTML = '<p>No counts yet.</p>'; return; }
        el.innerHTML = counts.slice().reverse().map(function (c) {
          return '<div class="pwc-item">' +
            '<div>' +
              escHtml(c.count_id) + ' — ' +
              escHtml(c.content_type) + ' — ' +
              escHtml(String(c.word_count)) + ' words — ' +
              escHtml(c.reading_time_mins) + ' min read' +
            '</div>' +
            '<button class="pwc-btn pwc-btn-danger" data-id="' + escHtml(c.count_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteCount(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading counts: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('pwc-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="pwc-stat-card"><div class="pwc-stat-value">' + escHtml(String(data.total_counts || 0)) + '</div><div class="pwc-stat-label">Total Counts</div></div>' +
          '<div class="pwc-stat-card"><div class="pwc-stat-value">' + escHtml(String(data.total_words || 0)) + '</div><div class="pwc-stat-label">Total Words</div></div>' +
          '<div class="pwc-stat-card"><div class="pwc-stat-value">' + escHtml(String(data.avg_word_count || '0.00')) + '</div><div class="pwc-stat-label">Avg Words</div></div>' +
          '<div class="pwc-stat-card"><div class="pwc-stat-value">' + escHtml(String(data.longest_count || 0)) + '</div><div class="pwc-stat-label">Longest</div></div>';
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function deleteCount(id) {
    fetch(API_COUNTS + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeader(),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadCounts(); loadStats(); setStatus('Count deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadContentTypes();
    loadCounts();
    loadStats();

    var form = document.getElementById('pwc-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var payload = {
          url: document.getElementById('pwc-url').value.trim(),
          content_type: document.getElementById('pwc-content-type').value,
          word_count: parseInt(document.getElementById('pwc-words').value || '0', 10),
          char_count: parseInt(document.getElementById('pwc-chars').value || '0', 10),
          sentence_count: parseInt(document.getElementById('pwc-sentences').value || '0', 10),
          paragraph_count: parseInt(document.getElementById('pwc-paragraphs').value || '0', 10),
        };
        fetch(API_COUNTS, {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeader()),
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Count recorded: ' + data.count.count_id + ' — ' + data.count.reading_time_mins + ' min read');
            form.reset();
            loadCounts();
            loadStats();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
