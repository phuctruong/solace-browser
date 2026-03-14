// Diagram: 02-dashboard-login
/* reading-goals-tracker.js — Reading Goals Tracker | Task 141 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_GOALS      = '/api/v1/reading-goals/goals';
  var API_STATS      = '/api/v1/reading-goals/stats';
  var API_GOAL_TYPES = '/api/v1/reading-goals/goal-types';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('rgt-status');
    if (el) el.textContent = msg;
  }

  function authHeaders() {
    return { Authorization: 'Bearer ' + (window._solaceToken || '') };
  }

  function loadGoalTypes() {
    fetch(API_GOAL_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var types = data.goal_types || [];
        var sel = document.getElementById('rgt-goal-type');
        if (sel) {
          sel.innerHTML = types.map(function (t) {
            return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading goal types: ' + err.message); });
  }

  function progressPercent(current, target) {
    var c = parseFloat(current) || 0;
    var t = parseFloat(target) || 1;
    return Math.min(100, Math.round((c / t) * 100));
  }

  function loadGoals() {
    fetch(API_GOALS, { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('rgt-goals-list');
        if (!el) return;
        var goals = data.goals || [];
        if (goals.length === 0) { el.innerHTML = '<p>No goals yet.</p>'; return; }
        el.innerHTML = goals.map(function (g) {
          var pct = progressPercent(g.current_value, g.target_value);
          return '<div class="rgt-item" data-id="' + escHtml(g.goal_id) + '">' +
            '<div class="rgt-item-header">' +
              '<span class="rgt-item-type">' + escHtml(g.goal_type) + '</span>' +
              (g.completed ? '<span class="rgt-item-complete">COMPLETED</span>' : '<span>' + escHtml(String(pct)) + '%</span>') +
            '</div>' +
            '<div class="rgt-progress-bar"><div class="rgt-progress-fill" style="width:' + escHtml(String(pct)) + '%"></div></div>' +
            '<small>' + escHtml(g.current_value) + ' / ' + escHtml(g.target_value) +
              (g.deadline ? ' | deadline: ' + escHtml(g.deadline) : '') + '</small>' +
            '<div class="rgt-item-actions">' +
              '<input class="rgt-increment-input" type="number" min="0.01" step="0.01" placeholder="Add" />' +
              '<button class="rgt-btn rgt-btn-success" data-progress-id="' + escHtml(g.goal_id) + '">Progress</button>' +
              '<button class="rgt-btn rgt-btn-danger" data-delete-id="' + escHtml(g.goal_id) + '">Delete</button>' +
            '</div>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-progress-id]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var gid = btn.getAttribute('data-progress-id');
            var item = el.querySelector('[data-id="' + gid + '"]');
            var input = item ? item.querySelector('.rgt-increment-input') : null;
            var inc = input ? input.value.trim() : '';
            if (!inc) { setStatus('Enter increment value.'); return; }
            addProgress(gid, inc);
          });
        });
        el.querySelectorAll('button[data-delete-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteGoal(btn.getAttribute('data-delete-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading goals: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS, { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var totalEl = document.getElementById('rgt-stat-total');
        var doneEl  = document.getElementById('rgt-stat-done');
        var rateEl  = document.getElementById('rgt-stat-rate');
        if (totalEl) totalEl.textContent = data.total_goals || 0;
        if (doneEl)  doneEl.textContent  = data.completed_count || 0;
        if (rateEl)  rateEl.textContent  = data.completion_rate || '0';
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function addProgress(goalId, increment) {
    fetch(API_GOALS + '/' + goalId + '/progress', {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
      body: JSON.stringify({ increment: increment }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { setStatus('Error: ' + escHtml(data.error)); return; }
        setStatus('Progress updated.');
        loadGoals();
        loadStats();
      })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  function deleteGoal(goalId) {
    fetch(API_GOALS + '/' + goalId, { method: 'DELETE', headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function () { setStatus('Goal deleted.'); loadGoals(); loadStats(); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  function bindForm() {
    var form = document.getElementById('rgt-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var goalType    = document.getElementById('rgt-goal-type').value;
      var targetValue = document.getElementById('rgt-target-value').value.trim();
      var deadline    = document.getElementById('rgt-deadline').value.trim() || undefined;
      if (!targetValue) { setStatus('Target value is required.'); return; }
      fetch(API_GOALS, {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({ goal_type: goalType, target_value: targetValue, deadline: deadline }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error) { setStatus('Error: ' + escHtml(data.error)); return; }
          setStatus('Goal created.');
          form.reset();
          loadGoals();
          loadStats();
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadGoalTypes();
    loadGoals();
    loadStats();
    bindForm();
  });
}());
