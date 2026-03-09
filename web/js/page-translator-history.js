/* page-translator-history.js — Page Translator History | Task 140 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_TRANSLATIONS = '/api/v1/page-translator/translations';
  var API_STATS        = '/api/v1/page-translator/stats';
  var API_LANGUAGES    = '/api/v1/page-translator/languages';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('ptr-status');
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
        ['ptr-source-lang', 'ptr-target-lang'].forEach(function (id) {
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

  function loadTranslations() {
    fetch(API_TRANSLATIONS, { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('ptr-list');
        if (!el) return;
        var translations = data.translations || [];
        if (translations.length === 0) { el.innerHTML = '<p>No translations yet.</p>'; return; }
        el.innerHTML = translations.map(function (t) {
          return '<div class="ptr-item">' +
            '<span>' +
              escHtml(t.source_lang) + ' \u2192 ' + escHtml(t.target_lang) +
              ' | words: ' + escHtml(String(t.word_count)) +
              '<span class="ptr-item-meta"> | ' + escHtml(t.translated_at) + '</span>' +
            '</span>' +
            '<button class="ptr-btn ptr-btn-danger" data-id="' + escHtml(t.translation_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteTranslation(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading translations: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS, { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var totalEl = document.getElementById('ptr-stat-total');
        var wordsEl = document.getElementById('ptr-stat-words');
        var topEl   = document.getElementById('ptr-stat-top');
        if (totalEl) totalEl.textContent = data.total_translations || 0;
        if (wordsEl) wordsEl.textContent = data.total_words || 0;
        if (topEl) topEl.textContent = data.most_translated_language || '—';
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function deleteTranslation(translationId) {
    fetch(API_TRANSLATIONS + '/' + translationId, { method: 'DELETE', headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function () { setStatus('Translation deleted.'); loadTranslations(); loadStats(); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  function bindForm() {
    var form = document.getElementById('ptr-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var url = document.getElementById('ptr-url').value.trim();
      var srcLang = document.getElementById('ptr-source-lang').value;
      var tgtLang = document.getElementById('ptr-target-lang').value;
      var wordCount = parseInt(document.getElementById('ptr-word-count').value, 10) || 0;
      var qualityScore = document.getElementById('ptr-quality').value.trim() || undefined;
      fetch(API_TRANSLATIONS, {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({
          url: url,
          source_lang: srcLang,
          target_lang: tgtLang,
          word_count: wordCount,
          quality_score: qualityScore,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error) { setStatus('Error: ' + escHtml(data.error)); return; }
          setStatus('Translation recorded.');
          form.reset();
          loadTranslations();
          loadStats();
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadLanguages();
    loadTranslations();
    loadStats();
    bindForm();
  });
}());
