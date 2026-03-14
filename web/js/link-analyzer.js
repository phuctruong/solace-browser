// Diagram: 02-dashboard-login
(function () {
  'use strict';

  var API_RESULTS = '/api/v1/links/results';
  var API_ANALYZE = '/api/v1/links/analyze';
  var API_STATS = '/api/v1/links/stats';
  var API_TYPES = '/api/v1/links/types';
  var TOKEN_KEY = 'solace_session_token';

  var _linkTypes = [];
  var _linkStatuses = [];

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
    var el = document.getElementById('la-status');
    if (el) {
      el.textContent = msg;
      el.style.color = isError ? 'var(--hub-error)' : 'var(--hub-text-muted)';
    }
  }

  function populateSelects() {
    document.querySelectorAll('.la-link-type').forEach(function (sel) {
      if (sel.options.length) return;
      _linkTypes.forEach(function (t) {
        var opt = document.createElement('option');
        opt.value = escHtml(t);
        opt.textContent = t;
        sel.appendChild(opt);
      });
    });
    document.querySelectorAll('.la-link-status').forEach(function (sel) {
      if (sel.options.length) return;
      _linkStatuses.forEach(function (s) {
        var opt = document.createElement('option');
        opt.value = escHtml(s);
        opt.textContent = s;
        sel.appendChild(opt);
      });
    });
  }

  function loadTypes() {
    return fetch(API_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _linkTypes = data.link_types || [];
        _linkStatuses = data.link_statuses || [];
        populateSelects();
      })
      .catch(function (err) { setStatus('Failed to load types: ' + err, true); });
  }

  function loadStats() {
    fetch(API_STATS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('la-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="la-stat-card"><div class="la-stat-label">Analyses</div><div class="la-stat-value">' + escHtml(String(data.total_analyses || 0)) + '</div></div>' +
          '<div class="la-stat-card"><div class="la-stat-label">Total Links</div><div class="la-stat-value">' + escHtml(String(data.total_links || 0)) + '</div></div>' +
          '<div class="la-stat-card"><div class="la-stat-label">Broken</div><div class="la-stat-value la-result-broken">' + escHtml(String(data.broken_links || 0)) + '</div></div>' +
          '<div class="la-stat-card"><div class="la-stat-label">Broken Rate</div><div class="la-stat-value">' + escHtml(String(data.broken_rate || '0')) + '</div></div>';
      })
      .catch(function (err) { setStatus('Failed to load stats: ' + err, true); });
  }

  function loadResults() {
    fetch(API_RESULTS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('la-results');
        if (!el) return;
        var results = data.results || [];
        if (!results.length) {
          el.innerHTML = '<div class="empty-state">No link analyses yet.</div>';
          return;
        }
        el.innerHTML = results.map(function (r) {
          return '<div class="la-result-card">' +
            '<div class="la-result-id">' + escHtml(r.result_id || '') + '</div>' +
            '<div class="la-result-meta">' +
            '<span>Page: <code>' + escHtml((r.page_hash || '').substring(0, 16)) + '…</code></span>' +
            '<span>Links: ' + escHtml(String(r.total_links || 0)) + '</span>' +
            '<span class="la-result-broken">Broken: ' + escHtml(String(r.broken_count || 0)) + '</span>' +
            '<span class="la-result-external">External: ' + escHtml(String(r.external_count || 0)) + '</span>' +
            '<span>' + escHtml(r.analyzed_at || '') + '</span>' +
            '</div></div>';
        }).join('');
      })
      .catch(function (err) { setStatus('Failed to load results: ' + err, true); });
  }

  function addLinkRow() {
    var container = document.getElementById('la-links-input');
    if (!container) return;
    var row = document.createElement('div');
    row.className = 'la-link-row';
    row.innerHTML =
      '<input class="form-input la-url-hash" placeholder="url_hash (64 chars)" maxlength="64">' +
      '<select class="form-input la-link-type"></select>' +
      '<select class="form-input la-link-status"></select>' +
      '<button class="btn-delete la-remove-link">X</button>';
    container.appendChild(row);
    populateSelects();
    row.querySelector('.la-remove-link').addEventListener('click', function () {
      container.removeChild(row);
    });
  }

  function analyze() {
    var pageHash = (document.getElementById('la-page-hash') || {}).value || '';
    if (!pageHash || pageHash.length !== 64) {
      setStatus('page_hash must be 64 hex characters', true);
      return;
    }
    var rows = document.querySelectorAll('#la-links-input .la-link-row');
    var links = [];
    var valid = true;
    rows.forEach(function (row) {
      var urlHash = row.querySelector('.la-url-hash').value || '';
      var linkType = row.querySelector('.la-link-type').value || '';
      var status = row.querySelector('.la-link-status').value || '';
      links.push({ url_hash: urlHash, link_type: linkType, status: status });
    });
    if (!valid) return;
    fetch(API_ANALYZE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + getToken(),
      },
      body: JSON.stringify({ page_hash: pageHash, links: links }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          setStatus('Error: ' + (res.data.error || 'unknown'), true);
          return;
        }
        setStatus('Analysis submitted: ' + (res.data.result || {}).result_id);
        loadResults();
        loadStats();
      })
      .catch(function (err) { setStatus('Request failed: ' + err, true); });
  }

  function clearResults() {
    if (!confirm('Clear all link analysis results?')) return;
    fetch(API_RESULTS, {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + getToken() },
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          setStatus('Error: ' + (res.data.error || 'unknown'), true);
          return;
        }
        setStatus('Results cleared.');
        loadResults();
        loadStats();
      })
      .catch(function (err) { setStatus('Request failed: ' + err, true); });
  }

  function init() {
    loadTypes().then(function () {
      populateSelects();
    });
    loadStats();
    loadResults();

    var btnRefresh = document.getElementById('btn-la-refresh');
    if (btnRefresh) btnRefresh.addEventListener('click', function () { loadResults(); loadStats(); });

    var btnClear = document.getElementById('btn-la-clear');
    if (btnClear) btnClear.addEventListener('click', clearResults);

    var btnAddLink = document.getElementById('btn-la-add-link');
    if (btnAddLink) btnAddLink.addEventListener('click', addLinkRow);

    var btnAnalyze = document.getElementById('btn-la-analyze');
    if (btnAnalyze) btnAnalyze.addEventListener('click', analyze);

    document.querySelectorAll('.la-remove-link').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var row = btn.closest('.la-link-row');
        if (row) row.parentNode.removeChild(row);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
