/* keyboard-macro-manager.js — Keyboard Macro Manager | Task 102 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_MACROS   = '/api/v1/macros';
  var API_TRIGGERS = '/api/v1/macros/triggers';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function loadMacros() {
    fetch(API_MACROS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('kmm-list');
        if (!el) return;
        if (!data.macros || data.macros.length === 0) {
          el.innerHTML = '<p class="kmm-empty">No macros defined.</p>';
          return;
        }
        var html = '';
        data.macros.forEach(function (m) {
          html += '<div class="kmm-row">';
          html += '<span class="kmm-trigger-badge">' + escHtml(m.trigger_type) + '</span>';
          html += '<span>' + escHtml(m.macro_id) + '</span>';
          html += '<span class="kmm-exec-count">Runs: ' + escHtml(String(m.execute_count)) + '</span>';
          html += '</div>';
        });
        el.innerHTML = html;
      });
  }

  function loadTriggers() {
    fetch(API_TRIGGERS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('kmm-triggers');
        if (!el) return;
        var html = '';
        (data.trigger_types || []).forEach(function (t) {
          html += '<span class="kmm-badge">' + escHtml(t) + '</span>';
        });
        el.innerHTML = html;
      });
  }

  function init() {
    loadMacros();
    loadTriggers();
  }

  document.addEventListener('DOMContentLoaded', init);
}());
