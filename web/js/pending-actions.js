/* pending-actions.js — extracted from pending-actions.html */
'use strict';

var ACTIONS_URL = '/api/v1/actions/pending';
var ACTIONS_CONTAINER = document.getElementById('actions-container');
var LAST_REFRESH = document.getElementById('last-refresh');
var STATUS_BANNER = document.getElementById('status-banner');
var HASH_RE = /^[a-f0-9]{64}$/;
var currentActions = new Map();
var busyActions = new Set();

function setStatus(message) {
  STATUS_BANNER.textContent = message || '';
}

function createNode(tagName, className, text) {
  var node = document.createElement(tagName);
  if (className) {
    node.className = className;
  }
  if (typeof text === 'string') {
    node.textContent = text;
  }
  return node;
}

function cooldownEndFor(action) {
  var value = action.cooldown_ends_at || action.available_at || '';
  var timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function isReady(action) {
  return cooldownEndFor(action) <= Date.now();
}

function cooldownText(timestamp) {
  if (!timestamp || timestamp <= Date.now()) {
    return 'Ready';
  }
  var seconds = Math.max(0, Math.ceil((timestamp - Date.now()) / 1000));
  var minutes = Math.floor(seconds / 60);
  var remainder = String(seconds % 60).padStart(2, '0');
  return 'Cooldown: ' + minutes + ':' + remainder;
}

async function sha256Hex(value) {
  var encoded = new TextEncoder().encode(value);
  var digest = await window.crypto.subtle.digest('SHA-256', encoded);
  var bytes = new Uint8Array(digest);
  return Array.from(bytes, function (byte) {
    return byte.toString(16).padStart(2, '0');
  }).join('');
}

async function resolveBearerToken() {
  var storedHash = localStorage.getItem('solace_token_sha256') || '';
  if (HASH_RE.test(storedHash)) {
    return storedHash;
  }
  var rawToken = localStorage.getItem('solace_token') || '';
  if (!rawToken) {
    return '';
  }
  if (HASH_RE.test(rawToken)) {
    return rawToken;
  }
  if (!window.crypto || !window.crypto.subtle) {
    return '';
  }
  return sha256Hex(rawToken);
}

async function apiFetch(path, options) {
  var requestOptions = options || {};
  var headers = Object.assign({}, requestOptions.headers || {});
  var token = await resolveBearerToken();
  if (token) {
    headers.Authorization = 'Bearer ' + token;
  }
  return fetch(path, Object.assign({}, requestOptions, { headers: headers }));
}

function badgeText(actionClass) {
  return actionClass === 'C' ? 'Class C' : 'Class B';
}

function cardClass(actionClass) {
  return actionClass === 'C' ? 'classC' : 'classB';
}

function titleText(action) {
  if (action.title) {
    return String(action.title);
  }
  if (action.action_type) {
    return String(action.action_type);
  }
  return 'Pending Action';
}

function subtitleText(action) {
  var parts = [];
  if (action.app_id) {
    parts.push('App: ' + String(action.app_id));
  }
  if (action.status) {
    parts.push('Status: ' + String(action.status));
  }
  return parts.join(' \u2022 ');
}

function previewText(action) {
  if (action.preview) {
    return String(action.preview);
  }
  if (action.preview_summary) {
    return String(action.preview_summary);
  }
  if (action.description) {
    return String(action.description);
  }
  return 'No preview available.';
}

function renderEmpty(message) {
  ACTIONS_CONTAINER.replaceChildren(createNode('div', 'empty-state', message));
}

function updateCooldowns() {
  document.querySelectorAll('[data-cooldown-at]').forEach(function (node) {
    var timestamp = Number(node.getAttribute('data-cooldown-at') || '0');
    var ready = !timestamp || timestamp <= Date.now();
    node.textContent = cooldownText(timestamp);
    node.classList.toggle('cooldown--ready', ready);
  });

  document.querySelectorAll('[data-approve-id]').forEach(function (button) {
    var actionId = button.getAttribute('data-approve-id') || '';
    var action = currentActions.get(actionId);
    var disabled = !action || !isReady(action) || busyActions.has(actionId);
    button.disabled = disabled;
  });

  document.querySelectorAll('[data-reject-id]').forEach(function (button) {
    var actionId = button.getAttribute('data-reject-id') || '';
    button.disabled = busyActions.has(actionId);
  });
}

function renderActions(actions) {
  currentActions.clear();
  actions.forEach(function (action) {
    currentActions.set(String(action.action_id || ''), action);
  });

  if (!Array.isArray(actions) || actions.length === 0) {
    renderEmpty('\u2705 No pending actions');
    updateCooldowns();
    return;
  }

  var fragment = document.createDocumentFragment();
  actions.forEach(function (action) {
    var actionId = String(action.action_id || '');
    var actionClass = String(action.class || 'B').toUpperCase() === 'C' ? 'C' : 'B';
    var cooldownAt = cooldownEndFor(action);

    var card = createNode('section', 'action-card action-card--' + cardClass(actionClass));
    card.setAttribute('data-action-id', actionId);

    var header = createNode('div', 'action-header');
    var headingWrap = createNode('div', '');
    var heading = createNode('h2', 'action-title', titleText(action));
    var subtitle = createNode('div', 'action-subtitle', subtitleText(action));
    var badge = createNode('span', 'badge badge--' + cardClass(actionClass), badgeText(actionClass));

    headingWrap.appendChild(heading);
    if (subtitle.textContent) {
      headingWrap.appendChild(subtitle);
    }
    header.appendChild(headingWrap);
    header.appendChild(badge);

    var preview = createNode('pre', 'action-preview', previewText(action));

    var footer = createNode('div', 'action-footer');
    var cooldown = createNode('span', 'cooldown', cooldownText(cooldownAt));
    cooldown.setAttribute('data-cooldown-at', String(cooldownAt));
    cooldown.classList.toggle('cooldown--ready', cooldownAt <= Date.now());

    var buttonRow = createNode('div', 'action-buttons');
    var approve = createNode('button', 'btn btn-approve', 'Approve');
    approve.type = 'button';
    approve.setAttribute('data-approve-id', actionId);
    approve.disabled = !isReady(action);

    var reject = createNode('button', 'btn btn-reject', 'Reject');
    reject.type = 'button';
    reject.setAttribute('data-reject-id', actionId);

    buttonRow.appendChild(approve);
    buttonRow.appendChild(reject);
    footer.appendChild(cooldown);
    footer.appendChild(buttonRow);

    card.appendChild(header);
    card.appendChild(preview);
    card.appendChild(footer);
    fragment.appendChild(card);
  });

  ACTIONS_CONTAINER.replaceChildren(fragment);
  updateCooldowns();
}

async function loadActions() {
  try {
    var response = await apiFetch(ACTIONS_URL, { method: 'GET' });
    if (!response.ok) {
      setStatus('Pending actions unavailable right now.');
      return;
    }
    var payload = await response.json();
    var allActions = Array.isArray(payload.pending) ? payload.pending : Array.isArray(payload.actions) ? payload.actions : [];
    var filtered = allActions.filter(function (action) {
      var actionClass = String(action.class || action.risk_class || '').toUpperCase();
      return actionClass === 'B' || actionClass === 'C';
    });
    LAST_REFRESH.textContent = 'Updated ' + new Date().toLocaleTimeString();
    setStatus('');
    renderActions(filtered);
  } catch (_error) {
    setStatus('Failed to refresh pending actions.');
  }
}

async function submitDecision(actionId, decisionPath, payload) {
  busyActions.add(actionId);
  updateCooldowns();
  try {
    var response = await apiFetch(decisionPath, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      var message = 'Action request failed.';
      try {
        var data = await response.json();
        if (data && typeof data.error === 'string' && data.error) {
          message = data.error;
        }
      } catch (_jsonError) {
      }
      setStatus(message);
      return;
    }
    setStatus('Action updated.');
    await loadActions();
  } catch (_error) {
    setStatus('Network error while updating action.');
  } finally {
    busyActions.delete(actionId);
    updateCooldowns();
  }
}

async function approveAction(actionId) {
  var action = currentActions.get(actionId);
  if (!action) {
    return;
  }
  var payload = {};
  if (String(action.class || '').toUpperCase() === 'C') {
    var reason = window.prompt('Class C approval requires a reason. Enter sign-off reason:', 'Reviewed and approved');
    if (reason === null) {
      return;
    }
    var normalized = reason.trim();
    if (!normalized) {
      setStatus('Class C approval needs a reason.');
      return;
    }
    payload.step_up_consent = true;
    payload.reason = normalized;
  }
  await submitDecision(actionId, '/api/v1/actions/' + encodeURIComponent(actionId) + '/approve', payload);
}

async function rejectAction(actionId) {
  var reason = window.prompt('Optional rejection reason:', '');
  if (reason === null) {
    return;
  }
  var payload = {};
  if (reason.trim()) {
    payload.reason = reason.trim();
  }
  await submitDecision(actionId, '/api/v1/actions/' + encodeURIComponent(actionId) + '/reject', payload);
}

ACTIONS_CONTAINER.addEventListener('click', function (event) {
  var target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  var approveId = target.getAttribute('data-approve-id');
  if (approveId) {
    approveAction(approveId);
    return;
  }
  var rejectId = target.getAttribute('data-reject-id');
  if (rejectId) {
    rejectAction(rejectId);
  }
});

loadActions();
window.setInterval(loadActions, 10000);
window.setInterval(updateCooldowns, 1000);
