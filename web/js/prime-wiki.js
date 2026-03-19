/* prime-wiki.js — extracted from prime-wiki.html */
'use strict';
var TOKEN = localStorage.getItem('solace_token') || '';
var AUTH = { headers: { 'Authorization': 'Bearer ' + TOKEN } };

function _esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function loadStats() {
  fetch('/api/v1/prime-wiki/stats', AUTH)
    .then(function (r) { return r.json(); })
    .then(function (d) {
      document.getElementById('stat-snapshots').textContent = d.total_snapshots || d.snapshot_count || '0';
      document.getElementById('stat-urls').textContent = d.total_urls || d.url_count || '0';
      var ratio = d.avg_compression_ratio || d.avg_ratio || 0;
      document.getElementById('stat-ratio').textContent = ratio ? ratio.toFixed(1) + ':1' : '\u2014';
      var saved = d.total_original_bytes || d.total_bytes || 0;
      document.getElementById('stat-size').textContent = saved ? Math.round(saved / 1024) + ' KB' : '\u2014';
    })
    .catch(function () {});
}

function _render(items) {
  var c = document.getElementById('results-container');
  if (!items || items.length === 0) {
    c.innerHTML = '<div class="empty-state">No snapshots found</div>';
    return;
  }
  c.innerHTML = '<div class="snapshot-list">' + items.map(function (item) {
    var url = item.url || item.source_url || '';
    var domain = 'unknown';
    try { domain = url ? new URL(url).hostname : item.domain || 'unknown'; } catch (e) {}
    var ptype = item.page_type || item.type || 'page';
    var ratio = item.compression_ratio || item.ratio || 0;
    return '<div class="snapshot-item"><div><div class="snapshot-domain">' + _esc(domain) + '</div>' +
      '<div class="snapshot-meta">' + _esc((url || '').substring(0, 60)) + ((url || '').length > 60 ? '\u2026' : '') + '</div></div>' +
      '<div style="text-align:right"><span class="snapshot-badge">' + _esc(ptype) + '</span>' +
      (ratio ? '<div class="snapshot-meta" style="margin-top:4px">' + ratio.toFixed(1) + ':1</div>' : '') + '</div></div>';
  }).join('') + '</div>';
}

function doSearch() {
  var q = document.getElementById('search-input').value.trim();
  fetch('/api/v1/prime-wiki/search?q=' + encodeURIComponent(q || ''), AUTH)
    .then(function (r) { return r.json(); })
    .then(function (d) {
      _render(d.results || d.snapshots || d || []);
    })
    .catch(function () {});
}

/* ---- Event delegation for search ---- */
document.querySelector('[data-action="search"]').addEventListener('click', function () {
  doSearch();
});

document.getElementById('search-input').addEventListener('keydown', function (e) {
  if (e.key === 'Enter') doSearch();
});

loadStats();
doSearch();
