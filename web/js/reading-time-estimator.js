/* reading-time-estimator.js — Reading Time Estimator | Task 130 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_ESTIMATES = '/api/v1/reading-time/estimates';
  var API_STATS     = '/api/v1/reading-time/stats';
  var API_TYPES     = '/api/v1/reading-time/content-types';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('rte-status');
    if (el) el.textContent = msg;
  }

  function loadContentTypes() {
    fetch(API_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var types = data.content_types || [];
        var sel = document.getElementById('rte-content-type');
        if (sel) {
          sel.innerHTML = types.map(function (t) {
            return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading types: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS, { headers: { Authorization: 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('rte-stats');
        if (!el) return;
        el.innerHTML =
          '<span>Total: ' + escHtml(String(data.total_estimates || 0)) + '</span> ' +
          '<span>Avg estimated: ' + escHtml(String(data.avg_estimated_minutes || '0.00')) + ' min</span>' +
          (data.avg_accuracy_pct ? ' <span>Avg accuracy: ' + escHtml(String(data.avg_accuracy_pct)) + '%</span>' : '');
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function loadEstimates() {
    fetch(API_ESTIMATES, { headers: { Authorization: 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('rte-list');
        if (!el) return;
        var estimates = data.estimates || [];
        if (estimates.length === 0) { el.innerHTML = '<p>No estimates yet.</p>'; return; }
        el.innerHTML = estimates.map(function (e) {
          return '<div class="rte-item">' +
            '<span>' + escHtml(e.content_type) + ' — ' + escHtml(String(e.word_count)) + ' words — ~' + escHtml(e.estimated_minutes) + ' min</span>' +
            '<button class="rte-btn rte-btn-danger" data-id="' + escHtml(e.estimate_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteEstimate(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading estimates: ' + err.message); });
  }

  function deleteEstimate(id) {
    fetch(API_ESTIMATES + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { Authorization: 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadEstimates(); loadStats(); setStatus('Deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadContentTypes();
    loadStats();
    loadEstimates();

    var form = document.getElementById('rte-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var actual = document.getElementById('rte-actual').value.trim();
        var payload = {
          url: document.getElementById('rte-url').value.trim(),
          content_type: document.getElementById('rte-content-type').value,
          word_count: parseInt(document.getElementById('rte-word-count').value, 10) || 0,
        };
        if (actual) payload.actual_minutes = actual;
        fetch(API_ESTIMATES, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (window._solaceToken || '') },
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Saved: ' + data.estimate.estimate_id + ' — ~' + data.estimate.estimated_minutes + ' min');
            form.reset();
            loadEstimates();
            loadStats();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
