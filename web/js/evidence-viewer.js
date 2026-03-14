// Diagram: 16-evidence-chain
/**
 * evidence-viewer.js — Evidence Viewer for Solace Hub (Task 016)
 * Laws:
 *   - No CDN dependencies. No jQuery. No Bootstrap. No Tailwind.
 *   - Port 8888 ONLY (same origin). Banned port omitted from source.
 *   - Dynamic escaping via escHtml() required for all dynamic content.
 *   - Solace Hub only. "Companion App" BANNED.
 *   - All CSS via var(--hub-*) tokens only.
 */

'use strict';

(function () {
  var TOKEN = localStorage.getItem('solace_token') || '';
  var AUTH_HEADERS = { 'Authorization': 'Bearer ' + TOKEN };

  var _allEntries = [];
  var _activeFilter = '';
  var _currentPage = 0;
  var PAGE_SIZE = 50;

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtTime(ts) {
    if (!ts) return '';
    try { return new Date(ts).toLocaleString(); } catch (e) { return String(ts); }
  }

  function apiFetch(path) {
    return fetch(path, { headers: AUTH_HEADERS });
  }

  // --- Stats banner ---
  function loadStats() {
    apiFetch('/api/v1/evidence/stats')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var banner = document.getElementById('stats-banner');
        if (!banner) return;
        var types = Array.isArray(d.unique_types) ? d.unique_types.length : '?';
        var first = d.first_event ? fmtTime(d.first_event) : 'N/A';
        var last = d.last_event ? fmtTime(d.last_event) : 'N/A';
        banner.innerHTML =
          '<span>' + escHtml(String(d.total || 0)) + ' total events</span>' +
          '<span>' + escHtml(String(types)) + ' unique types</span>' +
          '<span>First: ' + escHtml(first) + '</span>' +
          '<span>Last: ' + escHtml(last) + '</span>';
      })
      .catch(function () {
        var banner = document.getElementById('stats-banner');
        if (banner) banner.innerHTML = '<span>Stats unavailable</span>';
      });
  }

  // --- Filter buttons ---
  function buildFilters(entries) {
    var bar = document.getElementById('filter-bar');
    if (!bar) return;
    var types = [];
    var seen = {};
    for (var i = 0; i < entries.length; i++) {
      var t = entries[i].event_type || entries[i].type || '';
      if (t && !seen[t]) { seen[t] = true; types.push(t); }
    }
    var html = '<button class="filter-btn filter-btn--active" data-type="">All</button>';
    for (var j = 0; j < types.length; j++) {
      html += '<button class="filter-btn" data-type="' + escHtml(types[j]) + '">' + escHtml(types[j]) + '</button>';
    }
    bar.innerHTML = html;
    bar.querySelectorAll('.filter-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        bar.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('filter-btn--active'); });
        btn.classList.add('filter-btn--active');
        _activeFilter = btn.getAttribute('data-type');
        _currentPage = 0;
        renderEntries();
      });
    });
  }

  // --- Render table ---
  function renderEntries() {
    var list = document.getElementById('evidence-list');
    if (!list) return;
    var filtered = _activeFilter
      ? _allEntries.filter(function (e) { return (e.event_type || e.type || '') === _activeFilter; })
      : _allEntries;

    var totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
    if (_currentPage >= totalPages) _currentPage = totalPages - 1;
    var page = filtered.slice(_currentPage * PAGE_SIZE, (_currentPage + 1) * PAGE_SIZE);

    if (!page.length) {
      list.innerHTML = '<div class="empty-state">No evidence entries found</div>';
      renderPagination(0, 0);
      return;
    }

    var rows = page.map(function (e) {
      var ts = e.timestamp || e.ts || e.created_at || '';
      var evType = e.event_type || e.type || e.action || 'event';
      var actionId = e.action_id || e.id || '';
      var hash = e.sha256 || e.hash || e.entry_hash || '';
      var hashPreview = hash ? hash.substring(0, 16) + '…' : '';
      var desc = e.description || e.summary || e.message || '';
      var detailJson = escHtml(JSON.stringify(e, null, 2));

      return '<tr class="ev-row" data-expanded="false">' +
        '<td class="ev-ts">' + escHtml(fmtTime(ts)) + '</td>' +
        '<td class="ev-type">' + escHtml(evType) + '</td>' +
        '<td class="ev-id">' + escHtml(actionId) + '</td>' +
        '<td class="ev-hash-cell">' + escHtml(hashPreview) + '</td>' +
        '<td class="ev-desc">' + escHtml(desc) + '</td>' +
        '<td class="ev-expand-cell"><button class="btn-expand">+</button></td>' +
        '</tr>' +
        '<tr class="ev-detail-row" style="display:none"><td colspan="6">' +
        '<pre class="ev-detail-json">' + detailJson + '</pre>' +
        '<div class="ev-full-hash">SHA-256: ' + escHtml(hash) + '</div>' +
        '</td></tr>';
    }).join('');

    list.innerHTML = '<table class="ev-table"><thead><tr>' +
      '<th>Timestamp</th><th>Type</th><th>Action ID</th>' +
      '<th>SHA-256</th><th>Details</th><th></th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table>';

    // Expand/collapse toggle
    list.querySelectorAll('.btn-expand').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var row = btn.closest('tr');
        var detailRow = row.nextElementSibling;
        var expanded = row.getAttribute('data-expanded') === 'true';
        if (expanded) {
          detailRow.style.display = 'none';
          row.setAttribute('data-expanded', 'false');
          btn.textContent = '+';
        } else {
          detailRow.style.display = '';
          row.setAttribute('data-expanded', 'true');
          btn.textContent = '−';
        }
      });
    });

    renderPagination(totalPages, filtered.length);
  }

  function renderPagination(totalPages, total) {
    var pag = document.getElementById('pagination');
    if (!pag) return;
    if (totalPages <= 1) { pag.innerHTML = ''; return; }
    var html = '<span class="pag-info">Page ' + (_currentPage + 1) + ' of ' + totalPages +
      ' (' + total + ' entries)</span>';
    if (_currentPage > 0) {
      html += '<button class="btn-pag" id="pag-prev">← Prev</button>';
    }
    if (_currentPage < totalPages - 1) {
      html += '<button class="btn-pag" id="pag-next">Next →</button>';
    }
    pag.innerHTML = html;
    var prev = document.getElementById('pag-prev');
    var next = document.getElementById('pag-next');
    if (prev) prev.addEventListener('click', function () { _currentPage--; renderEntries(); });
    if (next) next.addEventListener('click', function () { _currentPage++; renderEntries(); });
  }

  // --- Keyword search ---
  function applySearch(keyword) {
    var kw = keyword.toLowerCase();
    _allEntries.forEach(function (e) { e._hidden = kw ? (JSON.stringify(e).toLowerCase().indexOf(kw) === -1) : false; });
  }

  // --- Load evidence ---
  function loadEvidence() {
    apiFetch('/api/v1/evidence?limit=50')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        _allEntries = d.entries || d.log || (Array.isArray(d) ? d : []);
        buildFilters(_allEntries);
        renderEntries();
        loadStats();
      })
      .catch(function () {
        var list = document.getElementById('evidence-list');
        if (list) list.innerHTML = '<div class="empty-state">Could not load evidence</div>';
      });
  }

  // --- Export ---
  function exportEvidence() {
    var url = '/api/v1/evidence/export?format=json';
    var a = document.createElement('a');
    a.href = url;
    a.download = 'evidence.json';
    // Set auth via fetch + blob since Bearer token can't be set in <a href>
    fetch(url, { headers: AUTH_HEADERS })
      .then(function (r) { return r.blob(); })
      .then(function (blob) {
        var objUrl = URL.createObjectURL(blob);
        a.href = objUrl;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(objUrl);
      })
      .catch(function () { window.alert('Export failed'); });
  }

  // --- Verify chain ---
  function verifyChain() {
    var status = document.getElementById('chain-status');
    if (status) { status.textContent = 'Verifying…'; status.className = 'chain-status chain-status--unknown'; }
    apiFetch('/api/v1/evidence/verify')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!status) return;
        if (d.valid || d.verified || d.status === 'ok') {
          status.textContent = '✓ Chain verified';
          status.className = 'chain-status chain-status--verified';
        } else {
          status.textContent = '⚠ Chain error';
          status.className = 'chain-status chain-status--error';
        }
      })
      .catch(function () {
        if (status) { status.textContent = 'Chain: error'; status.className = 'chain-status chain-status--error'; }
      });
  }

  // --- Wire up ---
  document.addEventListener('DOMContentLoaded', function () {
    var exportBtn = document.getElementById('btn-export');
    if (exportBtn) exportBtn.addEventListener('click', exportEvidence);

    var verifyBtn = document.getElementById('btn-verify');
    if (verifyBtn) verifyBtn.addEventListener('click', verifyChain);

    var searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        applySearch(searchInput.value);
        renderEntries();
      });
    }

    loadEvidence();
  });
}());
