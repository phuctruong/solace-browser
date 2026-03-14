// Diagram: 02-dashboard-login
/* Accessibility Checker — Task 159. IIFE. No eval(). escHtml required. */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function msg(text) {
    var el = document.getElementById('a11c-msg');
    if (el) el.textContent = text;
  }

  function loadStats() {
    fetch('/api/v1/accessibility/stats', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('a11c-stats');
        if (!el) return;
        el.innerHTML = '<div class="a11c-stats-grid">' +
          '<div class="a11c-stat"><div class="a11c-stat-val">' + escHtml(d.total_checks) + '</div><div class="a11c-stat-lbl">Total Checks</div></div>' +
          '<div class="a11c-stat"><div class="a11c-stat-val">' + escHtml(d.avg_score) + '</div><div class="a11c-stat-lbl">Avg Score</div></div>' +
          '<div class="a11c-stat"><div class="a11c-stat-val">' + escHtml(d.avg_issues) + '</div><div class="a11c-stat-lbl">Avg Issues</div></div>' +
          '<div class="a11c-stat"><div class="a11c-stat-val">' + escHtml(d.perfect_score_count) + '</div><div class="a11c-stat-lbl">Perfect Scores</div></div>' +
          '</div>';
      })
      .catch(function (e) { msg('Stats error: ' + e.message); });
  }

  function loadChecks() {
    fetch('/api/v1/accessibility/checks', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var panel = document.getElementById('a11c-panel');
        if (!panel) return;
        if (!d.checks || d.checks.length === 0) { panel.innerHTML = '<p>No checks recorded.</p>'; return; }
        panel.innerHTML = d.checks.map(function (c) {
          var scoreClass = c.score >= 80 ? 'a11c-score-high' : 'a11c-score-low';
          return '<div class="a11c-item">' +
            '<div><div class="a11c-item-meta"><span class="a11c-badge">' + escHtml(c.wcag_level) + '</span> ' +
            'Score: <span class="' + scoreClass + '">' + escHtml(c.score) + '</span> | Issues: ' + escHtml(c.total_issues) + '</div>' +
            '<div class="a11c-item-id">' + escHtml(c.check_id) + '</div></div>' +
            '<div class="a11c-actions"><button class="a11c-btn a11c-btn-del" data-id="' + escHtml(c.check_id) + '">Delete</button></div>' +
            '</div>';
        }).join('');
        panel.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteCheck(btn.dataset.id); });
        });
      })
      .catch(function (e) { msg('Load error: ' + e.message); });
  }

  function deleteCheck(id) {
    fetch('/api/v1/accessibility/checks/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadChecks(); loadStats(); })
      .catch(function (e) { msg('Delete error: ' + e.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadStats();
    loadChecks();

    var form = document.getElementById('a11c-form');
    if (form) {
      form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        var issueType = document.getElementById('a11c-issue-type').value;
        var payload = {
          url: document.getElementById('a11c-url').value,
          wcag_level: document.getElementById('a11c-wcag').value,
          total_issues: parseInt(document.getElementById('a11c-total').value, 10),
          critical_issues: parseInt(document.getElementById('a11c-critical').value, 10),
          score: parseInt(document.getElementById('a11c-score').value, 10),
          top_issue_type: issueType || null,
        };
        fetch('/api/v1/accessibility/checks', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + (window._solaceToken || '')
          },
          body: JSON.stringify(payload)
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.check) { msg('Recorded: ' + d.check.check_id); loadChecks(); loadStats(); }
            else { msg('Error: ' + (d.error || 'unknown')); }
          })
          .catch(function (e) { msg('Submit error: ' + e.message); });
      });
    }
  });
}());
