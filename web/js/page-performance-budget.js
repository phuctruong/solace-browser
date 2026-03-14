// Diagram: 02-dashboard-login
/* page-performance-budget.js — Page Performance Budget | Task 109 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_METRICS      = '/api/v1/perf-budget/metrics';
  var API_BUDGETS      = '/api/v1/perf-budget/budgets';
  var API_MEASUREMENTS = '/api/v1/perf-budget/measurements';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('ppb-status');
    if (el) el.textContent = msg;
  }

  function loadMetrics() {
    fetch(API_METRICS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var metrics = data.metrics || [];
        var metricsEl = document.getElementById('ppb-metrics');
        if (!metricsEl) return;
        metricsEl.innerHTML = metrics.map(function (m) {
          return '<span class="ppb-badge">' + escHtml(m) + '</span>';
        }).join('');

        // Populate metric selects
        ['ppb-metric', 'ppb-msr-metric'].forEach(function (id) {
          var sel = document.getElementById(id);
          if (!sel) return;
          sel.innerHTML = metrics.map(function (m) {
            return '<option value="' + escHtml(m) + '">' + escHtml(m.toUpperCase()) + '</option>';
          }).join('');
        });
      })
      .catch(function (err) { setStatus('Error loading metrics: ' + err.message); });
  }

  function loadBudgets() {
    fetch(API_BUDGETS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('ppb-budgets-list');
        if (!el) return;
        var budgets = data.budgets || [];
        if (budgets.length === 0) {
          el.innerHTML = '<p class="ppb-empty">No budgets defined.</p>';
          return;
        }
        el.innerHTML = budgets.map(function (b) {
          return '<div class="ppb-row">' +
            '<div class="ppb-row-meta">' +
            '<span class="ppb-metric-tag">' + escHtml(b.metric) + '</span>' +
            '<span>' + escHtml(b.budget_value) + ' ' + escHtml(b.unit) + '</span>' +
            '</div>' +
            '<button class="ppb-btn ppb-btn-danger" data-id="' + escHtml(b.budget_id) + '">Delete</button>' +
            '</div>';
        }).join('');

        el.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteBudget(btn.getAttribute('data-id'));
          });
        });
      })
      .catch(function (err) { setStatus('Error loading budgets: ' + err.message); });
  }

  function deleteBudget(budgetId) {
    fetch(API_BUDGETS + '/' + encodeURIComponent(budgetId), { method: 'DELETE' })
      .then(function () { loadBudgets(); })
      .catch(function (err) { setStatus('Delete error: ' + err.message); });
  }

  function loadMeasurements() {
    fetch(API_MEASUREMENTS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('ppb-measurements-list');
        if (!el) return;
        var measurements = data.measurements || [];
        if (measurements.length === 0) {
          el.innerHTML = '<p class="ppb-empty">No measurements recorded.</p>';
          return;
        }
        el.innerHTML = measurements.map(function (m) {
          return '<div class="ppb-row">' +
            '<div class="ppb-row-meta">' +
            '<span class="ppb-metric-tag">' + escHtml(m.metric) + '</span>' +
            '<span>Actual: ' + escHtml(m.actual_value) + ' ' + escHtml(m.unit) + '</span>' +
            '<span>Budget: ' + escHtml(m.budget_value) + '</span>' +
            '<span class="' + (m.exceeded ? 'ppb-exceeded' : 'ppb-ok') + '">' +
            (m.exceeded ? 'EXCEEDED' : 'OK') +
            '</span>' +
            '</div>' +
            '</div>';
        }).join('');
      })
      .catch(function (err) { setStatus('Error loading measurements: ' + err.message); });
  }

  function initBudgetForm() {
    var form = document.getElementById('ppb-budget-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var metric = document.getElementById('ppb-metric').value;
      var budgetValue = document.getElementById('ppb-budget-value').value.trim();
      var unit = document.getElementById('ppb-unit').value.trim();
      fetch(API_BUDGETS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metric: metric, budget_value: budgetValue, unit: unit }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'created') {
            setStatus('Budget created: ' + data.budget.budget_id);
            loadBudgets();
          } else {
            setStatus('Error: ' + (data.error || 'unknown'));
          }
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  function initMeasureForm() {
    var form = document.getElementById('ppb-measure-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var metric = document.getElementById('ppb-msr-metric').value;
      var actualValue = document.getElementById('ppb-actual').value.trim();
      var budgetValue = document.getElementById('ppb-budget-ref').value.trim();
      var unit = document.getElementById('ppb-msr-unit').value.trim();
      var pageHash = document.getElementById('ppb-page-hash').value.trim();
      fetch(API_MEASUREMENTS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          metric: metric, actual_value: actualValue,
          budget_value: budgetValue, unit: unit, page_hash: pageHash,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'recorded') {
            setStatus('Recorded: ' + data.measurement.measurement_id +
              ' | Exceeded: ' + data.measurement.exceeded);
            loadMeasurements();
          } else {
            setStatus('Error: ' + (data.error || 'unknown'));
          }
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadMetrics();
    loadBudgets();
    loadMeasurements();
    initBudgetForm();
    initMeasureForm();
  });
})();
