(function () {
  'use strict';

  var API_CHECK = '/api/v1/spellcheck/check';
  var API_DICT = '/api/v1/spellcheck/dictionary';
  var API_LANGS = '/api/v1/spellcheck/languages';
  var TOKEN_KEY = 'solace_session_token';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function setStatus(msg, isError) {
    var el = document.getElementById('sc-status');
    if (el) {
      el.textContent = msg;
      el.style.color = isError ? 'var(--hub-error)' : 'var(--hub-text-muted)';
    }
  }

  function loadLanguages() {
    fetch(API_LANGS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('sc-language');
        if (!sel) return;
        var langs = data.languages || [];
        sel.innerHTML = '';
        langs.forEach(function (lang) {
          var opt = document.createElement('option');
          opt.value = escHtml(lang);
          opt.textContent = lang;
          sel.appendChild(opt);
        });
      })
      .catch(function (err) { setStatus('Failed to load languages: ' + err, true); });
  }

  function renderErrors(errors, wordCount) {
    var container = document.getElementById('sc-errors');
    if (!container) return;
    var counter = document.getElementById('sc-counter');
    if (counter) {
      counter.textContent = wordCount + ' words, ' + errors.length + ' errors';
    }
    if (!errors.length) {
      container.innerHTML = '<div class="empty-state">No spelling errors found.</div>';
      return;
    }
    container.innerHTML = errors.map(function (e) {
      return '<div class="sc-error-row">' +
        '<span class="sc-error-hash">' + escHtml(e.word_hash || '') + '</span>' +
        '<span class="sc-error-suggestion">→ ' + escHtml(e.suggestion || '') + '</span>' +
        '<span class="sc-error-position">pos ' + escHtml(String(e.position)) + '</span>' +
        '</div>';
    }).join('');
  }

  function checkSpelling() {
    var text = (document.getElementById('sc-text') || {}).value || '';
    var language = (document.getElementById('sc-language') || {}).value || 'en-US';
    fetch(API_CHECK, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, language: language }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          setStatus('Error: ' + (res.data.error || 'unknown'), true);
          return;
        }
        renderErrors(res.data.errors || [], res.data.word_count || 0);
        setStatus('Check complete.');
      })
      .catch(function (err) { setStatus('Request failed: ' + err, true); });
  }

  function renderDict(entries) {
    var container = document.getElementById('sc-dict-list');
    if (!container) return;
    if (!entries.length) {
      container.innerHTML = '<div class="empty-state">No custom words added.</div>';
      return;
    }
    container.innerHTML = entries.map(function (e) {
      return '<div class="sc-dict-row">' +
        '<span class="sc-dict-hash">' + escHtml(e.word_hash || '') + '</span>' +
        '<span class="sc-dict-label">' + escHtml(e.label || '') + '</span>' +
        '<button class="btn-delete" data-hash="' + escHtml(e.word_hash || '') + '">Remove</button>' +
        '</div>';
    }).join('');
    container.querySelectorAll('.btn-delete').forEach(function (btn) {
      btn.addEventListener('click', function () { deleteWord(btn.getAttribute('data-hash')); });
    });
  }

  function loadDict() {
    fetch(API_DICT)
      .then(function (r) { return r.json(); })
      .then(function (data) { renderDict(data.entries || []); })
      .catch(function (err) { setStatus('Failed to load dictionary: ' + err, true); });
  }

  function addWord() {
    var hash = (document.getElementById('sc-word-hash') || {}).value || '';
    var label = (document.getElementById('sc-word-label') || {}).value || '';
    if (!hash || hash.length !== 64) {
      setStatus('word_hash must be 64 hex characters', true);
      return;
    }
    fetch(API_DICT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + getToken(),
      },
      body: JSON.stringify({ word_hash: hash, label: label }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          setStatus('Error: ' + (res.data.error || 'unknown'), true);
          return;
        }
        setStatus('Word added to dictionary.');
        document.getElementById('sc-word-hash').value = '';
        document.getElementById('sc-word-label').value = '';
        loadDict();
      })
      .catch(function (err) { setStatus('Request failed: ' + err, true); });
  }

  function deleteWord(wordHash) {
    fetch(API_DICT + '/' + encodeURIComponent(wordHash), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + getToken() },
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          setStatus('Error: ' + (res.data.error || 'unknown'), true);
          return;
        }
        setStatus('Word removed.');
        loadDict();
      })
      .catch(function (err) { setStatus('Request failed: ' + err, true); });
  }

  function init() {
    loadLanguages();
    loadDict();

    var btnCheck = document.getElementById('btn-sc-check');
    if (btnCheck) btnCheck.addEventListener('click', checkSpelling);

    var btnRefresh = document.getElementById('btn-sc-refresh');
    if (btnRefresh) btnRefresh.addEventListener('click', function () { loadDict(); loadLanguages(); });

    var btnAdd = document.getElementById('btn-sc-add-word');
    if (btnAdd) btnAdd.addEventListener('click', addWord);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
