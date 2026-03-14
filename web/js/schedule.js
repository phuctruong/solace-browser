// Diagram: 02-dashboard-login
/**
 * schedule.js — Schedule Operations 4-tab view for Solace Hub
 * Laws:
 *   - No CDN dependencies. No jQuery. No Bootstrap. No Tailwind.
 *   - AUTO_APPROVE_ON_TIMEOUT = BANNED. Countdown = auto-REJECT only.
 *   - Solace Hub only. Legacy name BANNED.
 */

'use strict';

const TOKEN = localStorage.getItem('solace_token') || '';
const CRON_PRESETS = {
  daily_7am: '0 7 * * *',
  weekdays_9am: '0 9 * * 1-5',
  hourly: '0 * * * *',
  every_2h: '0 */2 * * *',
  weekly_monday: '0 9 * * 1',
};

let activeScheduleAppId = '';
let activeScheduleAppLabel = '';
const countdowns = {};

function apiFetch(path, opts) {
  const options = opts || {};
  return fetch(path, {
    method: options.method || 'GET',
    headers: Object.assign(
      { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json' },
      options.headers || {}
    ),
    body: options.body || undefined,
  });
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function emptyState(message) {
  return '<div class="empty-state">' + escapeHtml(message) + '</div>';
}

function fmtSecs(seconds) {
  const value = Math.max(0, Number(seconds) || 0);
  if (value < 60) {
    return value + 's';
  }
  if (value < 3600) {
    return Math.floor(value / 60) + 'm';
  }
  return Math.floor(value / 3600) + 'h ' + Math.floor((value % 3600) / 60) + 'm';
}

function switchTab(tabName) {
  document.querySelectorAll('.tab').forEach(function(tabButton) {
    tabButton.classList.toggle('active', tabButton.dataset.tab === tabName);
  });
  document.querySelectorAll('.tab-panel').forEach(function(panel) {
    const isActive = panel.id === 'tab-' + tabName;
    panel.hidden = !isActive;
    panel.classList.toggle('active', isActive);
  });
  if (tabName === 'upcoming') {
    loadUpcoming();
  }
  if (tabName === 'approval') {
    loadApprovalQueue();
  }
  if (tabName === 'history') {
    loadHistory();
  }
  if (tabName === 'esign') {
    loadESign();
  }
}

function loadUpcoming() {
  Promise.all([
    apiFetch('/api/v1/schedule/upcoming').then(function(response) { return response.json(); }),
    apiFetch('/api/v1/schedule/roi').then(function(response) { return response.json(); })
  ])
    .then(function(results) {
      const upcoming = results[0] || {};
      const roi = results[1] || {};
      renderSchedules(upcoming.schedules || []);
      renderKeepalive(upcoming.keepalive || {});
      renderPendingCounters(upcoming.pending_approvals || 0, upcoming.pending_esign || 0);
      updateApprovalBadge(upcoming.pending_approvals || 0);
      renderRoiStrip(roi);
    })
    .catch(function() {});
}

function renderSchedules(schedules) {
  const element = document.getElementById('schedules-list');
  if (!schedules.length) {
    element.innerHTML = emptyState('No scheduled activity yet.');
    return;
  }
  element.innerHTML = schedules.map(function(schedule) {
    const countdownLabel = schedule.countdown_seconds ? 'Runs in ' + fmtSecs(schedule.countdown_seconds) : 'Awaiting next run';
    const enabledLabel = schedule.enabled ? 'Enabled' : 'Disabled';
    return '<button class="schedule-row" type="button" data-app-id="' + escapeHtml(schedule.app_id) + '" data-app-name="' + escapeHtml(schedule.app_name || schedule.app_id) + '">' +
      '<span class="schedule-row__identity">' +
        '<strong>' + escapeHtml(schedule.app_name || schedule.app_id) + '</strong>' +
        '<span class="schedule-row__cron">' + escapeHtml(schedule.cron_human || schedule.cron || 'Custom schedule') + '</span>' +
      '</span>' +
      '<span class="schedule-row__meta">' +
        '<span class="schedule-row__countdown">' + escapeHtml(countdownLabel) + '</span>' +
        '<span class="status-chip">' + escapeHtml(enabledLabel) + '</span>' +
      '</span>' +
    '</button>';
  }).join('');
}

function renderKeepalive(keepalive) {
  const element = document.getElementById('keepalive-summary');
  if (keepalive.active_count > 0) {
    element.innerHTML = '<div class="summary-card">' +
      '<strong>' + escapeHtml(String(keepalive.active_count)) + ' session(s) protected</strong>' +
      '<p class="muted-copy">Last refresh ' + escapeHtml(keepalive.last_refresh || 'just now') + ' · next refresh in ' + escapeHtml(fmtSecs(keepalive.next_refresh_seconds || 0)) + '.</p>' +
    '</div>';
    return;
  }
  element.innerHTML = emptyState('No keep-alive sessions right now.');
}

function renderPendingCounters(pendingApprovals, pendingESign) {
  const element = document.getElementById('pending-counters');
  const cards = [];
  if (pendingApprovals > 0) {
    cards.push('<div class="counter-card counter-card--warning"><strong>' + escapeHtml(String(pendingApprovals)) + '</strong><span>Approval Queue</span></div>');
  }
  if (pendingESign > 0) {
    cards.push('<div class="counter-card counter-card--warning"><strong>' + escapeHtml(String(pendingESign)) + '</strong><span>eSign pending</span></div>');
  }
  if (!cards.length) {
    element.innerHTML = emptyState('Everything is clear right now.');
    return;
  }
  element.innerHTML = cards.join('');
}

function renderRoiStrip(roi) {
  document.getElementById('roi-week-runs').textContent = String(roi.week_runs || 0);
  document.getElementById('roi-hours-saved').textContent = String(roi.week_hours_saved || '0.00') + 'h';
  document.getElementById('roi-value-usd').textContent = '$' + String(roi.week_value_usd_at_30_per_hour || '0.00');
}

function updateApprovalBadge(count) {
  const badge = document.getElementById('approval-badge');
  badge.hidden = count === 0;
  badge.textContent = String(count);
}

function loadApprovalQueue() {
  apiFetch('/api/v1/schedule/queue')
    .then(function(response) { return response.json(); })
    .then(function(data) {
      renderApprovalQueue(data.queue || []);
      updateApprovalBadge(data.count || 0);
    })
    .catch(function() {});
}

function renderApprovalQueue(items) {
  const element = document.getElementById('approval-list');
  Object.keys(countdowns).forEach(function(runId) {
    clearInterval(countdowns[runId]);
    delete countdowns[runId];
  });
  if (!items.length) {
    element.innerHTML = emptyState('No approvals waiting for sign-off.');
    return;
  }
  element.innerHTML = items.map(function(item) {
    const riskTier = escapeHtml(item.class || item.risk_tier || 'B');
    const approveDisabled = Number(item.countdown_seconds_remaining || 0) > 0 ? ' disabled' : '';
    return '<article class="approval-item" id="approval-' + escapeHtml(item.run_id) + '">' +
      '<div class="approval-item__header">' +
        '<strong>' + escapeHtml(item.preview_text || item.action_type || item.run_id) + '</strong>' +
        '<span class="risk-badge risk-badge--' + riskTier + '">Risk ' + riskTier + '</span>' +
      '</div>' +
      '<div class="approval-item__meta">' + escapeHtml(item.app_id || '') + ' · ' + escapeHtml(item.action_type || '') + '</div>' +
      '<div class="approval-item__countdown" id="countdown-' + escapeHtml(item.run_id) + '">' + escapeHtml(String(item.countdown_seconds_remaining || 0)) + 's → auto-REJECT</div>' +
      '<div class="approval-item__actions">' +
        '<button class="btn-primary btn-approve" type="button" data-approve-run-id="' + escapeHtml(item.run_id) + '"' + approveDisabled + '>Approve</button>' +
        '<button class="btn-secondary btn-danger btn-reject" type="button" data-reject-run-id="' + escapeHtml(item.run_id) + '">Reject</button>' +
      '</div>' +
    '</article>';
  }).join('');
  items.forEach(function(item) {
    startCountdown(item.run_id, item.countdown_seconds_remaining || 0);
  });
}

function updateCountdownDisplay(runId, remaining) {
  const countdownElement = document.getElementById('countdown-' + runId);
  const approveButton = document.querySelector('[data-approve-run-id="' + runId + '"]');
  if (countdownElement) {
    countdownElement.textContent = String(Math.max(0, remaining)) + 's → auto-REJECT';
  }
  if (approveButton) {
    approveButton.disabled = remaining > 0;
  }
}

function startCountdown(runId, seconds) {
  if (countdowns[runId]) {
    clearInterval(countdowns[runId]);
  }
  let remaining = Math.max(0, Number(seconds) || 0);
  updateCountdownDisplay(runId, remaining);
  if (remaining <= 0) {
    autoRejectItem(runId);
    return;
  }
  countdowns[runId] = setInterval(function() {
    remaining -= 1;
    updateCountdownDisplay(runId, remaining);
    if (remaining <= 0) {
      clearInterval(countdowns[runId]);
      delete countdowns[runId];
      autoRejectItem(runId);
    }
  }, 1000);
}

function markAsRejected(runId) {
  const approvalElement = document.getElementById('approval-' + runId);
  const countdownElement = document.getElementById('countdown-' + runId);
  const approveButton = document.querySelector('[data-approve-run-id="' + runId + '"]');
  if (approvalElement) {
    approvalElement.classList.add('approval-item--rejected');
  }
  if (countdownElement) {
    countdownElement.textContent = 'Rejected after countdown_expired';
  }
  if (approveButton) {
    approveButton.disabled = true;
  }
}

function autoRejectItem(runId) {
  apiFetch('/api/v1/schedule/cancel/' + runId, {
    method: 'POST',
    body: JSON.stringify({ reason: 'countdown_expired' }),
  })
    .then(function() {
      markAsRejected(runId);
      loadUpcoming();
      loadApprovalQueue();
      loadHistory();
    })
    .catch(function() {});
}

function approveItem(runId) {
  apiFetch('/api/v1/schedule/approve/' + runId, { method: 'POST', body: JSON.stringify({}) })
    .then(function() {
      loadUpcoming();
      loadApprovalQueue();
      loadHistory();
    })
    .catch(function() {});
}

function rejectItem(runId) {
  apiFetch('/api/v1/schedule/cancel/' + runId, {
    method: 'POST',
    body: JSON.stringify({ reason: 'user_rejected' }),
  })
    .then(function() {
      markAsRejected(runId);
      loadUpcoming();
      loadApprovalQueue();
      loadHistory();
    })
    .catch(function() {});
}

function loadHistory() {
  Promise.all([
    apiFetch('/api/v1/schedule').then(function(response) { return response.json(); }),
    apiFetch('/api/v1/schedule/roi').then(function(response) { return response.json(); })
  ])
    .then(function(results) {
      const historyData = results[0] || {};
      const roi = results[1] || {};
      const items = historyData.items || historyData.runs || [];
      populateHistoryFilter(items);
      renderHistory(items);
      renderRoiSummary(roi);
    })
    .catch(function() {});
}

function populateHistoryFilter(items) {
  const select = document.getElementById('history-app-filter');
  const currentValue = select.value;
  const appIds = Array.from(new Set(items.map(function(item) {
    return item.app_id || '';
  }).filter(Boolean))).sort();
  const options = ['<option value="">All Apps</option>'];
  appIds.forEach(function(appId) {
    const selected = currentValue === appId ? ' selected' : '';
    options.push('<option value="' + escapeHtml(appId) + '"' + selected + '>' + escapeHtml(appId) + '</option>');
  });
  select.innerHTML = options.join('');
  if (currentValue && appIds.indexOf(currentValue) === -1) {
    select.value = '';
  }
}

function renderHistory(items) {
  const historyElement = document.getElementById('history-list');
  const statusFilter = document.getElementById('history-status-filter').value;
  const appFilter = document.getElementById('history-app-filter').value;
  const filteredItems = items.filter(function(item) {
    if (statusFilter && item.status !== statusFilter) {
      return false;
    }
    if (appFilter && item.app_id !== appFilter) {
      return false;
    }
    return true;
  });
  if (!filteredItems.length) {
    historyElement.innerHTML = emptyState('No activity matches the current filters.');
    return;
  }
  historyElement.innerHTML = filteredItems.map(function(item) {
    return '<article class="history-item">' +
      '<div class="history-item__header">' +
        '<strong>' + escapeHtml(item.app_name || item.app_id || item.action_type || 'Unknown app') + '</strong>' +
        '<span class="status-chip">' + escapeHtml(item.status || 'unknown') + '</span>' +
      '</div>' +
      '<div class="history-item__meta">' + escapeHtml(item.scheduled_at || item.started_at || '') + '</div>' +
      '<div class="history-item__summary">' + escapeHtml(item.output_summary || item.preview_text || 'No summary yet.') + '</div>' +
      '<div class="history-item__evidence">Evidence: ' + escapeHtml(item.evidence_hash || item.evidence_path || 'Pending seal') + '</div>' +
    '</article>';
  }).join('');
}

function renderRoiSummary(roi) {
  document.getElementById('roi-display').innerHTML = '<div class="summary-card">' +
    '<strong>This week: ' + escapeHtml(String(roi.week_hours_saved || '0.00')) + 'h saved</strong>' +
    '<p class="muted-copy">→ $' + escapeHtml(String(roi.week_value_usd_at_30_per_hour || '0.00')) + ' at $30/hr</p>' +
  '</div>';
}

function loadESign() {
  Promise.all([
    apiFetch('/api/v1/esign/pending').then(function(response) { return response.json(); }),
    apiFetch('/api/v1/esign/history').then(function(response) { return response.json(); })
  ])
    .then(function(results) {
      renderESignPending(Array.isArray(results[0]) ? results[0] : []);
      renderESignHistory(Array.isArray(results[1]) ? results[1] : []);
    })
    .catch(function() {});
}

function renderESignPending(items) {
  const element = document.getElementById('esign-pending');
  if (!items.length) {
    element.innerHTML = emptyState('No pending signatures.');
    return;
  }
  element.innerHTML = items.map(function(item) {
    return '<article class="esign-item">' +
      '<div class="esign-item__header">' +
        '<strong>' + escapeHtml(item.preview_text || item.action_type || item.esign_id) + '</strong>' +
        '<span class="status-chip">Pending</span>' +
      '</div>' +
      '<div class="esign-item__status">Requested by ' + escapeHtml(item.requested_by || 'unknown') + ' · Expires ' + escapeHtml(item.expires_at || '') + '</div>' +
      '<button class="btn-primary" type="button" data-esign-id="' + escapeHtml(item.esign_id) + '">Sign</button>' +
    '</article>';
  }).join('');
}

function renderESignHistory(items) {
  const element = document.getElementById('esign-history');
  if (!items.length) {
    element.innerHTML = emptyState('No signature history yet.');
    return;
  }
  element.innerHTML = items.map(function(item) {
    return '<article class="esign-item">' +
      '<div class="esign-item__header">' +
        '<strong>' + escapeHtml(item.action_type || item.esign_id) + '</strong>' +
        '<span class="status-chip">Signed</span>' +
      '</div>' +
      '<div class="esign-item__status">Signed ' + escapeHtml(item.signed_at || '') + ' · By ' + escapeHtml(item.approver || '') + '</div>' +
      '<div class="history-item__evidence">Evidence: ' + escapeHtml(item.evidence_hash || '') + '</div>' +
    '</article>';
  }).join('');
}

function signItem(esignId) {
  const signatureToken = window.prompt('Enter signature token');
  if (!signatureToken) {
    return;
  }
  apiFetch('/api/v1/esign/' + esignId + '/sign', {
    method: 'POST',
    body: JSON.stringify({ signature_token: signatureToken }),
  })
    .then(function() {
      loadUpcoming();
      loadESign();
    })
    .catch(function() {});
}

function openScheduleEditor(appId, appLabel) {
  activeScheduleAppId = appId || 'custom-app';
  activeScheduleAppLabel = appLabel || appId || 'Custom app';
  document.getElementById('drawer-app-label').textContent = 'Editing schedule for ' + activeScheduleAppLabel + '.';
  document.getElementById('schedule-drawer').hidden = false;
}

function closeScheduleEditor() {
  document.getElementById('schedule-drawer').hidden = true;
}

function saveSchedule() {
  const preset = document.getElementById('cron-preset').value;
  const rawCron = document.getElementById('cron-raw').value.trim();
  const cronExpression = preset === 'custom' ? rawCron : CRON_PRESETS[preset];
  if (!cronExpression) {
    return;
  }
  apiFetch('/api/v1/browser/schedules', {
    method: 'POST',
    body: JSON.stringify({
      app_id: activeScheduleAppId || 'custom-app',
      cron: cronExpression,
      url: '',
    }),
  })
    .then(function() {
      closeScheduleEditor();
      loadUpcoming();
    })
    .catch(function() {});
}

document.querySelectorAll('.tab').forEach(function(tabButton) {
  tabButton.addEventListener('click', function() {
    switchTab(tabButton.dataset.tab);
  });
});

document.getElementById('history-status-filter').addEventListener('change', loadHistory);
document.getElementById('history-app-filter').addEventListener('change', loadHistory);
document.getElementById('add-schedule-btn').addEventListener('click', function() {
  openScheduleEditor('custom-app', 'Custom app');
});
document.getElementById('cancel-schedule-btn').addEventListener('click', closeScheduleEditor);
document.getElementById('save-schedule-btn').addEventListener('click', saveSchedule);
document.getElementById('cron-preset').addEventListener('change', function() {
  document.getElementById('cron-raw').hidden = this.value !== 'custom';
});
document.getElementById('request-signature-btn').addEventListener('click', function() {
  window.alert('Signature requests appear here once an app submits them.');
});

document.getElementById('schedules-list').addEventListener('click', function(event) {
  const target = event.target.closest('[data-app-id]');
  if (!target) {
    return;
  }
  openScheduleEditor(target.dataset.appId, target.dataset.appName);
});

document.getElementById('approval-list').addEventListener('click', function(event) {
  const approveTarget = event.target.closest('[data-approve-run-id]');
  const rejectTarget = event.target.closest('[data-reject-run-id]');
  if (approveTarget) {
    approveItem(approveTarget.dataset.approveRunId);
  }
  if (rejectTarget) {
    rejectItem(rejectTarget.dataset.rejectRunId);
  }
});

document.getElementById('esign-pending').addEventListener('click', function(event) {
  const signTarget = event.target.closest('[data-esign-id]');
  if (!signTarget) {
    return;
  }
  signItem(signTarget.dataset.esignId);
});

loadUpcoming();
loadApprovalQueue();
loadHistory();
loadESign();
setInterval(loadUpcoming, 30000);
