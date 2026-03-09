/* url-categorizer.js — URL Categorizer | Task 079 | IIFE pattern | no dangerous eval */
(function () {
  'use strict';

  var API_BASE = '/api/v1/url-categorizer';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleString();
    } catch (_) {
      return escHtml(iso);
    }
  }

  function showMsg(msg) {
    var el = document.getElementById('uc-categorize-msg');
    el.textContent = msg;
    el.hidden = false;
  }

  function loadSummary() {
    fetch(API_BASE + '/summary')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('uc-summary');
        var by = data.by_category || {};
        var cats = Object.keys(by);
        if (cats.length === 0) {
          container.innerHTML = '<p class="uc-loading">No data yet.</p>';
          return;
        }
        var html = '';
        cats.forEach(function (cat) {
          html += '<div class="uc-summary-card">';
          html += '<span class="uc-summary-cat">' + escHtml(cat.replace(/_/g, ' ')) + '</span>';
          html += '<span class="uc-summary-count">' + escHtml(String(by[cat])) + '</span>';
          html += '</div>';
        });
        container.innerHTML = html;
      })
      .catch(function (err) { console.error('summary error', err); });
  }

  function loadHistory() {
    fetch(API_BASE + '/history')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('uc-history');
        var history = data.history || [];
        if (history.length === 0) {
          container.innerHTML = '<p class="uc-loading">No history.</p>';
          return;
        }
        var html = '';
        history.slice().reverse().forEach(function (e) {
          html += '<div class="uc-history-row">';
          html += '<span class="uc-history-cat">' + escHtml(e.category) + '</span>';
          html += '<span class="uc-history-meta">url: ' + escHtml(e.url_hash.slice(0, 12)) + '…</span>';
          html += '<span class="uc-history-meta">score: ' + escHtml(e.confidence_score) + ' (' + escHtml(e.confidence_level) + ')</span>';
          html += '<span class="uc-history-meta">' + formatDate(e.categorized_at) + '</span>';
          html += '</div>';
        });
        container.innerHTML = html;
      })
      .catch(function (err) { console.error('history error', err); });
  }

  function categorize() {
    fetch(API_BASE + '/categorize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: document.getElementById('uc-url').value.trim(),
        domain: document.getElementById('uc-domain').value.trim(),
        category: document.getElementById('uc-category').value,
        confidence_score: document.getElementById('uc-confidence').value.trim(),
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showMsg('Categorized: ' + (data.entry_id || ''));
        loadSummary();
        loadHistory();
      })
      .catch(function (err) { console.error('categorize error', err); });
  }

  function clearHistory() {
    fetch(API_BASE + '/history', { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () { loadSummary(); loadHistory(); })
      .catch(function (err) { console.error('clear error', err); });
  }

  document.getElementById('uc-categorize-btn').addEventListener('click', categorize);
  document.getElementById('uc-clear-btn').addEventListener('click', clearHistory);

  loadSummary();
  loadHistory();
}());
