/* evidence-viewer-page.js — extracted from evidence-viewer.html (the standalone page) */
'use strict';
var TOKEN = localStorage.getItem('solace_token') || '';
var AUTH = { headers: { 'Authorization': 'Bearer ' + TOKEN } };

function _esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function _fmt(ts) {
  if (!ts) return '';
  try { return new Date(ts).toLocaleString(); } catch (e) { return ts; }
}

var _activeFilter = '';
var _allEntries = [];

function verifyChain() {
  var b = document.getElementById('chain-status');
  b.textContent = 'Verifying...';
  b.className = 'chain-status chain-status--unknown';
  fetch('/api/v1/evidence/verify', AUTH)
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.valid || d.verified || d.status === 'ok') {
        b.textContent = '\u2713 Chain verified';
        b.className = 'chain-status chain-status--verified';
      } else {
        b.textContent = '\u26A0 Chain error';
        b.className = 'chain-status chain-status--error';
      }
    })
    .catch(function () {
      b.textContent = 'Chain: error';
      b.className = 'chain-status chain-status--error';
    });
}

function setFilter(btn, type) {
  document.querySelectorAll('.filter-btn').forEach(function (b) {
    b.classList.remove('filter-btn--active');
  });
  btn.classList.add('filter-btn--active');
  _activeFilter = type;
  renderEntries();
}

function renderEntries() {
  var filtered = _activeFilter
    ? _allEntries.filter(function (e) { return (e.action_type || e.event_type || '') === _activeFilter; })
    : _allEntries;
  var list = document.getElementById('evidence-list');
  if (!filtered.length) {
    list.innerHTML = '<div class="empty-state">No evidence entries found</div>';
    return;
  }
  list.innerHTML = '<div class="evidence-timeline">' + filtered.map(function (e) {
    var hash = (e.sha256 || e.hash || e.entry_hash || '').substring(0, 16);
    return '<div class="evidence-item">' +
      '<div class="ev-time">' + _esc(_fmt(e.ts || e.timestamp || e.created_at)) + '</div>' +
      '<div class="ev-body"><div class="ev-action">' + _esc(e.action_type || e.event_type || 'event') + '</div>' +
      '<div class="ev-desc">' + _esc(e.description || e.summary || e.message || '') + '</div>' +
      (hash ? '<div class="ev-hash">' + _esc(hash) + '\u2026</div>' : '') + '</div></div>';
  }).join('') + '</div>';
}

function buildFilters(entries) {
  var types = [];
  var seen = {};
  entries.forEach(function (e) {
    var t = e.action_type || e.event_type || '';
    if (t && !seen[t]) {
      seen[t] = true;
      types.push(t);
    }
  });
  var bar = document.getElementById('filter-bar');
  bar.innerHTML = '<button class="filter-btn filter-btn--active" data-action="filter" data-filter-type="">All</button>' +
    types.map(function (t) {
      return '<button class="filter-btn" data-action="filter" data-filter-type="' + _esc(t) + '">' + _esc(t) + '</button>';
    }).join('');
}

function loadEvidence() {
  fetch('/api/v1/evidence/log?limit=50', AUTH)
    .then(function (r) { return r.json(); })
    .then(function (d) {
      _allEntries = d.entries || d.log || d || [];
      buildFilters(_allEntries);
      renderEntries();
    })
    .catch(function () {
      document.getElementById('evidence-list').innerHTML = '<div class="empty-state">Could not load evidence</div>';
    });
}

/* ---- Event delegation for filter buttons and verify button ---- */
document.getElementById('filter-bar').addEventListener('click', function (e) {
  var target = e.target;
  if (!(target instanceof HTMLElement)) return;
  if (target.getAttribute('data-action') === 'filter') {
    setFilter(target, target.getAttribute('data-filter-type') || '');
  }
});

document.querySelector('[data-action="verify-chain"]').addEventListener('click', function () {
  verifyChain();
});

loadEvidence();
