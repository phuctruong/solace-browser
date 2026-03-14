// Diagram: 02-dashboard-login
/* dark-mode-scheduler.js — Dark Mode Scheduler | Task 142 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_SCHEDULES     = '/api/v1/dark-mode/schedules';
  var API_CURRENT       = '/api/v1/dark-mode/current';
  var API_OVERRIDE      = '/api/v1/dark-mode/override';
  var API_TRIGGER_TYPES = '/api/v1/dark-mode/trigger-types';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('dms-status');
    if (el) el.textContent = msg;
  }

  function authHeaders() {
    return { Authorization: 'Bearer ' + (window._solaceToken || '') };
  }

  function loadTriggerTypes() {
    fetch(API_TRIGGER_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var types = data.trigger_types || [];
        var sel = document.getElementById('dms-trigger-type');
        if (sel) {
          sel.innerHTML = types.map(function (t) {
            return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading trigger types: ' + err.message); });
  }

  function loadCurrentMode() {
    fetch(API_CURRENT, { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var badge = document.getElementById('dms-current-badge');
        var source = document.getElementById('dms-current-source');
        if (badge) {
          badge.textContent = data.mode || 'unknown';
          badge.className = 'dms-mode-badge ' + (data.mode === 'dark' ? 'dms-mode-dark' : 'dms-mode-light');
        }
        if (source) source.textContent = 'source: ' + escHtml(data.source || 'default');
      })
      .catch(function (err) { setStatus('Error loading current mode: ' + err.message); });
  }

  function loadSchedules() {
    fetch(API_SCHEDULES, { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('dms-schedules-list');
        if (!el) return;
        var schedules = data.schedules || [];
        if (schedules.length === 0) { el.innerHTML = '<p>No schedules yet.</p>'; return; }
        el.innerHTML = schedules.map(function (s) {
          var hours = (s.dark_start_hour != null && s.dark_end_hour != null)
            ? escHtml(String(s.dark_start_hour)) + ':00 \u2013 ' + escHtml(String(s.dark_end_hour)) + ':00'
            : 'n/a';
          return '<div class="dms-item">' +
            '<span>' +
              escHtml(s.trigger_type) + ' | ' + hours +
              (s.enabled ? '' : ' | <em>disabled</em>') +
            '</span>' +
            '<button class="dms-btn dms-btn-danger" data-id="' + escHtml(s.schedule_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteSchedule(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading schedules: ' + err.message); });
  }

  function deleteSchedule(scheduleId) {
    fetch(API_SCHEDULES + '/' + scheduleId, { method: 'DELETE', headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function () { setStatus('Schedule deleted.'); loadSchedules(); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  function bindScheduleForm() {
    var form = document.getElementById('dms-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var triggerType    = document.getElementById('dms-trigger-type').value;
      var darkStartHour  = parseInt(document.getElementById('dms-start-hour').value, 10);
      var darkEndHour    = parseInt(document.getElementById('dms-end-hour').value, 10);
      fetch(API_SCHEDULES, {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        body: JSON.stringify({
          trigger_type: triggerType,
          dark_start_hour: darkStartHour,
          dark_end_hour: darkEndHour,
          enabled: true,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error) { setStatus('Error: ' + escHtml(data.error)); return; }
          setStatus('Schedule created.');
          form.reset();
          loadSchedules();
          loadCurrentMode();
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  function bindOverride() {
    ['dms-override-dark', 'dms-override-light'].forEach(function (id) {
      var btn = document.getElementById(id);
      if (!btn) return;
      btn.addEventListener('click', function () {
        var mode = id === 'dms-override-dark' ? 'dark' : 'light';
        var untilHourEl = document.getElementById('dms-until-hour');
        var until = untilHourEl && untilHourEl.value ? parseInt(untilHourEl.value, 10) : undefined;
        fetch(API_OVERRIDE, {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
          body: JSON.stringify({ mode: mode, until_hour: until }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + escHtml(data.error)); return; }
            setStatus('Override set: ' + escHtml(data.mode));
            loadCurrentMode();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadTriggerTypes();
    loadCurrentMode();
    loadSchedules();
    bindScheduleForm();
    bindOverride();
  });
}());
