// Diagram: 02-dashboard-login
/* notification-filter.js — Notification Filter | Task 104 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_RULES   = '/api/v1/notification-filter/rules';
  var API_LOG     = '/api/v1/notification-filter/log';
  var API_ACTIONS = '/api/v1/notification-filter/actions';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function loadRules() {
    fetch(API_RULES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('nf-rules-list');
        if (!el) return;
        if (!data.rules || data.rules.length === 0) {
          el.innerHTML = '<p class="nf-empty">No filter rules defined.</p>';
          return;
        }
        var html = '';
        data.rules.forEach(function (r) {
          html += '<div class="nf-row">';
          html += '<span class="nf-action-badge nf-action-' + escHtml(r.action) + '">' + escHtml(r.action) + '</span>';
          html += '<span style="color:var(--hub-text-muted);font-size:0.8rem">' + escHtml(r.rule_id) + '</span>';
          html += '</div>';
        });
        el.innerHTML = html;
      });
  }

  function loadLog() {
    fetch(API_LOG)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('nf-log-list');
        if (!el) return;
        if (!data.log || data.log.length === 0) {
          el.innerHTML = '<p class="nf-empty">No notification log entries.</p>';
          return;
        }
        var html = '';
        data.log.forEach(function (entry) {
          var prioClass = 'nf-priority-' + escHtml(entry.priority);
          html += '<div class="nf-row">';
          html += '<span class="nf-action-badge nf-action-' + escHtml(entry.action_taken) + '">' + escHtml(entry.action_taken) + '</span>';
          html += '<span class="' + prioClass + '">' + escHtml(entry.priority) + '</span>';
          html += '<span style="color:var(--hub-text-muted);font-size:0.8rem;margin-left:auto">' + escHtml(entry.logged_at) + '</span>';
          html += '</div>';
        });
        el.innerHTML = html;
      });
  }

  function loadActions() {
    fetch(API_ACTIONS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('nf-actions');
        if (!el) return;
        var html = '';
        (data.actions || []).forEach(function (a) {
          html += '<span class="nf-badge">' + escHtml(a) + '</span>';
        });
        el.innerHTML = html;
      });
  }

  function init() {
    loadRules();
    loadLog();
    loadActions();
  }

  document.addEventListener('DOMContentLoaded', init);
}());
