// Diagram: 02-dashboard-login
'use strict';

const SSE_RECONNECT_DELAY_MS = 3000;

let _sseSource = null;
let _unreadCount = 0;
const _seenNotificationIds = new Set();

function _getBadgeEl() {
  return document.getElementById('notif-badge');
}

function _getToastContainer() {
  return document.getElementById('toast-container');
}

function _updateBadge(count) {
  _unreadCount = count;
  const badge = _getBadgeEl();
  if (!badge) {
    return;
  }
  badge.textContent = count > 0 ? (count > 99 ? '99+' : String(count)) : '';
  badge.style.display = count > 0 ? 'inline-flex' : 'none';
}

function _notifIcon(type) {
  const icons = {
    task_complete: '✅',
    task_failed: '❌',
    task_blocked: '🚫',
    budget_warning: '⚠️',
    budget_exhausted: '🛑',
    app_update: '🔄',
    support_reply: '💬',
    milestone: '🏆',
    system: 'ℹ️',
    celebration: '🎉'
  };
  return icons[type] || 'ℹ️';
}

function _dispatchAction(action) {
  if (action.url) {
    window.location.assign(action.url);
    return;
  }
  window.dispatchEvent(new CustomEvent('solace:yinyang-action', { detail: action }));
}

function _makeToastAction(action) {
  const button = document.createElement('button');
  button.className = 'toast__action';
  button.type = 'button';
  button.textContent = String(action.label || 'Open');
  button.addEventListener('click', () => _dispatchAction(action));
  return button;
}

function _showToast(notif) {
  const container = _getToastContainer();
  if (!container) {
    return;
  }

  const toast = document.createElement('div');
  toast.className = `toast toast--${notif.priority || 'normal'}`;
  toast.setAttribute('role', 'alert');

  const icon = document.createElement('div');
  icon.className = 'toast__icon';
  icon.textContent = _notifIcon(notif.type);

  const body = document.createElement('div');
  body.className = 'toast__body';

  const message = document.createElement('div');
  message.className = 'toast__message';
  message.textContent = String(notif.message || 'New notification');
  body.appendChild(message);

  const actions = Array.isArray(notif.actions) ? notif.actions : [];
  if (actions.length > 0) {
    const actionsEl = document.createElement('div');
    actionsEl.className = 'toast__actions';
    actions.forEach((action) => {
      if (action && action.label) {
        actionsEl.appendChild(_makeToastAction(action));
      }
    });
    if (actionsEl.childElementCount > 0) {
      body.appendChild(actionsEl);
    }
  }

  const close = document.createElement('button');
  close.className = 'toast__close';
  close.type = 'button';
  close.setAttribute('aria-label', 'Close');
  close.textContent = '×';
  close.addEventListener('click', () => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  });

  toast.appendChild(icon);
  toast.appendChild(body);
  toast.appendChild(close);
  container.appendChild(toast);

  const delay = notif.priority === 'critical' || notif.priority === 'high' ? 10000 : 5000;
  window.setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  }, delay);
}

function _runDelight(notif) {
  if (!window.SolaceDelight || typeof window.SolaceDelight.handleNotificationDelight !== 'function') {
    return;
  }

  window.SolaceDelight.handleNotificationDelight(notif);
}

async function _syncUnreadCount(bearerToken) {
  if (!bearerToken) {
    _updateBadge(0);
    return;
  }
  const response = await fetch('/api/yinyang/status', {
    headers: { Authorization: `Bearer ${bearerToken}` }
  });
  if (!response.ok) {
    return;
  }
  const data = await response.json();
  const notifications = Array.isArray(data.notifications) ? data.notifications : [];
  notifications.forEach((notif) => {
    if (notif && notif.id) {
      _seenNotificationIds.add(notif.id);
    }
  });
  _updateBadge(Number(data.unread_count || 0));
}

function connectSSE(bearerToken) {
  if (!bearerToken || typeof EventSource === 'undefined') {
    return;
  }

  _syncUnreadCount(bearerToken).catch(() => {});

  if (_sseSource) {
    _sseSource.close();
    _sseSource = null;
  }

  const url = `/api/yinyang/events?token=${encodeURIComponent(bearerToken)}`;
  _sseSource = new EventSource(url);

  _sseSource.onmessage = (event) => {
    let notif;
    try {
      notif = JSON.parse(event.data);
    } catch (_error) {
      return;
    }

    if (!notif || !notif.id || _seenNotificationIds.has(notif.id)) {
      return;
    }

    _seenNotificationIds.add(notif.id);
    _updateBadge(_unreadCount + 1);
    _runDelight(notif);
    if (notif.priority === 'high' || notif.priority === 'critical') {
      _showToast(notif);
    }
  };

  _sseSource.onerror = () => {
    if (_sseSource) {
      _sseSource.close();
      _sseSource = null;
    }
    window.setTimeout(() => connectSSE(bearerToken), SSE_RECONNECT_DELAY_MS);
  };
}

window.SolaceNotificationsSSE = {
  connectSSE,
  updateBadge: _updateBadge
};
