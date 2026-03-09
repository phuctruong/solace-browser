(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function apiGet(path) {
    return fetch(path).then(function (r) { return r.json(); });
  }

  function apiPost(path, body) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function loadSummary() {
    apiGet('/api/v1/cost/summary').then(function (data) {
      var dailyTotal = data.daily_total_usd || '0.000000';
      var dailyLimit = data.daily_limit || '5.00';
      var pct = parseFloat(data.daily_pct || '0');
      var gaugeBar = document.getElementById('ct-gauge-bar');
      var gaugeLabel = document.getElementById('ct-gauge-label');
      var alert = document.getElementById('ct-alert');
      if (gaugeBar) {
        gaugeBar.style.width = Math.min(pct, 100) + '%';
        if (pct >= 80) {
          gaugeBar.style.background = 'var(--hub-danger)';
        }
      }
      if (gaugeLabel) {
        gaugeLabel.textContent = '$' + escHtml(dailyTotal) + ' / $' + escHtml(dailyLimit) + ' (' + pct.toFixed(1) + '%)';
      }
      if (alert) {
        if (data.alert) {
          alert.textContent = 'Warning: over 80% of daily budget used!';
          alert.hidden = false;
        } else {
          alert.hidden = true;
        }
      }
      updateTimeline(data);
    });
  }

  function updateTimeline(data) {
    var svg = document.getElementById('ct-timeline');
    if (!svg) return;
    var monthly = parseFloat(data.monthly_total_usd || '0');
    var limit = parseFloat(data.monthly_limit || '50');
    var w = 400;
    var h = 70;
    var pct = limit > 0 ? Math.min(monthly / limit, 1) : 0;
    var barW = Math.round(pct * (w - 20));
    svg.innerHTML =
      '<rect x="10" y="20" width="' + (w - 20) + '" height="30" rx="4" fill="var(--hub-border)"/>' +
      '<rect x="10" y="20" width="' + barW + '" height="30" rx="4" fill="var(--hub-accent)"/>' +
      '<text x="10" y="68" class="ct-svg-label">Monthly: $' + escHtml(data.monthly_total_usd || '0') + ' / $' + escHtml(data.monthly_limit || '50') + '</text>';
  }

  function loadBudget() {
    apiGet('/api/v1/cost/budget').then(function (data) {
      var d = document.getElementById('ct-daily-limit');
      var m = document.getElementById('ct-monthly-limit');
      if (d) d.value = data.daily_limit || '';
      if (m) m.value = data.monthly_limit || '';
    });
  }

  var recordForm = document.getElementById('ct-record-form');
  if (recordForm) {
    recordForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var sid = document.getElementById('ct-session-id').value.trim();
      var model = document.getElementById('ct-model').value;
      var tin = parseInt(document.getElementById('ct-tokens-in').value, 10) || 0;
      var tout = parseInt(document.getElementById('ct-tokens-out').value, 10) || 0;
      var status = document.getElementById('ct-record-status');
      apiPost('/api/v1/cost/record', {
        session_id: sid, model: model, tokens_in: tin, tokens_out: tout,
      }).then(function (data) {
        if (status) {
          if (data.event_id) {
            status.textContent = 'Recorded: $' + escHtml(data.cost_usd) + ' (id: ' + escHtml(data.event_id) + ')';
          } else {
            status.textContent = 'Error: ' + escHtml(data.error || 'unknown');
          }
        }
        loadSummary();
      });
    });
  }

  var budgetForm = document.getElementById('ct-budget-form');
  if (budgetForm) {
    budgetForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var d = document.getElementById('ct-daily-limit').value.trim();
      var m = document.getElementById('ct-monthly-limit').value.trim();
      var body = {};
      if (d) body.daily_limit = d;
      if (m) body.monthly_limit = m;
      apiPost('/api/v1/cost/budget', body).then(function () { loadSummary(); });
    });
  }

  loadSummary();
  loadBudget();
}());
