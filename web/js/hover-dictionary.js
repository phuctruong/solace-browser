// Diagram: 02-dashboard-login
/* hover-dictionary.js — Hover Dictionary | Task 138 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_LOOKUPS   = '/api/v1/hover-dict/lookups';
  var API_STATS     = '/api/v1/hover-dict/stats';
  var API_LANGUAGES = '/api/v1/hover-dict/languages';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('hd-status');
    if (el) el.textContent = msg;
  }

  function authHeaders() {
    return { Authorization: 'Bearer ' + (window._solaceToken || '') };
  }

  function loadLanguages() {
    fetch(API_LANGUAGES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var langs = data.languages || [];
        ['hd-source-lang', 'hd-target-lang'].forEach(function (id) {
          var sel = document.getElementById(id);
          if (sel) {
            sel.innerHTML = langs.map(function (l) {
              return '<option value="' + escHtml(l) + '">' + escHtml(l) + '</option>';
            }).join('');
          }
        });
      })
      .catch(function (err) { setStatus('Error loading languages: ' + err.message); });
  }

  function loadLookups() {
    fetch(API_LOOKUPS, { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('hd-lookups-list');
        if (!el) return;
        var lookups = data.lookups || [];
        if (lookups.length === 0) { el.innerHTML = '<p>No lookups yet.</p>'; return; }
        el.innerHTML = lookups.map(function (lk) {
          return '<div class="hd-item">' +
            '<span>' +
              '<span class="hd-item-meta">' + escHtml(lk.source_language) + ' → ' + escHtml(lk.target_language) + '</span>' +
              ' | hash: ' + escHtml(lk.word_hash.substring(0, 8)) + '…' +
            '</span>' +
            '<button class="hd-btn hd-btn-danger" data-id="' + escHtml(lk.lookup_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteLookup(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading lookups: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS, { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var totalEl = document.getElementById('hd-stat-total');
        var uniqueEl = document.getElementById('hd-stat-unique');
        if (totalEl) totalEl.textContent = data.total_lookups || 0;
        if (uniqueEl) uniqueEl.textContent = data.unique_words || 0;
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function deleteLookup(lookupId) {
    fetch(API_LOOKUPS + '/' + lookupId, { method: 'DELETE', headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function () { setStatus('Lookup deleted.'); loadLookups(); loadStats(); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  function bindForm() {
    var form = document.getElementById('hd-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var word = document.getElementById('hd-word').value.trim();
      var srcLang = document.getElementById('hd-source-lang').value;
      var tgtLang = document.getElementById('hd-target-lang').value;
      var definition = document.getElementById('hd-definition').value.trim();
      var pageUrl = document.getElementById('hd-page-url').value.trim();
      if (!word) { setStatus('Word is required.'); return; }
      fetch(API_LOOKUPS, {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({
          word: word,
          source_language: srcLang,
          target_language: tgtLang,
          definition: definition,
          page_url: pageUrl,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error) { setStatus('Error: ' + escHtml(data.error)); return; }
          setStatus('Lookup recorded.');
          form.reset();
          loadLookups();
          loadStats();
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadLanguages();
    loadLookups();
    loadStats();
    bindForm();
  });
}());
