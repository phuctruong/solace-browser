/* password-strength-checker.js — Task 118 | IIFE + escHtml | no eval() | no CDN */
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg, isErr) {
    var el = document.getElementById('psc-status');
    if (!el) return;
    el.textContent = msg;
    el.className = 'psc-status ' + (isErr ? 'err' : 'ok');
  }

  function loadLevels() {
    fetch('/api/v1/password-checker/strength-levels')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('psc-levels-row');
        if (!el) return;
        el.innerHTML = (data.strength_levels || []).map(function (lvl) {
          return '<span class="psc-badge">' + escHtml(lvl) + '</span>';
        }).join('');
      });
  }

  function loadStats() {
    fetch('/api/v1/password-checker/stats', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('psc-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="psc-stat-card"><div class="psc-stat-label">Total Checks</div><div class="psc-stat-value">' + escHtml(String(data.total_checks || 0)) + '</div></div>' +
          '<div class="psc-stat-card"><div class="psc-stat-label">Avg Score</div><div class="psc-stat-value">' + escHtml(String(data.avg_score || '0.00')) + '</div></div>';
      });
  }

  function authHeaders() {
    var token = window.__SOLACE_TOKEN__ || '';
    return token ? { 'Authorization': 'Bearer ' + token } : {};
  }

  function loadChecks() {
    fetch('/api/v1/password-checker/checks', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('psc-checks-list');
        if (!el) return;
        if (!data.checks || data.checks.length === 0) {
          el.innerHTML = '<p class="psc-item-meta">No checks yet.</p>';
          return;
        }
        el.innerHTML = data.checks.map(function (c) {
          return '<div class="psc-item">' +
            '<div>' +
              '<div>' + escHtml(c.check_id) + '</div>' +
              '<div class="psc-item-meta">Strength: ' + escHtml(c.strength_level) + ' | Score: ' + escHtml(String(c.score)) + ' | ' + escHtml(c.checked_at) + '</div>' +
            '</div>' +
            '<button class="psc-btn psc-btn-danger" data-id="' + escHtml(c.check_id) + '">Delete</button>' +
          '</div>';
        }).join('');
      });
  }

  function init() {
    loadLevels();
    loadStats();
    loadChecks();

    var form = document.getElementById('psc-check-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var password = document.getElementById('psc-password').value;
        var score = parseInt(document.getElementById('psc-score').value, 10);
        var hasUppercase = document.getElementById('psc-uppercase').checked;
        var hasNumbers = document.getElementById('psc-numbers').checked;
        var hasSymbols = document.getElementById('psc-symbols').checked;
        fetch('/api/v1/password-checker/checks', {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
          body: JSON.stringify({
            password: password,
            score: score,
            length: password.length,
            has_uppercase: hasUppercase,
            has_numbers: hasNumbers,
            has_symbols: hasSymbols,
          }),
        })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
            if (res.ok) {
              setStatus('Check recorded: ' + res.data.check.strength_level, false);
              loadStats();
              loadChecks();
              form.reset();
            } else {
              setStatus('Error: ' + (res.data.error || 'unknown'), true);
            }
          });
      });
    }

    var list = document.getElementById('psc-checks-list');
    if (list) {
      list.addEventListener('click', function (e) {
        var btn = e.target.closest('button[data-id]');
        if (!btn) return;
        var id = btn.getAttribute('data-id');
        fetch('/api/v1/password-checker/checks/' + encodeURIComponent(id), {
          method: 'DELETE',
          headers: authHeaders(),
        })
          .then(function (r) { return r.json(); })
          .then(function () { loadStats(); loadChecks(); });
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
