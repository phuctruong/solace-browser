/* network-request-blocker.js — Network Request Blocker | Task 131 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_RULES      = '/api/v1/request-blocker/rules';
  var API_LOG        = '/api/v1/request-blocker/blocked-log';
  var API_RULE_TYPES = '/api/v1/request-blocker/rule-types';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('nrb-status');
    if (el) el.textContent = msg;
  }

  function loadRuleTypes() {
    fetch(API_RULE_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var ruleTypes = data.rule_types || [];
        var resourceTypes = data.resource_types || [];
        var rtSel = document.getElementById('nrb-rule-type');
        if (rtSel) {
          rtSel.innerHTML = ruleTypes.map(function (t) {
            return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
          }).join('');
        }
        var resSel = document.getElementById('nrb-resource-type');
        if (resSel) {
          resSel.innerHTML = resourceTypes.map(function (t) {
            return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading rule types: ' + err.message); });
  }

  function loadRules() {
    fetch(API_RULES, { headers: { Authorization: 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('nrb-rules-list');
        if (!el) return;
        var rules = data.rules || [];
        if (rules.length === 0) { el.innerHTML = '<p>No rules yet.</p>'; return; }
        el.innerHTML = rules.map(function (r) {
          return '<div class="nrb-item">' +
            '<span>' + escHtml(r.rule_type) + ' / ' + escHtml(r.resource_type) + ' — hits: ' + escHtml(String(r.hit_count)) + '</span>' +
            '<button class="nrb-btn nrb-btn-danger" data-id="' + escHtml(r.rule_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteRule(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading rules: ' + err.message); });
  }

  function loadLog() {
    fetch(API_LOG, { headers: { Authorization: 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('nrb-log-list');
        if (!el) return;
        var log = data.blocked_log || [];
        if (log.length === 0) { el.innerHTML = '<p>No blocked requests yet.</p>'; return; }
        el.innerHTML = log.slice(-20).reverse().map(function (e) {
          return '<div class="nrb-item"><span>Rule: ' + escHtml(e.rule_id) + ' — ' + escHtml(e.blocked_at) + '</span></div>';
        }).join('');
      })
      .catch(function (err) { setStatus('Error loading log: ' + err.message); });
  }

  function deleteRule(id) {
    fetch(API_RULES + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { Authorization: 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadRules(); setStatus('Rule deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadRuleTypes();
    loadRules();
    loadLog();

    var form = document.getElementById('nrb-rule-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var payload = {
          pattern: document.getElementById('nrb-pattern').value.trim(),
          rule_type: document.getElementById('nrb-rule-type').value,
          resource_type: document.getElementById('nrb-resource-type').value,
        };
        fetch(API_RULES, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (window._solaceToken || '') },
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Rule created: ' + data.rule.rule_id);
            form.reset();
            loadRules();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
