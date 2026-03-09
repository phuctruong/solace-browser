diff --git a/yinyang_server.py b/yinyang_server.py
--- a/yinyang_server.py
+++ b/yinyang_server.py
@@
+import queue
@@ route table
+  POST /api/yinyang/notify             → queue in-memory agent notification (requires auth)
+  GET  /api/yinyang/events             → SSE notification stream (?token=sha256)
+  GET  /api/yinyang/status             → in-memory notification queue status (requires auth)
+  POST /api/yinyang/notifications/{id}/read → mark yinyang notification as read (requires auth)
@@ notification constants
+YINYANG_NOTIFICATION_TYPES: dict[str, str] = {
+    "task_complete": "normal",
+    "task_failed": "high",
+    "task_blocked": "high",
+    "budget_warning": "high",
+    "budget_exhausted": "critical",
+    "app_update": "low",
+    "support_reply": "normal",
+    "milestone": "normal",
+    "system": "low",
+    "celebration": "normal",
+}
+YINYANG_NOTIFICATION_PRIORITIES: frozenset = frozenset(["critical", "high", "normal", "low"])
+YINYANG_SSE_PING_SECONDS = 15
+YINYANG_SSE_RECENT_LIMIT = 10
+_YINYANG_NOTIFICATIONS: list[dict[str, Any]] = []
+_YINYANG_NOTIF_LOCK = threading.Lock()
+_YINYANG_SSE_CLIENTS: list[queue.Queue[str]] = []
+_YINYANG_SSE_CLIENTS_LOCK = threading.Lock()
+_YINYANG_NOTIF_COUNTER = 0
@@ helpers
+def _yinyang_now_iso() -> str:
+def _yinyang_notification_public(notif: dict[str, Any]) -> dict[str, Any]:
+def _yinyang_sse_frame(notif: dict[str, Any]) -> str:
+def _create_yinyang_notification(...):
+def _yinyang_sse_token_valid(expected_sha256: str, token: str) -> bool:
@@ GET routes
+        elif path == "/api/yinyang/status":
+            self._handle_yinyang_status()
+        elif path == "/api/yinyang/events":
+            self._handle_yinyang_events_sse()
+        elif path == "/web/js/notifications-sse.js":
+            self._handle_notifications_sse_js()
+        elif path == "/web/css/notifications.css":
+            self._handle_notifications_css()
@@ POST routes
+        elif path == "/api/yinyang/notify":
+            self._handle_yinyang_notify()
+        elif re.match(r"^/api/yinyang/notifications/[^/]+/read$", path):
+            notif_id = path.split("/")[-2]
+            self._handle_yinyang_mark_read(notif_id)
@@ handler methods
+    def _handle_yinyang_notify(self) -> None:
+    def _handle_yinyang_status(self) -> None:
+    def _handle_yinyang_mark_read(self, notif_id: str) -> None:
+    def _handle_yinyang_events_sse(self) -> None:
+    def _handle_notifications_sse_js(self) -> None:
+    def _handle_notifications_css(self) -> None:
+
+Key behavior added in `yinyang_server.py`:
+- POST `/api/yinyang/notify` validates taxonomy, priority, actions, and metadata, then enqueues an in-memory notification.
+- GET `/api/yinyang/status` returns `queue_depth`, `unread_count`, `notifications`, and `last_checked`.
+- POST `/api/yinyang/notifications/{id}/read` flips `read=true` without touching existing `/api/v1/notifications/*` storage.
+- GET `/api/yinyang/events` authenticates via `?token=<sha256>`, sends immediate unread backlog, streams `id:` + `data:` frames, and emits `: ping` every 15s.
+
+File refs:
+- `yinyang_server.py:210`
+- `yinyang_server.py:3423`
+- `yinyang_server.py:3664`
+- `yinyang_server.py:7673`
+- `yinyang_server.py:9264`
+
+diff --git a/web/js/notifications-sse.js b/web/js/notifications-sse.js
+new file mode 100644
+--- /dev/null
++++ b/web/js/notifications-sse.js
@@
+'use strict';
+
+const SSE_RECONNECT_DELAY_MS = 3000;
+let _sseSource = null;
+let _unreadCount = 0;
+const _seenNotificationIds = new Set();
+
+async function _syncUnreadCount(bearerToken) {
+  const response = await fetch('/api/yinyang/status', {
+    headers: { Authorization: `Bearer ${bearerToken}` }
+  });
+  ...
+}
+
+function connectSSE(bearerToken) {
+  _syncUnreadCount(bearerToken).catch(() => {});
+  _sseSource = new EventSource(`/api/yinyang/events?token=${encodeURIComponent(bearerToken)}`);
+  _sseSource.onmessage = (event) => {
+    ...dedupe by notification id...
+    ...update badge...
+    ...toast high/critical...
+  };
+}
+
+window.SolaceNotificationsSSE = {
+  connectSSE,
+  updateBadge: _updateBadge
+};
+
+File ref:
+- `web/js/notifications-sse.js:1`
+
+diff --git a/web/css/notifications.css b/web/css/notifications.css
+new file mode 100644
+--- /dev/null
++++ b/web/css/notifications.css
@@
+:root {
+  --hub-toast-warning: #f59e0b;
+  --hub-toast-critical: #ef4444;
+  --hub-toast-success: #10b981;
+  --hub-toast-shadow: rgba(0, 0, 0, 0.4);
+  --hub-toast-badge-text: #ffffff;
+}
+
+#toast-container { ... }
+.toast { ... }
+.toast--high { border-left: 3px solid var(--hub-toast-warning); }
+.toast--critical { border-left: 3px solid var(--hub-toast-critical); }
+.notif-badge { ... }
+
+File ref:
+- `web/css/notifications.css:1`
+
+diff --git a/tests/test_notifications_sse.py b/tests/test_notifications_sse.py
+new file mode 100644
+--- /dev/null
++++ b/tests/test_notifications_sse.py
@@
+def test_notify_post_queues_notification(): ...
+def test_notify_requires_auth(): ...
+def test_notify_requires_type(): ...
+def test_notify_requires_message(): ...
+def test_yinyang_status_shows_queue(): ...
+def test_yinyang_status_requires_auth(): ...
+def test_mark_read_updates_read_flag(): ...
+def test_mark_nonexistent_read_404(): ...
+def test_sse_endpoint_returns_event_stream(): ...
+def test_sse_requires_token_param(): ...
+def test_js_file_exists(): ...
+def test_css_file_exists(): ...
+def test_js_no_cdn(): ...
+
+File ref:
+- `tests/test_notifications_sse.py:1`
