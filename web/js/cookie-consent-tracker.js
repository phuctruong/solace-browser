/* cookie-consent-tracker.js — Cookie Consent Tracker | Task 111 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_DECISIONS  = '/api/v1/cookie-consent/decisions';
  var API_STATS      = '/api/v1/cookie-consent/stats';
  var API_CATEGORIES = '/api/v1/cookie-consent/categories';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('cct-status');
    if (el) el.textContent = msg;
  }

  var _categories = [];

  function loadCategories() {
    fetch(API_CATEGORIES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _categories = data.categories || [];
        var badgesEl = document.getElementById('cct-categories');
        if (badgesEl) {
          badgesEl.innerHTML = _categories.map(function (c) {
            return '<span class="cct-badge">' + escHtml(c) + '</span>';
          }).join('');
        }
        var checksEl = document.getElementById('cct-cats-checkboxes');
        if (checksEl) {
          checksEl.innerHTML = _categories.map(function (c) {
            return '<label class="cct-check-label">' +
              '<input type="checkbox" name="cat" value="' + escHtml(c) + '"> ' +
              escHtml(c) +
              '</label>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading categories: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('cct-stats');
        if (!el) return;
        var byDec = data.by_decision || {};
        var cards = '<div class="cct-stat-card"><div class="cct-stat-label">Total Decisions</div><div class="cct-stat-value">' + escHtml(String(data.total_decisions || 0)) + '</div></div>';
        cards += '<div class="cct-stat-card"><div class="cct-stat-label">Most Common</div><div class="cct-stat-value" style="font-size:1rem">' + escHtml(data.most_common_decision || 'N/A') + '</div></div>';
        Object.keys(byDec).forEach(function (d) {
          cards += '<div class="cct-stat-card"><div class="cct-stat-label">' + escHtml(d) + '</div><div class="cct-stat-value">' + escHtml(String(byDec[d])) + '</div></div>';
        });
        el.innerHTML = cards;
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function loadDecisions() {
    fetch(API_DECISIONS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('cct-decisions-list');
        if (!el) return;
        var decisions = data.decisions || [];
        if (decisions.length === 0) {
          el.innerHTML = '<p class="cct-empty">No consent decisions recorded.</p>';
          return;
        }
        el.innerHTML = decisions.map(function (d) {
          var cats = (d.categories_accepted || []).join(', ') || 'none';
          return '<div class="cct-row">' +
            '<div class="cct-row-meta">' +
            '<span class="cct-decision-tag">' + escHtml(d.decision) + '</span>' +
            '<span class="cct-hash">' + escHtml((d.site_hash || '').slice(0, 16)) + '&hellip;</span>' +
            '<span class="cct-cats">Accepted: ' + escHtml(cats) + '</span>' +
            '</div>' +
            '<button class="cct-btn cct-btn-danger" data-id="' + escHtml(d.decision_id) + '">Delete</button>' +
            '</div>';
        }).join('');

        el.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteDecision(btn.getAttribute('data-id'));
          });
        });
      })
      .catch(function (err) { setStatus('Error loading decisions: ' + err.message); });
  }

  function deleteDecision(decisionId) {
    fetch(API_DECISIONS + '/' + encodeURIComponent(decisionId), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () {
        setStatus('Deleted: ' + decisionId);
        loadDecisions();
        loadStats();
      })
      .catch(function (err) { setStatus('Delete error: ' + err.message); });
  }

  function initDecisionForm() {
    var form = document.getElementById('cct-decision-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var siteUrl = document.getElementById('cct-site-url').value.trim();
      var decision = document.getElementById('cct-decision').value;
      var checked = Array.prototype.slice.call(form.querySelectorAll('input[name="cat"]:checked'));
      var categoriesAccepted = checked.map(function (c) { return c.value; });
      fetch(API_DECISIONS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site_url: siteUrl,
          decision: decision,
          categories_accepted: categoriesAccepted,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'recorded') {
            setStatus('Recorded: ' + data.decision.decision_id);
            loadDecisions();
            loadStats();
          } else {
            setStatus('Error: ' + (data.error || 'unknown'));
          }
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadCategories();
    loadStats();
    loadDecisions();
    initDecisionForm();
  });
})();
