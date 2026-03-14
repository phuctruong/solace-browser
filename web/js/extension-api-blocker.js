// Diagram: 02-dashboard-login
/* Extension API Blocker — Task 157 — IIFE, no eval() */
(function () {
  'use strict';

  var BASE = '/api/v1/api-blocker';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showMsg(text) {
    var el = document.getElementById('abr-msg');
    if (el) { el.textContent = text; }
  }

  function loadStats() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', BASE + '/stats');
    xhr.onload = function () {
      if (xhr.status !== 200) { return; }
      var d;
      try { d = JSON.parse(xhr.responseText); } catch (e) { return; }
      var el = document.getElementById('abr-stats');
      if (!el) { return; }
      el.innerHTML = '<div class="abr-stats-grid">' +
        '<div class="abr-stat"><div class="abr-stat-val">' + escHtml(d.total_rules) + '</div><div class="abr-stat-lbl">Total Rules</div></div>' +
        '<div class="abr-stat"><div class="abr-stat-val">' + escHtml(d.enabled_rules) + '</div><div class="abr-stat-lbl">Enabled Rules</div></div>' +
        '<div class="abr-stat"><div class="abr-stat-val">' + escHtml(d.total_blocked) + '</div><div class="abr-stat-lbl">Calls Blocked</div></div>' +
        '</div>';
    };
    xhr.send();
  }

  function loadRules() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', BASE + '/rules');
    xhr.onload = function () {
      if (xhr.status !== 200) { return; }
      var d;
      try { d = JSON.parse(xhr.responseText); } catch (e) { return; }
      var el = document.getElementById('abr-rules-panel');
      if (!el) { return; }
      if (!d.rules || d.rules.length === 0) {
        el.innerHTML = '<p>No rules defined yet.</p>';
        return;
      }
      var html = '';
      d.rules.slice().reverse().forEach(function (r) {
        var badgeCls = r.is_enabled ? 'abr-badge-enabled' : 'abr-badge-disabled';
        var badgeTxt = r.is_enabled ? 'Enabled' : 'Disabled';
        html += '<div class="abr-item">' +
          '<div>' +
            '<div class="abr-item-meta">' +
              '<span class="abr-badge ' + badgeCls + '">' + escHtml(badgeTxt) + '</span> ' +
              '<span class="abr-badge">' + escHtml(r.rule_type) + '</span> ' +
              'Hash: <code>' + escHtml(r.pattern_hash.substring(0, 16)) + '...</code>' +
            '</div>' +
            '<div class="abr-item-id">' + escHtml(r.rule_id) + ' — ' + escHtml(r.created_at) + '</div>' +
          '</div>' +
          '<div class="abr-actions">' +
            '<button class="abr-btn abr-btn-del" data-id="' + escHtml(r.rule_id) + '">Delete</button>' +
          '</div>' +
        '</div>';
      });
      el.innerHTML = html;
      el.querySelectorAll('.abr-btn-del').forEach(function (btn) {
        btn.addEventListener('click', function () {
          deleteRule(btn.getAttribute('data-id'));
        });
      });
    };
    xhr.send();
  }

  function loadLog() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', BASE + '/log');
    xhr.onload = function () {
      if (xhr.status !== 200) { return; }
      var d;
      try { d = JSON.parse(xhr.responseText); } catch (e) { return; }
      var el = document.getElementById('abr-log-panel');
      if (!el) { return; }
      if (!d.log || d.log.length === 0) {
        el.innerHTML = '<p>No blocked calls logged yet.</p>';
        return;
      }
      var html = '';
      d.log.slice().reverse().slice(0, 50).forEach(function (entry) {
        html += '<div class="abr-item">' +
          '<div>' +
            '<div class="abr-item-meta">' +
              'API hash: <code>' + escHtml(entry.api_hash.substring(0, 16)) + '...</code> &nbsp;' +
              'Rule: ' + escHtml(entry.rule_id_matched) +
            '</div>' +
            '<div class="abr-item-id">' + escHtml(entry.log_id) + ' — ' + escHtml(entry.blocked_at) + '</div>' +
          '</div>' +
        '</div>';
      });
      el.innerHTML = html;
    };
    xhr.send();
  }

  function deleteRule(id) {
    var xhr = new XMLHttpRequest();
    xhr.open('DELETE', BASE + '/rules/' + id);
    xhr.onload = function () {
      if (xhr.status === 200) {
        showMsg('Rule deleted.');
        loadStats();
        loadRules();
      } else {
        showMsg('Delete failed.');
      }
    };
    xhr.send();
  }

  function init() {
    loadStats();
    loadRules();
    loadLog();

    var ruleForm = document.getElementById('abr-rule-form');
    if (ruleForm) {
      ruleForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var body = JSON.stringify({
          rule_type: document.getElementById('abr-rule-type').value,
          pattern: document.getElementById('abr-pattern').value,
          is_enabled: document.getElementById('abr-enabled').checked
        });
        var xhr = new XMLHttpRequest();
        xhr.open('POST', BASE + '/rules');
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = function () {
          if (xhr.status === 201) {
            showMsg('Rule created.');
            document.getElementById('abr-pattern').value = '';
            loadStats();
            loadRules();
          } else {
            var d;
            try { d = JSON.parse(xhr.responseText); } catch (ex) { d = {}; }
            showMsg('Error: ' + escHtml(d.error || 'unknown'));
          }
        };
        xhr.send(body);
      });
    }

    var logForm = document.getElementById('abr-log-form');
    if (logForm) {
      logForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var body = JSON.stringify({
          api_call: document.getElementById('abr-api-call').value,
          rule_id_matched: document.getElementById('abr-rule-matched').value || 'no_rule'
        });
        var xhr = new XMLHttpRequest();
        xhr.open('POST', BASE + '/log');
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = function () {
          if (xhr.status === 201) {
            showMsg('Blocked call logged.');
            document.getElementById('abr-api-call').value = '';
            loadStats();
            loadLog();
          } else {
            var d;
            try { d = JSON.parse(xhr.responseText); } catch (ex) { d = {}; }
            showMsg('Error: ' + escHtml(d.error || 'unknown'));
          }
        };
        xhr.send(body);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
