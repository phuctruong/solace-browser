// Diagram: 02-dashboard-login
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
  var RULE_TYPES = [];

  function initTypes() {
    fetch('/api/v1/content-blocker/rule-types')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        RULE_TYPES = data.rule_types || [];
        var sel = document.getElementById('cb-type');
        RULE_TYPES.forEach(function (t) {
          var opt = document.createElement('option');
          opt.value = t;
          opt.textContent = t;
          sel.appendChild(opt);
        });
      });
  }

  function loadStats() {
    fetch('/api/v1/content-blocker/stats', {
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (data) {
        var bar = document.getElementById('cb-stats-bar');
        bar.innerHTML = '';
        var fields = [
          { label: 'Total Rules', value: data.total_rules || 0 },
          { label: 'Enabled', value: data.enabled_rules || 0 },
          { label: 'Total Blocks', value: data.total_blocks || 0 },
        ];
        fields.forEach(function (f) {
          var c = document.createElement('div');
          c.className = 'cb-stat-card';
          c.innerHTML = '<div class="cb-stat-value">' + escHtml(String(f.value)) + '</div>' +
            '<div class="cb-stat-label">' + escHtml(f.label) + '</div>';
          bar.appendChild(c);
        });
      });
  }

  function loadRules() {
    fetch('/api/v1/content-blocker/rules', {
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function (r) { return r.ok ? r.json() : { rules: [] }; })
      .then(function (data) {
        var tbody = document.getElementById('cb-tbody');
        tbody.innerHTML = '';
        (data.rules || []).forEach(function (rule) {
          var tr = document.createElement('tr');
          tr.innerHTML = '<td>' + escHtml(rule.rule_type || '') + '</td>' +
            '<td class="cb-hash">' + escHtml((rule.pattern_hash || '').slice(0, 16)) + '…</td>' +
            '<td>' + (rule.enabled ? 'Yes' : 'No') + '</td>' +
            '<td>' + escHtml(String(rule.block_count || 0)) + '</td>' +
            '<td>' + escHtml((rule.created_at || '').slice(0, 10)) + '</td>' +
            '<td><button class="cb-btn cb-btn-danger" data-id="' + escHtml(rule.rule_id) + '">Delete</button></td>';
          tbody.appendChild(tr);
        });
        tbody.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteRule(btn.getAttribute('data-id')); });
        });
      });
  }

  function addRule() {
    var ruleType = document.getElementById('cb-type').value;
    var pattern = document.getElementById('cb-pattern').value.trim();
    var enabled = document.getElementById('cb-enabled').checked;
    if (!pattern) { document.getElementById('cb-status').textContent = 'Pattern required'; return; }
    fetch('/api/v1/content-blocker/rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken },
      body: JSON.stringify({ rule_type: ruleType, pattern: pattern, enabled: enabled }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (res.ok) {
          document.getElementById('cb-status').textContent = 'Rule added';
          document.getElementById('cb-pattern').value = '';
          loadRules();
          loadStats();
        } else {
          document.getElementById('cb-status').textContent = res.d.error || 'Error';
        }
      });
  }

  function deleteRule(id) {
    fetch('/api/v1/content-blocker/rules/' + id, {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + authToken },
    })
      .then(function () { loadRules(); loadStats(); document.getElementById('cb-status').textContent = 'Deleted'; });
  }

  function checkUrl() {
    var url = document.getElementById('cb-check-url').value.trim();
    if (!url) return;
    fetch('/api/v1/content-blocker/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken },
      body: JSON.stringify({ url: url }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('cb-check-result');
        if (data.matched) {
          el.style.color = 'var(--hub-danger)';
          el.textContent = 'BLOCKED by ' + escHtml(data.rule_type || '') + ' rule';
        } else {
          el.style.color = 'var(--hub-success)';
          el.textContent = 'ALLOWED — no matching rule';
        }
      });
  }

  document.getElementById('cb-add-btn').addEventListener('click', addRule);
  document.getElementById('cb-check-btn').addEventListener('click', checkUrl);

  initTypes();
  loadRules();
  loadStats();
})();
