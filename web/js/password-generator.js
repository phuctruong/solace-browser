(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var authToken = '';

  var STRENGTH_COLORS = {
    very_weak: 'var(--hub-strength-very-weak)',
    weak: 'var(--hub-strength-weak)',
    fair: 'var(--hub-strength-fair)',
    strong: 'var(--hub-strength-strong)',
    very_strong: 'var(--hub-strength-very-strong)',
  };

  var STRENGTH_WIDTHS = {
    very_weak: '15%', weak: '35%', fair: '55%', strong: '75%', very_strong: '100%',
  };

  document.getElementById('pg-length').addEventListener('input', function () {
    document.getElementById('pg-len-val').textContent = this.value;
  });

  document.getElementById('pg-generate').addEventListener('click', function () {
    var length = parseInt(document.getElementById('pg-length').value, 10);
    var charsets = [];
    if (document.getElementById('pg-upper').checked) charsets.push('uppercase');
    if (document.getElementById('pg-lower').checked) charsets.push('lowercase');
    if (document.getElementById('pg-numbers').checked) charsets.push('numbers');
    if (document.getElementById('pg-symbols').checked) charsets.push('symbols');
    var excludeSimilar = document.getElementById('pg-exclude-similar').checked;
    fetch('/api/v1/passwords/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken },
      body: JSON.stringify({ length: length, charsets: charsets, exclude_similar: excludeSimilar }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var resultEl = document.getElementById('pg-result');
        resultEl.style.display = 'block';
        var bar = document.getElementById('pg-strength-bar');
        var lvl = data.strength_level || 'very_weak';
        bar.style.width = STRENGTH_WIDTHS[lvl] || '15%';
        bar.style.background = STRENGTH_COLORS[lvl] || 'var(--hub-danger)';
        document.getElementById('pg-strength-label').textContent =
          lvl.replace(/_/g, ' ').toUpperCase() + ' (' + (data.strength_score || 0) + '/100)';
        document.getElementById('pg-hash-display').textContent = data.password_hash || '';
        loadHistory();
      });
  });

  document.getElementById('pg-copy').addEventListener('click', function () {
    var hash = document.getElementById('pg-hash-display').textContent;
    if (navigator.clipboard) navigator.clipboard.writeText(hash);
  });

  document.getElementById('pg-audit-btn').addEventListener('click', function () {
    var pw = document.getElementById('pg-audit-input').value;
    fetch('/api/v1/passwords/audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pw }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('pg-audit-result');
        var lvl = data.strength_level || 'very_weak';
        el.style.color = STRENGTH_COLORS[lvl] || 'var(--hub-danger)';
        el.textContent = lvl.replace(/_/g, ' ').toUpperCase() + ' — score: ' + (data.strength_score || 0);
      });
  });

  function loadHistory() {
    fetch('/api/v1/passwords/history', {
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.ok ? r.json() : { history: [] }; })
      .then(function (data) {
        var ul = document.getElementById('pg-history');
        ul.innerHTML = '';
        (data.history || []).slice(-10).forEach(function (entry) {
          var li = document.createElement('li');
          li.textContent = escHtml((entry.password_hash || '').slice(0, 32)) + '… (' + escHtml(entry.generated_at || '') + ')';
          ul.appendChild(li);
        });
      });
  }

  loadHistory();
})();
