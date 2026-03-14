// Diagram: 02-dashboard-login
'use strict';

(function () {
  var REFRESH_INTERVAL_MS = 30000;
  var _refreshTimer = null;
  var _bearerToken = null;

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _getBearerToken() {
    if (_bearerToken) {
      return _bearerToken;
    }
    var stored = window.localStorage.getItem('solace_token');
    _bearerToken = stored || null;
    return _bearerToken;
  }

  function _authHeaders() {
    var token = _getBearerToken();
    if (!token) {
      return {};
    }
    return { Authorization: 'Bearer ' + token };
  }

  function _showToast(msg, isError) {
    var el = document.getElementById('toast');
    if (!el) {
      return;
    }
    el.textContent = msg;
    el.style.borderLeftColor = isError ? 'var(--hub-accent)' : 'var(--hub-success)';
    el.hidden = false;
    window.clearTimeout(_showToast._timer);
    _showToast._timer = window.setTimeout(function () {
      el.hidden = true;
    }, 3000);
  }

  function _eventTypeIcon(eventType) {
    var icons = {
      schedule_run: '\u23F0',
      recipe_complete: '\u2705',
      budget_alert: '\u26A0\uFE0F',
      esign_request: '\u270F\uFE0F',
      info: '\u2139\uFE0F',
      warn: '\u26A0\uFE0F',
      error: '\u274C'
    };
    return icons[eventType] || '\uD83D\uDD14';
  }

  function _formatTime(ts) {
    if (!ts) {
      return '';
    }
    var d;
    if (typeof ts === 'number') {
      d = new Date(ts * 1000);
    } else {
      d = new Date(ts);
    }
    if (isNaN(d.getTime())) {
      return String(ts);
    }
    return d.toLocaleString();
  }

  function _renderNotifications(notifs) {
    var listEl = document.getElementById('notif-list');
    var emptyEl = document.getElementById('empty-state');
    if (!listEl) {
      return;
    }

    // Remove existing items (keep empty state)
    var existing = listEl.querySelectorAll('.notif-item');
    for (var i = 0; i < existing.length; i++) {
      existing[i].parentNode.removeChild(existing[i]);
    }

    if (!notifs || notifs.length === 0) {
      if (emptyEl) {
        emptyEl.hidden = false;
      }
      return;
    }

    if (emptyEl) {
      emptyEl.hidden = true;
    }

    // Sort: unread first, then by timestamp descending
    var sorted = notifs.slice().sort(function (a, b) {
      var aRead = a.read || a.is_read || false;
      var bRead = b.read || b.is_read || false;
      if (aRead !== bRead) {
        return aRead ? 1 : -1;
      }
      var aTs = a.timestamp || a.created_at || 0;
      var bTs = b.timestamp || b.created_at || 0;
      if (typeof aTs === 'string') {
        aTs = new Date(aTs).getTime() || 0;
      }
      if (typeof bTs === 'string') {
        bTs = new Date(bTs).getTime() || 0;
      }
      return bTs - aTs;
    });

    for (var j = 0; j < sorted.length; j++) {
      var notif = sorted[j];
      var isRead = notif.read || notif.is_read || false;
      var notifId = notif.id || notif.notification_id || '';
      var title = notif.title || notif.type || 'Notification';
      var body = notif.body || notif.message || '';
      var eventType = notif.event_type || notif.category || notif.type || 'info';
      var ts = notif.created_at || notif.timestamp || '';
      var actionUrl = notif.action_url || null;

      var item = document.createElement('div');
      item.className = 'notif-item' + (isRead ? ' notif-item--read' : ' notif-item--unread');
      item.dataset.notifId = escHtml(notifId);

      var iconEl = document.createElement('div');
      iconEl.className = 'notif-icon';
      iconEl.textContent = _eventTypeIcon(eventType);

      var bodyEl = document.createElement('div');
      bodyEl.className = 'notif-body';

      var titleEl = document.createElement('div');
      titleEl.className = 'notif-title';
      titleEl.textContent = title;

      var msgEl = document.createElement('div');
      msgEl.className = 'notif-message';
      msgEl.textContent = body;

      var metaEl = document.createElement('div');
      metaEl.className = 'notif-meta';

      if (!isRead) {
        var dot = document.createElement('span');
        dot.className = 'notif-unread-dot';
        metaEl.appendChild(dot);
      }

      var timeEl = document.createElement('span');
      timeEl.className = 'notif-time';
      timeEl.textContent = _formatTime(ts);
      metaEl.appendChild(timeEl);

      var typeBadge = document.createElement('span');
      typeBadge.className = 'notif-type-badge';
      typeBadge.textContent = escHtml(eventType);
      metaEl.appendChild(typeBadge);

      bodyEl.appendChild(titleEl);
      bodyEl.appendChild(msgEl);
      bodyEl.appendChild(metaEl);

      if (actionUrl) {
        var actionLink = document.createElement('a');
        actionLink.href = escHtml(actionUrl);
        actionLink.className = 'btn btn--ghost';
        actionLink.style.fontSize = '12px';
        actionLink.style.display = 'inline-block';
        actionLink.style.marginTop = '6px';
        actionLink.textContent = 'View';
        bodyEl.appendChild(actionLink);
      }

      var actionsEl = document.createElement('div');
      actionsEl.className = 'notif-actions';

      if (!isRead && notifId) {
        var markReadBtn = document.createElement('button');
        markReadBtn.className = 'btn-mark-read';
        markReadBtn.type = 'button';
        markReadBtn.textContent = 'Mark read';
        markReadBtn.addEventListener('click', (function (id) {
          return function () {
            _markRead(id);
          };
        })(notifId));
        actionsEl.appendChild(markReadBtn);
      }

      if (notifId) {
        var dismissBtn = document.createElement('button');
        dismissBtn.className = 'btn-dismiss';
        dismissBtn.type = 'button';
        dismissBtn.textContent = 'Dismiss';
        dismissBtn.addEventListener('click', (function (id) {
          return function () {
            _dismiss(id);
          };
        })(notifId));
        actionsEl.appendChild(dismissBtn);
      }

      item.appendChild(iconEl);
      item.appendChild(bodyEl);
      item.appendChild(actionsEl);
      listEl.appendChild(item);
    }
  }

  function _updateBadge(unread) {
    var badge = document.getElementById('unread-badge');
    var label = document.getElementById('count-label');
    if (badge) {
      if (unread > 0) {
        badge.textContent = unread > 99 ? '99+' : String(unread);
        badge.hidden = false;
      } else {
        badge.hidden = true;
      }
    }
    if (label) {
      label.textContent = unread > 0 ? (unread + ' unread') : 'All caught up';
    }
  }

  function _loadNotifications() {
    var headers = _authHeaders();
    fetch('/api/v1/notifications?limit=50', { headers: headers })
      .then(function (resp) {
        if (!resp.ok) {
          return resp.json().then(function (e) { throw new Error(e.error || 'Failed'); });
        }
        return resp.json();
      })
      .then(function (data) {
        var notifs = Array.isArray(data.notifications) ? data.notifications : [];
        var unread = typeof data.unread_count === 'number' ? data.unread_count : 0;
        _renderNotifications(notifs);
        _updateBadge(unread);
      })
      .catch(function () {
        _showToast('Failed to load notifications', true);
      });
  }

  function _markRead(notifId) {
    var headers = Object.assign({ 'Content-Type': 'application/json' }, _authHeaders());
    fetch('/api/v1/notifications/' + encodeURIComponent(notifId) + '/read', {
      method: 'POST',
      headers: headers
    })
      .then(function (resp) {
        if (!resp.ok) {
          return resp.json().then(function (e) { throw new Error(e.error || 'Failed'); });
        }
        return resp.json();
      })
      .then(function () {
        _loadNotifications();
      })
      .catch(function () {
        _showToast('Failed to mark as read', true);
      });
  }

  function _markAllRead() {
    var headers = Object.assign({ 'Content-Type': 'application/json' }, _authHeaders());
    fetch('/api/v1/notifications/mark-all-read', {
      method: 'POST',
      headers: headers
    })
      .then(function (resp) {
        if (!resp.ok) {
          return resp.json().then(function (e) { throw new Error(e.error || 'Failed'); });
        }
        return resp.json();
      })
      .then(function () {
        _showToast('All notifications marked as read', false);
        _loadNotifications();
      })
      .catch(function () {
        _showToast('Failed to mark all as read', true);
      });
  }

  function _dismiss(notifId) {
    var headers = Object.assign({}, _authHeaders());
    fetch('/api/v1/notifications/' + encodeURIComponent(notifId), {
      method: 'DELETE',
      headers: headers
    })
      .then(function (resp) {
        if (!resp.ok) {
          return resp.json().then(function (e) { throw new Error(e.error || 'Failed'); });
        }
        return resp.json();
      })
      .then(function () {
        _showToast('Notification dismissed', false);
        _loadNotifications();
      })
      .catch(function () {
        _showToast('Failed to dismiss notification', true);
      });
  }

  function _startAutoRefresh() {
    if (_refreshTimer) {
      window.clearInterval(_refreshTimer);
    }
    _refreshTimer = window.setInterval(_loadNotifications, REFRESH_INTERVAL_MS);
  }

  function _init() {
    var btnMarkAll = document.getElementById('btn-mark-all-read');
    if (btnMarkAll) {
      btnMarkAll.addEventListener('click', _markAllRead);
    }

    _loadNotifications();
    _startAutoRefresh();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }

  window.SolaceNotifications = {
    refresh: _loadNotifications,
    markAllRead: _markAllRead
  };
}());
