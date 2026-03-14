// Diagram: 16-evidence-chain
/**
 * evidence-chain.js — Evidence Chain Viewer for Solace Hub (Task 026)
 * Laws:
 *   - No CDN dependencies. No jQuery. No Bootstrap. No Tailwind.
 *   - Port 8888 ONLY (same origin). Banned port omitted from source.
 *   - Dynamic escaping via escHtml() required for all dynamic content.
 *   - Solace Hub only. "Companion App" BANNED.
 *   - All CSS via var(--hub-*) tokens only.
 *   - IIFE pattern.
 */

'use strict';

(function () {
  var TOKEN = localStorage.getItem('solace_token') || '';
  var AUTH_HEADERS = { 'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json' };

  var _allEntries = [];
  var _searchQuery = '';

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
    try {
      var d = (typeof ts === 'number' && ts < 1e12) ? new Date(ts * 1000) : new Date(ts);
      return d.toLocaleString();
    } catch (e) { return String(ts); }
  }

  function apiFetch(path, opts) {
    return fetch(path, opts || { headers: AUTH_HEADERS });
  }

  function apiFetchAuth(path, method, body) {
    var opts = { method: method || 'GET', headers: AUTH_HEADERS };
    if (body !== undefined) opts.body = JSON.stringify(body);
    return apiFetch(path, opts);
  }

  // --- Stats ---
  function loadStats() {
    apiFetch('/api/v1/evidence/stats')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var total = document.getElementById('stat-total');
        var types = document.getElementById('stat-types');
        var first = document.getElementById('stat-first');
        var last = document.getElementById('stat-last');
        if (total) total.textContent = (d.total || 0) + ' entries';
        if (types) types.textContent = (d.unique_types ? d.unique_types.length : 0) + ' types';
        if (first) first.textContent = 'First: ' + (d.first_event ? fmtTime(d.first_event) : 'N/A');
        if (last) last.textContent = 'Last: ' + (d.last_event ? fmtTime(d.last_event) : 'N/A');
      })
      .catch(function () {});
  }

  // --- Integrity verify ---
  function verifyChain() {
    var badge = document.getElementById('chain-integrity');
    if (badge) { badge.textContent = 'Verifying...'; badge.className = 'integrity-badge integrity-badge--unknown'; }
    apiFetch('/api/v1/evidence/verify')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!badge) return;
        if (d.valid || d.verified || d.status === 'ok') {
          badge.textContent = 'Chain OK';
          badge.className = 'integrity-badge integrity-badge--ok';
        } else {
          badge.textContent = 'Chain Error';
          badge.className = 'integrity-badge integrity-badge--error';
        }
      })
      .catch(function () {
        var badge2 = document.getElementById('chain-integrity');
        if (badge2) { badge2.textContent = 'Verify failed'; badge2.className = 'integrity-badge integrity-badge--error'; }
      });
  }

  // --- Render entries ---
  function renderEntries() {
    var list = document.getElementById('chain-list');
    if (!list) return;
    var q = _searchQuery.toLowerCase();
    var filtered = _allEntries.filter(function (e) {
      if (!q) return true;
      var type = String(e.event_type || e.action_type || e.type || '').toLowerCase();
      var desc = String(e.description || e.summary || e.message || '').toLowerCase();
      return type.indexOf(q) !== -1 || desc.indexOf(q) !== -1;
    });
    if (!filtered.length) {
      list.innerHTML = '<div class="empty-state">No evidence entries found.</div>';
      return;
    }
    list.innerHTML = filtered.map(function (e) {
      var hash = (e.sha256 || e.hash || e.entry_hash || '').substring(0, 16);
      var type = e.event_type || e.action_type || e.type || 'event';
      var desc = e.description || e.summary || e.message || '';
      var ts = e.ts || e.timestamp || e.created_at || '';
      var fullJson = JSON.stringify(e, null, 2);
      return (
        '<div class="chain-entry" data-id="' + escHtml(e.id || '') + '">' +
          '<div class="entry-dot"></div>' +
          '<div class="entry-body">' +
            '<div class="entry-type">' + escHtml(type) + '</div>' +
            '<div class="entry-desc">' + escHtml(desc) + '</div>' +
            '<div class="entry-meta">' +
              '<span>' + escHtml(fmtTime(ts)) + '</span>' +
              (hash ? '<span class="entry-hash">' + escHtml(hash) + '...</span>' : '') +
            '</div>' +
            '<div class="entry-expanded">' + escHtml(fullJson) + '</div>' +
          '</div>' +
        '</div>'
      );
    }).join('');

    list.querySelectorAll('.chain-entry').forEach(function (card) {
      card.addEventListener('click', function () {
        card.classList.toggle('expanded');
      });
    });
  }

  // --- Load entries ---
  function loadEntries() {
    var list = document.getElementById('chain-list');
    if (list) list.innerHTML = '<div class="empty-state">Loading evidence chain...</div>';
    apiFetch('/api/v1/evidence/log?limit=100')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        _allEntries = d.entries || d.records || d.log || (Array.isArray(d) ? d : []);
        renderEntries();
        loadStats();
      })
      .catch(function () {
        if (list) list.innerHTML = '<div class="empty-state">Could not load evidence chain.</div>';
      });
  }

  // --- Add entry modal ---
  function openModal() {
    var modal = document.getElementById('modal-add');
    var inp = document.getElementById('input-ev-type');
    var err = document.getElementById('modal-ev-error');
    if (modal) modal.style.display = 'flex';
    if (inp) { inp.value = ''; inp.focus(); }
    if (err) { err.style.display = 'none'; err.textContent = ''; }
    var desc = document.getElementById('input-ev-desc');
    if (desc) desc.value = '';
  }

  function closeModal() {
    var modal = document.getElementById('modal-add');
    if (modal) modal.style.display = 'none';
  }

  function confirmAdd() {
    var typeInp = document.getElementById('input-ev-type');
    var descInp = document.getElementById('input-ev-desc');
    var err = document.getElementById('modal-ev-error');
    var type = (typeInp ? typeInp.value : '').trim();
    var desc = (descInp ? descInp.value : '').trim();

    if (!type) {
      if (err) { err.textContent = 'Event type is required.'; err.style.display = ''; }
      return;
    }
    apiFetchAuth('/api/v1/evidence/chain', 'POST', { type: type, description: desc, data: { source: 'browser-ui' } })
      .then(function (r) {
        if (r.status === 400) return r.json().then(function (d) { throw new Error(d.error || 'Bad request'); });
        if (!r.ok) throw new Error('Record failed (' + r.status + ')');
        return r.json();
      })
      .then(function () { closeModal(); loadEntries(); })
      .catch(function (e) {
        if (err) { err.textContent = e.message; err.style.display = ''; }
      });
  }

  // --- Search ---
  var searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      _searchQuery = searchInput.value;
      renderEntries();
    });
  }

  // --- Bind buttons ---
  var btnVerify = document.getElementById('btn-verify');
  var btnAdd = document.getElementById('btn-add');
  var btnCancel = document.getElementById('btn-cancel-add');
  var btnConfirm = document.getElementById('btn-confirm-add');
  var overlay = document.getElementById('modal-add');

  if (btnVerify) btnVerify.addEventListener('click', verifyChain);
  if (btnAdd) btnAdd.addEventListener('click', openModal);
  if (btnCancel) btnCancel.addEventListener('click', closeModal);
  if (btnConfirm) btnConfirm.addEventListener('click', confirmAdd);
  if (overlay) {
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeModal();
    });
  }

  loadEntries();
})();
