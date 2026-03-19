/* schedule-tz.js — extracted from schedule-tz.html */
(function () {
  'use strict';

  /* ---- Cron next-run calculator (no library) ---- */
  function nextRuns(cronStr, tz, count) {
    count = count || 3;
    var parts = cronStr.trim().split(/\s+/);
    if (parts.length !== 5) return [];
    var minutePart = parts[0];
    var hourPart   = parts[1];
    var domPart    = parts[2];
    var monthPart  = parts[3];
    var dowPart    = parts[4];

    function matchField(val, part, min, max) {
      if (part === '*') return true;
      if (part.startsWith('*/')) {
        var step = parseInt(part.slice(2), 10);
        if (isNaN(step) || step <= 0) return false;
        return (val - min) % step === 0;
      }
      var n = parseInt(part, 10);
      return !isNaN(n) && n === val;
    }

    var results = [];
    var now = new Date();
    var cursor = new Date(now.getTime() + 60000);
    cursor.setSeconds(0, 0);

    var limit = 0;
    while (results.length < count && limit < 1440 * 7) {
      limit++;
      var min = cursor.getMinutes();
      var hr  = cursor.getHours();
      var dom = cursor.getDate();
      var mo  = cursor.getMonth() + 1;
      var dow = cursor.getDay();

      if (
        matchField(min, minutePart, 0, 59) &&
        matchField(hr,  hourPart,   0, 23) &&
        matchField(dom, domPart,    1, 31) &&
        matchField(mo,  monthPart,  1, 12) &&
        matchField(dow, dowPart,    0,  6)
      ) {
        try {
          var label = cursor.toLocaleString('en-US', {
            timeZone: tz,
            year:   'numeric',
            month:  'short',
            day:    'numeric',
            hour:   '2-digit',
            minute: '2-digit',
            timeZoneName: 'short'
          });
          results.push(label);
        } catch (e) {
          results.push(cursor.toISOString());
        }
      }
      cursor = new Date(cursor.getTime() + 60000);
    }
    return results;
  }

  /* ---- Toast notifications ---- */
  function toast(msg, type) {
    var area = document.getElementById('toast-area');
    var el = document.createElement('div');
    el.className = 'toast ' + (type || '');
    el.textContent = msg;
    area.appendChild(el);
    setTimeout(function () { el.remove(); }, 3500);
  }

  /* ---- Cron preview live update ---- */
  var cronInput  = document.getElementById('sched-cron');
  var tzSelect   = document.getElementById('sched-tz');
  var previewEl  = document.getElementById('cron-preview');

  function updatePreview() {
    var cron = cronInput.value.trim();
    var tz   = tzSelect.value || 'UTC';
    if (!cron) {
      previewEl.textContent = 'Enter a cron expression to preview next runs.';
      previewEl.className = 'preview-box';
      return;
    }
    var runs = nextRuns(cron, tz, 3);
    if (runs.length === 0) {
      previewEl.textContent = 'Invalid cron expression.';
      previewEl.className = 'preview-box invalid';
    } else {
      previewEl.textContent = runs.join(' | ');
      previewEl.className = 'preview-box valid';
    }
  }
  cronInput.addEventListener('input', updatePreview);
  tzSelect.addEventListener('change', updatePreview);
  updatePreview();

  /* ---- API helpers ---- */
  function apiFetch(path, opts) {
    var url = 'http://localhost:8888' + path;
    return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}));
  }

  /* ---- HTML escaping ---- */
  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ---- Load + render schedules ---- */
  function renderSchedules(schedules) {
    var tbody = document.getElementById('schedules-body');
    if (!schedules || schedules.length === 0) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No schedules yet. Create one above.</td></tr>';
      return;
    }
    tbody.innerHTML = schedules.map(function (s) {
      var tz     = s.tz || 'UTC';
      var cron   = s.cron || '';
      var name   = s.name || s.app_id || s.id || '\u2014';
      var enabled = s.enabled !== false;
      var status = enabled ? '<span class="badge badge-active">Active</span>' : '<span class="badge badge-paused">Paused</span>';
      var runs   = nextRuns(cron, tz, 1);
      var nextRun = runs.length > 0 ? runs[0] : '\u2014';
      var pauseBtn = enabled
        ? '<button class="btn btn-warning btn-sm" data-action="patch" data-schedule-id="' + escHtml(s.id) + '" data-schedule-action="pause">Pause</button>'
        : '<button class="btn btn-success btn-sm" data-action="patch" data-schedule-id="' + escHtml(s.id) + '" data-schedule-action="resume">Resume</button>';
      var deleteBtn = '<button class="btn btn-danger btn-sm" data-action="delete" data-schedule-id="' + escHtml(s.id) + '">Delete</button>';
      return '<tr>' +
        '<td>' + escHtml(name) + '</td>' +
        '<td><code>' + escHtml(cron) + '</code></td>' +
        '<td>' + escHtml(tz) + '</td>' +
        '<td style="font-size:12px;">' + escHtml(nextRun) + '</td>' +
        '<td>' + status + '</td>' +
        '<td><div class="actions">' + pauseBtn + deleteBtn + '</div></td>' +
        '</tr>';
    }).join('');
  }

  function loadSchedules() {
    apiFetch('/api/v1/browser/schedules')
      .then(function (r) { return r.json(); })
      .then(function (data) { renderSchedules(data.schedules || []); })
      .catch(function () {
        document.getElementById('schedules-body').innerHTML =
          '<tr class="empty-row"><td colspan="6">Unable to reach Yinyang Server.</td></tr>';
      });
  }

  /* ---- Patch (pause/resume) schedule ---- */
  function patchSchedule(id, action) {
    apiFetch('/api/v1/schedules/' + id, {
      method: 'PATCH',
      body: JSON.stringify({ action: action })
    }).then(function (r) {
      if (r.ok) {
        toast(action === 'pause' ? 'Schedule paused.' : 'Schedule resumed.', 'success');
        loadSchedules();
      } else {
        toast('Failed to ' + action + ' schedule.', 'error');
      }
    }).catch(function () { toast('Network error.', 'error'); });
  }

  /* ---- Delete schedule ---- */
  function deleteSchedule(id) {
    apiFetch('/api/v1/browser/schedules/' + id, { method: 'DELETE' })
      .then(function (r) {
        if (r.ok) {
          toast('Schedule deleted.', 'success');
          loadSchedules();
        } else {
          toast('Failed to delete schedule.', 'error');
        }
      }).catch(function () { toast('Network error.', 'error'); });
  }

  /* ---- Event delegation for schedule table actions ---- */
  document.getElementById('schedules-table').addEventListener('click', function (e) {
    var target = e.target;
    if (!(target instanceof HTMLElement)) return;
    var action = target.getAttribute('data-action');
    var scheduleId = target.getAttribute('data-schedule-id');
    if (!action || !scheduleId) return;

    if (action === 'patch') {
      var scheduleAction = target.getAttribute('data-schedule-action');
      if (scheduleAction) {
        patchSchedule(scheduleId, scheduleAction);
      }
    } else if (action === 'delete') {
      deleteSchedule(scheduleId);
    }
  });

  /* ---- Create schedule form ---- */
  document.getElementById('create-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var name = document.getElementById('sched-name').value.trim();
    var cron = document.getElementById('sched-cron').value.trim();
    var tz   = document.getElementById('sched-tz').value || 'UTC';
    if (!name || !cron) { toast('Name and cron are required.', 'error'); return; }
    apiFetch('/api/v1/schedules', {
      method: 'POST',
      body: JSON.stringify({ name: name, cron: cron, tz: tz })
    }).then(function (r) {
      if (r.status === 201 || r.status === 200) {
        toast('Schedule created.', 'success');
        document.getElementById('sched-name').value = '';
        loadSchedules();
      } else {
        r.json().then(function (d) { toast('Error: ' + (d.error || 'unknown'), 'error'); });
      }
    }).catch(function () { toast('Network error.', 'error'); });
  });

  /* ---- Run history ---- */
  function loadHistory() {
    apiFetch('/api/v1/evidence/log?type=schedule')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var entries = (data.entries || data.log || []).slice(0, 10);
        var tbody = document.getElementById('history-body');
        if (entries.length === 0) {
          tbody.innerHTML = '<tr class="empty-row"><td colspan="3">No schedule history yet.</td></tr>';
          return;
        }
        tbody.innerHTML = entries.map(function (e) {
          var name = e.name || e.schedule_name || e.app_id || '\u2014';
          var ts   = e.triggered_at || e.ts || e.timestamp || '';
          var local = ts ? new Date(typeof ts === 'number' ? ts * 1000 : ts).toLocaleString() : '\u2014';
          var ok   = e.status === 'ok' || e.status === 'success' || e.action === 'schedule_created';
          var badge = ok
            ? '<span class="badge badge-ok">ok</span>'
            : '<span class="badge badge-fail">fail</span>';
          return '<tr><td>' + escHtml(name) + '</td><td>' + escHtml(local) + '</td><td>' + badge + '</td></tr>';
        }).join('');
      })
      .catch(function () {
        document.getElementById('history-body').innerHTML =
          '<tr class="empty-row"><td colspan="3">Unable to load history.</td></tr>';
      });
  }

  /* ---- Auto-refresh every 30s ---- */
  loadSchedules();
  loadHistory();
  setInterval(function () { loadSchedules(); loadHistory(); }, 30000);
}());
