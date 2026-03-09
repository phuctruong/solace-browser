/* page-summary-ai.js — Page Summary AI | Task 129 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_SUMMARIES = '/api/v1/page-summary/summaries';
  var API_STATS     = '/api/v1/page-summary/stats';
  var API_TYPES     = '/api/v1/page-summary/summary-types';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('psa-status');
    if (el) el.textContent = msg;
  }

  function loadTypes() {
    fetch(API_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var types = data.summary_types || [];
        var sel = document.getElementById('psa-type');
        if (sel) {
          sel.innerHTML = types.map(function (t) {
            return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
          }).join('');
        }
        var modelSel = document.getElementById('psa-model');
        if (modelSel) {
          var models = ['haiku', 'sonnet', 'opus', 'gpt4', 'gpt4o', 'local'];
          modelSel.innerHTML = models.map(function (m) {
            return '<option value="' + escHtml(m) + '">' + escHtml(m) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading types: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS, { headers: { Authorization: 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('psa-stats');
        if (!el) return;
        el.innerHTML =
          '<span>Total: ' + escHtml(String(data.total_summaries || 0)) + '</span> ' +
          '<span>Avg quality: ' + escHtml(String(data.avg_quality || '0.00')) + '</span> ' +
          '<span>Total cost: $' + escHtml(String(data.total_cost_usd || '0')) + '</span>';
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function loadSummaries() {
    fetch(API_SUMMARIES, { headers: { Authorization: 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('psa-list');
        if (!el) return;
        var summaries = data.summaries || [];
        if (summaries.length === 0) { el.innerHTML = '<p>No summaries yet.</p>'; return; }
        el.innerHTML = summaries.map(function (s) {
          return '<div class="psa-item">' +
            '<span>' + escHtml(s.summary_type) + ' / ' + escHtml(s.model) + ' — ' + escHtml(String(s.word_count)) + ' words</span>' +
            '<button class="psa-btn psa-btn-danger" data-id="' + escHtml(s.summary_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteSummary(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading summaries: ' + err.message); });
  }

  function deleteSummary(id) {
    fetch(API_SUMMARIES + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { Authorization: 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadSummaries(); loadStats(); setStatus('Deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadTypes();
    loadStats();
    loadSummaries();

    var form = document.getElementById('psa-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var quality = document.getElementById('psa-quality').value.trim();
        var payload = {
          url: document.getElementById('psa-url').value.trim(),
          title: document.getElementById('psa-title').value.trim(),
          content: document.getElementById('psa-content').value.trim(),
          summary_type: document.getElementById('psa-type').value,
          model: document.getElementById('psa-model').value,
          word_count: parseInt(document.getElementById('psa-words').value, 10) || 0,
          token_cost_usd: document.getElementById('psa-cost').value.trim() || '0',
        };
        if (quality) payload.quality_score = parseInt(quality, 10);
        fetch(API_SUMMARIES, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (window._solaceToken || '') },
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Saved: ' + data.summary.summary_id);
            form.reset();
            loadSummaries();
            loadStats();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
