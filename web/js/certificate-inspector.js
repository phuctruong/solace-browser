// Diagram: 02-dashboard-login
/* certificate-inspector.js — Certificate Inspector | Task 078 | IIFE pattern | no dangerous eval */
(function () {
  'use strict';

  var API_BASE = '/api/v1/certificates';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function gradeClass(grade) {
    if (grade === 'A+' || grade === 'A') { return 'ci-grade-good'; }
    if (grade === 'B') { return 'ci-grade-warn'; }
    return 'ci-grade-bad';
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleString();
    } catch (_) {
      return escHtml(iso);
    }
  }

  function showMsg(msg) {
    var el = document.getElementById('ci-record-msg');
    el.textContent = msg;
    el.hidden = false;
  }

  function loadAlerts() {
    fetch(API_BASE + '/alerts')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('ci-alerts');
        var alerts = data.alerts || [];
        if (alerts.length === 0) {
          container.innerHTML = '<p class="ci-loading">No alerts.</p>';
          return;
        }
        var html = '';
        alerts.forEach(function (c) {
          html += '<div class="ci-alert-row">';
          html += '<strong>' + escHtml(c.alert_type) + '</strong>';
          html += ' — grade: <span class="ci-grade ' + gradeClass(c.grade) + '">' + escHtml(c.grade) + '</span>';
          html += ' — days: ' + escHtml(String(c.validity_days_remaining));
          html += '</div>';
        });
        container.innerHTML = html;
      })
      .catch(function (err) { console.error('alerts error', err); });
  }

  function loadCertList() {
    fetch(API_BASE)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('ci-list');
        var certs = data.certificates || [];
        if (certs.length === 0) {
          container.innerHTML = '<p class="ci-loading">No certificates recorded.</p>';
          return;
        }
        var html = '';
        certs.forEach(function (c) {
          html += '<div class="ci-cert-row" data-id="' + escHtml(c.cert_id) + '">';
          html += '<div>';
          html += '<span class="ci-grade ' + gradeClass(c.grade) + '">' + escHtml(c.grade) + '</span>';
          html += ' <span class="ci-cert-meta">domain: ' + escHtml(c.domain_hash.slice(0, 12)) + '… | days: ' + escHtml(String(c.validity_days_remaining)) + '</span>';
          html += '</div>';
          html += '<div>';
          html += '<span class="ci-cert-meta">' + formatDate(c.recorded_at) + '</span> ';
          html += '<button class="ci-btn ci-btn-danger ci-delete-btn" data-id="' + escHtml(c.cert_id) + '">Delete</button>';
          html += '</div>';
          html += '</div>';
        });
        container.innerHTML = html;
        container.querySelectorAll('.ci-delete-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteCert(btn.getAttribute('data-id'));
          });
        });
      })
      .catch(function (err) { console.error('list error', err); });
  }

  function deleteCert(id) {
    fetch(API_BASE + '/' + encodeURIComponent(id), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () { loadCertList(); loadAlerts(); })
      .catch(function (err) { console.error('delete error', err); });
  }

  function recordCert() {
    fetch(API_BASE + '/record', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        domain: document.getElementById('ci-domain').value.trim(),
        fingerprint: document.getElementById('ci-fingerprint').value.trim(),
        issuer: document.getElementById('ci-issuer').value.trim(),
        subject: document.getElementById('ci-subject').value.trim(),
        grade: document.getElementById('ci-grade').value,
        validity_days_remaining: parseInt(document.getElementById('ci-validity').value, 10) || 365,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showMsg('Recorded: ' + (data.cert_id || ''));
        loadCertList();
        loadAlerts();
      })
      .catch(function (err) { console.error('record error', err); });
  }

  document.getElementById('ci-record-btn').addEventListener('click', recordCert);

  loadAlerts();
  loadCertList();
}());
