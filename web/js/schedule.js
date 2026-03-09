/**
 * schedule.js — Schedule 4-Tab Redesign for Solace Hub
 * Laws:
 *   - No CDN dependencies. No jQuery. No Bootstrap. No Tailwind.
 *   - Port 8888 ONLY (same origin).
 *   - AUTO_APPROVE_ON_TIMEOUT = BANNED. Countdown = auto-REJECT only.
 *   - Solace Hub only. Legacy name BANNED.
 */

'use strict';

const TOKEN = localStorage.getItem('solace_token') || '';

function apiFetch(path, opts) {
  var options = opts || {};
  return fetch(path, {
    headers: Object.assign(
      { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json' },
      options.headers || {}
    ),
    method: options.method || 'GET',
    body: options.body || undefined,
  });
}

// --- Tab switching ---
document.querySelectorAll('.tab').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.tab-panel').forEach(function(p) {
      p.classList.remove('active');
      p.hidden = true;
    });
    btn.classList.add('active');
    var panel = document.getElementById('tab-' + btn.dataset.tab);
    panel.hidden = false;
    panel.classList.add('active');
    if (btn.dataset.tab === 'upcoming') { loadUpcoming(); }
    if (btn.dataset.tab === 'approval') { loadApprovalQueue(); }
    if (btn.dataset.tab === 'history') { loadHistory(); }
    if (btn.dataset.tab === 'esign') { loadESign(); }
  });
});

// --- Tab 1: Upcoming ---
function loadUpcoming() {
  Promise.all([
    apiFetch('/api/v1/schedule/upcoming').then(function(r) { return r.json(); }),
    apiFetch('/api/v1/schedule/calendar').then(function(r) { return r.json(); }),
    apiFetch('/api/v1/schedule/roi').then(function(r) { return r.json(); })
  ])
    .then(function(results) {
      var upcoming = results[0] || {};
      renderSchedules(upcoming.schedules || []);
      renderKeepalive(upcoming.keepalive || {});
      renderPendingCounters(upcoming);
      updateApprovalBadge(upcoming.pending_approvals || 0);
      renderCalendar(results[1] || {});
      renderRoiStrip(results[2] || {});
    })
    .catch(function() {});
}

function renderSchedules(schedules) {
  var el = document.getElementById('schedules-list');
  if (!schedules.length) {
    el.innerHTML = '';
    return;
  }
  el.innerHTML = schedules.map(function(s) {
    return '<div class="schedule-row" onclick="openScheduleEditor(\'' + s.app_id + '\')">' +
      '<span>' + (s.app_name || s.app_id) + '</span>' +
      '<span class="schedule-row__cron">' + (s.cron_human || s.cron) + '</span>' +
      '<span class="schedule-row__cron">' + (s.countdown_seconds ? 'in ' + fmtSecs(s.countdown_seconds) : '') + '</span>' +
      '</div>';
  }).join('');
}

function renderCalendar(days) {
  var el = document.getElementById('calendar-view');
  var keys = Object.keys(days).sort();
  if (!keys.length) {
    el.innerHTML = '<div class="empty-state">No scheduled activity yet.</div>';
    return;
  }
  el.innerHTML = keys.map(function(day) {
    var pills = (days[day] || []).map(function(item) {
      return '<span class="calendar-pill status-' + item.status + '">' + item.time + ' · ' + item.app + '</span>';
    }).join('');
    return '<section class="calendar-day"><h4>' + day + '</h4><div class="calendar-pills">' + pills + '</div></section>';
  }).join('');
}

function renderRoiStrip(roi) {
  document.getElementById('roi-week-runs').textContent = String(roi.week_runs || 0);
  document.getElementById('roi-hours-saved').textContent = String(roi.week_hours_saved || '0.00') + 'h';
  document.getElementById('roi-value-usd').textContent = '$' + String(roi.week_value_usd_at_30_per_hour || '0.00');
}

function renderKeepalive(ka) {
  var el = document.getElementById('keepalive-summary');
  if (ka.active_count != null) {
    el.innerHTML = '<p>' + ka.active_count + ' active session(s). Next refresh in ' + fmtSecs(ka.next_refresh_seconds || 0) + '.</p>';
  } else {
    el.innerHTML = '<p style="color:var(--hub-text-muted)">No keep-alive sessions.</p>';
  }
}

function renderPendingCounters(data) {
  var el = document.getElementById('pending-counters');
  var parts = [];
  if (data.pending_approvals) {
    parts.push('<span style="color:var(--hub-warning)">' + data.pending_approvals + ' awaiting approval</span>');
  }
  if (data.pending_esign) {
    parts.push('<span style="color:var(--hub-warning)">' + data.pending_esign + ' awaiting eSign</span>');
  }
  el.innerHTML = parts.join(' &nbsp;|&nbsp; ') || '';
}

function updateApprovalBadge(count) {
  var badge = document.getElementById('approval-badge');
  badge.hidden = count === 0;
  badge.textContent = count;
}

// --- Tab 2: Approval Queue ---
var _countdowns = {};

function loadApprovalQueue() {
  Promise.all([
    apiFetch('/api/v1/schedule/queue').then(function(r) { return r.json(); }),
    apiFetch('/api/v1/schedule').then(function(r) { return r.json(); })
  ])
    .then(function(results) {
      var queueData = results[0] || {};
      var scheduleData = results[1] || {};
      renderApprovalQueue(queueData.queue || []);
      renderKanban(scheduleData.items || []);
    })
    .catch(function() {});
}

function renderApprovalQueue(items) {
  var el = document.getElementById('approval-list');
  renderSignoffSheet(items);
  if (!items.length) { el.innerHTML = ''; return; }
  el.innerHTML = items.map(function(item) {
    return '<div class="approval-item" id="approval-' + item.run_id + '">' +
      '<div><strong>' + item.action_type + '</strong> &mdash; ' + item.app_id + '</div>' +
      '<div class="approval-item__countdown" id="countdown-' + item.run_id + '">' +
        item.countdown_seconds_remaining + 's &rarr; auto-REJECT' +
      '</div>' +
      '<div class="approval-item__actions">' +
        '<button class="btn-approve" onclick="approveItem(\'' + item.run_id + '\')">Approve</button>' +
        '<button class="btn-reject" onclick="rejectItem(\'' + item.run_id + '\')">Reject</button>' +
      '</div>' +
    '</div>';
  }).join('');
  items.forEach(function(item) {
    startCountdown(item.run_id, item.countdown_seconds_remaining);
  });
}

function renderKanban(items) {
  var board = document.getElementById('kanban-board');
  var groups = { past: [], pending: [], future: [] };
  items.forEach(function(item) {
    if (item.status === 'scheduled' || item.status === 'queued') { groups.future.push(item); return; }
    if (item.status === 'pending_approval' || item.status === 'cooldown') { groups.pending.push(item); return; }
    groups.past.push(item);
  });
  board.innerHTML = ['past', 'pending', 'future'].map(function(key) {
    var title = key === 'past' ? 'Past' : key === 'pending' ? 'Pending' : 'Future';
    var cards = groups[key].map(function(item) {
      return '<div class="kanban-card status-' + item.status + '"><strong>' + (item.app_name || item.app_id) + '</strong><span>' + item.status + '</span></div>';
    }).join('') || '<div class="empty-state">None</div>';
    return '<section class="kanban-column"><h4>' + title + '</h4>' + cards + '</section>';
  }).join('');
}

function renderSignoffSheet(items) {
  var sheet = document.getElementById('signoff-sheet');
  var list = document.getElementById('signoff-list');
  sheet.hidden = items.length === 0;
  list.innerHTML = items.map(function(item) {
    return '<div class="signoff-item">' +
      '<strong>' + item.app_id + '</strong>' +
      '<div>' + item.action_type + '</div>' +
      '<div class="approval-item__countdown">' + item.countdown_seconds_remaining + 's → auto-REJECT</div>' +
    '</div>';
  }).join('');
}

// AUTO-REJECT on countdown = 0. NEVER auto-approve.
function startCountdown(runId, seconds) {
  if (_countdowns[runId]) { clearInterval(_countdowns[runId]); }
  var remaining = seconds;
  _countdowns[runId] = setInterval(function() {
    remaining--;
    var el = document.getElementById('countdown-' + runId);
    if (el) { el.textContent = remaining + 's \u2192 auto-REJECT'; }
    if (remaining <= 0) {
      clearInterval(_countdowns[runId]);
      autoRejectItem(runId);
    }
  }, 1000);
}

async function autoRejectItem(runId) {
  return rejectItem(runId);
}

async function refreshSignoffQueue() {
  return loadApprovalQueue();
}

function approveItem(runId) {
  apiFetch('/api/v1/schedule/approve/' + runId, { method: 'POST' })
    .then(function() { loadApprovalQueue(); })
    .catch(function() {});
}

function rejectItem(runId) {
  if (_countdowns[runId]) { clearInterval(_countdowns[runId]); }
  apiFetch('/api/v1/schedule/cancel/' + runId, {
    method: 'POST',
    body: JSON.stringify({ reason: 'user_rejected' }),
  }).then(function() {
    var el = document.getElementById('approval-' + runId);
    if (el) { el.remove(); }
  }).catch(function() {});
}

// --- Tab 3: History ---
function loadHistory() {
  apiFetch('/api/v1/schedule')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      renderHistory(data.runs || data.items || []);
    })
    .catch(function() {});
  apiFetch('/api/v1/schedule/roi')
    .then(function(r) { return r.json(); })
    .then(function(roi) {
      document.getElementById('roi-display').innerHTML =
        '<p>This week: ' + (roi.hours_saved_this_week || roi.week_hours_saved || 0) + 'h saved' +
        ' \u2192 $' + (roi.value_usd_this_week || roi.week_value_usd_at_30_per_hour || '0.00') + ' at $30/hr</p>';
    })
    .catch(function() {});
}

function renderHistory(runs) {
  var timeline = document.getElementById('timeline-view');
  var el = document.getElementById('history-list');
  if (!runs.length) {
    timeline.innerHTML = '<div class="empty-state">No activity yet.</div>';
    el.innerHTML = '';
    return;
  }
  timeline.innerHTML = runs.map(function(r) {
    return '<div class="timeline-item">' +
      '<strong>' + (r.app_id || '') + '</strong>' +
      '<span>' + (r.status || '') + '</span>' +
      '<span>' + (r.scheduled_at || r.started_at || '') + '</span>' +
    '</div>';
  }).join('');
  el.innerHTML = '';
}

// --- Tab 4: List ---
function loadESign() {
  apiFetch('/api/v1/schedule')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      renderScheduleList(data.items || []);
    })
    .catch(function() {});
}

function renderScheduleList(items) {
  var el = document.getElementById('list-view');
  if (!items.length) {
    el.innerHTML = '<div class="empty-state">No rows yet.</div>';
    return;
  }
  el.innerHTML = '<table class="schedule-table"><thead><tr><th>App</th><th>Status</th><th>When</th><th>Safety</th></tr></thead><tbody>' + items.map(function(item) {
    return '<tr><td>' + (item.app_name || item.app_id) + '</td><td>' + item.status + '</td><td>' + (item.scheduled_at || item.started_at || '') + '</td><td>' + (item.safety_tier || '') + '</td></tr>';
  }).join('') + '</tbody></table>';
}

function renderESignPending(items) {
  var el = document.getElementById('esign-pending');
  if (!items.length) {
    el.innerHTML = '<p style="color:var(--hub-text-muted)">No pending signatures.</p>';
    return;
  }
  el.innerHTML = '<h4>Pending Signatures</h4>' + items.map(function(i) {
    return '<div class="esign-item">' +
      '<div>' + i.preview_text + '</div>' +
      '<div class="esign-item__status">Requested by ' + i.requested_by + ' \u2022 Expires ' + i.expires_at + '</div>' +
      '<button class="btn-approve" onclick="signItem(\'' + i.esign_id + '\')">Sign</button>' +
    '</div>';
  }).join('');
}

function renderESignHistory(items) {
  var el = document.getElementById('esign-history');
  if (!items.length) { el.innerHTML = ''; return; }
  el.innerHTML = '<h4>Signed History</h4>' + items.map(function(i) {
    return '<div class="esign-item">' +
      '<div>' + i.action_type + ' \u2014 Signed ' + i.signed_at + '</div>' +
      '<div class="esign-item__status">By ' + i.approver + ' | Hash: ' + (i.evidence_hash ? i.evidence_hash.slice(0, 12) : '') + '...</div>' +
    '</div>';
  }).join('');
}

function signItem(esignId) {
  var token = prompt('Enter signature token:');
  if (!token) { return; }
  apiFetch('/api/v1/esign/' + esignId + '/sign', {
    method: 'POST',
    body: JSON.stringify({ signature_token: token }),
  }).then(function() { loadESign(); }).catch(function() {});
}

// --- Schedule Editor Drawer ---
function openScheduleEditor(appId) {
  document.getElementById('schedule-drawer').hidden = false;
}

document.getElementById('cancel-schedule-btn').addEventListener('click', function() {
  document.getElementById('schedule-drawer').hidden = true;
});

document.getElementById('cron-preset').addEventListener('change', function() {
  document.getElementById('cron-raw').hidden = this.value !== 'custom';
});

document.getElementById('bulk-approve-a').addEventListener('click', function() {
  apiFetch('/api/v1/schedule/queue')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      (data.queue || []).filter(function(item) { return item.class === 'A'; }).forEach(function(item) {
        approveItem(item.run_id);
      });
    })
    .catch(function() {});
});

// --- Utility ---
function fmtSecs(s) {
  if (s < 60) { return s + 's'; }
  if (s < 3600) { return Math.floor(s / 60) + 'm'; }
  return Math.floor(s / 3600) + 'h ' + Math.floor((s % 3600) / 60) + 'm';
}

// --- Init ---
loadUpcoming();
loadApprovalQueue();
setInterval(loadUpcoming, 30000);
