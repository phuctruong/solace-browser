// Diagram: 02-dashboard-login
/* form-validator.js — Form Validator | Task 096 | IIFE + escHtml */
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showMsg(el, text, isError) {
    el.textContent = text;
    el.style.color = isError ? 'var(--hub-danger)' : 'var(--hub-success)';
    el.hidden = false;
    setTimeout(function () { el.hidden = true; }, 4000);
  }

  function sha256Hex(str) {
    var encoder = new TextEncoder();
    var data = encoder.encode(str);
    return crypto.subtle.digest('SHA-256', data).then(function (buf) {
      return Array.from(new Uint8Array(buf)).map(function (b) {
        return b.toString(16).padStart(2, '0');
      }).join('');
    });
  }

  function loadRules() {
    var list = document.getElementById('fv-list');
    fetch('/api/v1/form-validator/rules', {
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = '';
        (d.rules || []).forEach(function (r) {
          items += '<div class="fv-item"><div>' +
            '<div>' + escHtml(r.rule_id) + '</div>' +
            '<div class="fv-item-meta">Fields: ' + escHtml(String((r.fields || []).length)) +
            ' | ' + escHtml(r.created_at) + '</div>' +
            '</div>' +
            '<button class="fv-btn fv-btn-danger" data-id="' + escHtml(r.rule_id) + '">Delete</button>' +
            '</div>';
        });
        list.innerHTML = items || '<p class="fv-loading">No rule sets yet.</p>';
        list.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteRule(btn.dataset.id); });
        });
      })
      .catch(function () { list.textContent = 'Failed to load rules.'; });
  }

  function deleteRule(ruleId) {
    fetch('/api/v1/form-validator/rules/' + encodeURIComponent(ruleId), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function () { loadRules(); });
  }

  document.getElementById('fv-create-btn').addEventListener('click', function () {
    var name = document.getElementById('fv-name').value.trim() || 'unnamed';
    var form = document.getElementById('fv-form').value.trim() || 'unknown';
    var fieldsRaw = document.getElementById('fv-fields').value.trim();
    var msg = document.getElementById('fv-create-msg');
    var fields = [];
    if (fieldsRaw) {
      try {
        fields = JSON.parse(fieldsRaw);
      } catch (e) {
        showMsg(msg, 'Invalid JSON in fields', true);
        return;
      }
    }
    Promise.all([sha256Hex(name), sha256Hex(form)]).then(function (hashes) {
      return fetch('/api/v1/form-validator/rules', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + (window._solaceToken || ''),
        },
        body: JSON.stringify({ name_hash: hashes[0], form_hash: hashes[1], fields: fields }),
      });
    }).then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status === 'created') {
          showMsg(msg, 'Rule set created: ' + d.rule.rule_id, false);
          loadRules();
        } else {
          showMsg(msg, d.error || 'Error', true);
        }
      })
      .catch(function () { showMsg(msg, 'Network error', true); });
  });

  document.getElementById('fv-validate-btn').addEventListener('click', function () {
    var ruleId = document.getElementById('fv-rule-id').value.trim();
    var submission = document.getElementById('fv-submission').value.trim() || 'empty';
    var msg = document.getElementById('fv-validate-msg');
    var resultEl = document.getElementById('fv-result');
    if (!ruleId) {
      showMsg(msg, 'Rule ID required', true);
      return;
    }
    sha256Hex(submission).then(function (hash) {
      return fetch('/api/v1/form-validator/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + (window._solaceToken || ''),
        },
        body: JSON.stringify({ rule_id: ruleId, submission_hash: hash, field_results: {} }),
      });
    }).then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.error) {
          showMsg(msg, d.error, true);
          resultEl.hidden = true;
        } else {
          resultEl.innerHTML = 'Valid: <strong>' + escHtml(String(d.valid)) + '</strong>' +
            ' | Passed: ' + escHtml(String(d.passed_count)) +
            ' | Failed: ' + escHtml(String(d.failed_count));
          resultEl.hidden = false;
        }
      })
      .catch(function () { showMsg(msg, 'Network error', true); });
  });

  loadRules();
}());
