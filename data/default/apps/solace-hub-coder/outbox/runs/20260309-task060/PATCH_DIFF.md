diff --git a/tests/test_solace_hub.py b/tests/test_solace_hub.py
index f9d50f43..659233f2 100644
--- a/tests/test_solace_hub.py
+++ b/tests/test_solace_hub.py
@@ -1181,3 +1181,58 @@ class TestEvidenceSearchUI:
     def test_evidence_search_in_server(self):
         server = (REPO_ROOT / "yinyang_server.py").read_text()
         assert "/api/v1/evidence/search" in server
+
+
+# ── Task 060: Schedule Operations 4-Tab Redesign ────────────────────────────
+
+class TestScheduleOperations4TabUI:
+    def test_schedule_html_uses_four_task_tabs(self):
+        html = (REPO_ROOT / "web" / "schedule.html").read_text()
+        assert "Upcoming" in html
+        assert "Approval Queue" in html
+        assert "History" in html
+        assert "eSign" in html
+        assert ">Calendar<" not in html
+        assert ">Kanban<" not in html
+        assert ">Timeline<" not in html
+        assert ">List<" not in html
+
+    def test_schedule_html_no_cdn(self):
+        html = (REPO_ROOT / "web" / "schedule.html").read_text().lower()
+        assert "cdn" not in html
+        assert "bootstrap" not in html
+        assert "tailwind" not in html
+        assert "jquery" not in html
+        assert "https://" not in html
+        assert "http://" not in html
+
+    def test_schedule_js_never_auto_approves(self):
+        js = (REPO_ROOT / "web" / "js" / "schedule.js").read_text()
+        assert "auto-REJECT" in js
+        assert "countdown_expired" in js
+        assert "schedule/cancel/" in js
+        start_idx = js.index("function startCountdown")
+        auto_reject_idx = js.index("function autoRejectItem")
+        countdown_block = js[start_idx:auto_reject_idx]
+        assert "approveItem(" not in countdown_block
+
+    def test_schedule_4tab_css_no_hardcoded_hex(self):
+        import re
+        # Detect hex color values (#abc / #aabbcc) but NOT CSS ID selectors (#kanban-board)
+        _HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}(?:[^0-9a-zA-Z_-]|$)")
+        css_lines = (REPO_ROOT / "web" / "css" / "schedule.css").read_text().splitlines()
+        for line_number, line in enumerate(css_lines, start=1):
+            stripped = line.strip()
+            if not stripped or stripped.startswith("/*"):
+                continue
+            if stripped.startswith("--hub-"):
+                continue
+            assert not _HEX_COLOR_RE.search(line), f"Hardcoded hex color at line {line_number}: {line.strip()}"
+
+    def test_schedule_html_has_cron_presets(self):
+        html = (REPO_ROOT / "web" / "schedule.html").read_text()
+        assert 'value="daily_7am"' in html
+        assert 'value="weekdays_9am"' in html
+        assert 'value="hourly"' in html
+        assert 'value="every_2h"' in html
+        assert 'value="weekly_monday"' in html
diff --git a/tests/test_yinyang_instructions.py b/tests/test_yinyang_instructions.py
index 0ad71992..42b45970 100644
--- a/tests/test_yinyang_instructions.py
+++ b/tests/test_yinyang_instructions.py
@@ -5,6 +5,7 @@ Donald Knuth law: every test is a proof. RED → GREEN gate.
 Port: 18888 (test-only, avoids conflict with production 8888)
 """
 import json
+import os
 import pathlib
 import sys
 import threading
@@ -635,6 +636,80 @@ def _post_no_auth(path: str, payload: dict) -> tuple[int, dict]:
         return exc.code, json.loads(exc.read().decode())
 
 
+def _get_json_with_auth(path: str, token: str = VALID_TOKEN, base: str = AUTH_BASE):
+    req = urllib.request.Request(
+        f"{base}{path}",
+        headers={"Authorization": f"Bearer {token}"},
+        method="GET",
+    )
+    try:
+        with urllib.request.urlopen(req, timeout=5) as resp:
+            return resp.status, json.loads(resp.read().decode())
+    except urllib.error.URLError as exc:
+        assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
+        assert hasattr(exc, "read"), f"Expected readable HTTP error, got: {exc}"
+        return exc.code, json.loads(exc.read().decode())
+
+
+def _schedule_settings_runtime_path(ys) -> pathlib.Path:
+    runtime_dir = ys.PORT_LOCK_PATH.parent
+    if ys.SETTINGS_PATH.parent == runtime_dir:
+        return ys.SETTINGS_PATH
+    return runtime_dir / ys.SETTINGS_PATH.name
+
+
+def _clear_schedule_ops_state(ys) -> None:
+    with ys._PENDING_ACTIONS_LOCK:
+        ys._PENDING_ACTIONS.clear()
+    with ys._ACTIONS_HISTORY_LOCK:
+        ys._ACTIONS_HISTORY.clear()
+    with ys._SESSIONS_LOCK:
+        ys._SESSIONS.clear()
+    if ys.SCHEDULES_PATH.exists():
+        ys.SCHEDULES_PATH.unlink()
+    settings_path = _schedule_settings_runtime_path(ys)
+    if settings_path.exists():
+        settings_path.unlink()
+    audit_dir = ys.PORT_LOCK_PATH.parent / "audit"
+    if audit_dir.exists():
+        for audit_path in audit_dir.glob("*.jsonl"):
+            audit_path.unlink()
+
+
+def _write_schedule_settings(ys, payload: dict) -> pathlib.Path:
+    settings_path = _schedule_settings_runtime_path(ys)
+    settings_path.parent.mkdir(parents=True, exist_ok=True)
+    settings_path.write_text(json.dumps(payload, indent=2))
+    return settings_path
+
+
+def _seed_schedule_action(ys, run_id: str, cooldown_offset_seconds: int) -> None:
+    now_ts = time.time()
+    record = {
+        "action_id": run_id,
+        "action_type": "post_message",
+        "app_id": "linkedin",
+        "created_at": now_ts - 5,
+        "cooldown_ends_at": now_ts + cooldown_offset_seconds,
+        "class": "B",
+        "status": "PENDING_APPROVAL",
+        "preview": {"preview_text": "Publish queued post"},
+        "params": {},
+        "action_hash": f"hash-{run_id}",
+    }
+    with ys._PENDING_ACTIONS_LOCK:
+        ys._PENDING_ACTIONS[run_id] = record
+
+
+@pytest.fixture()
+def schedule_ops_state(auth_server):
+    import yinyang_server as ys
+
+    _clear_schedule_ops_state(ys)
+    yield ys
+    _clear_schedule_ops_state(ys)
+
+
 class TestAuthSecurity:
     def test_get_endpoints_no_auth_required(self, auth_server):
         """GET endpoints must NOT require auth (read-only, safe)."""
@@ -3385,3 +3460,135 @@ class TestHubSummary:
         assert "apps" in data
         assert "schedules" in data
         assert "evidence" in data
+
+
+# ── Task 060: Schedule Operations 4-Tab Redesign ────────────────────────────
+
+class TestScheduleOperations4Tab:
+    def test_upcoming_returns_schedules_and_keepalive(self, auth_server, schedule_ops_state):
+        ys = schedule_ops_state
+        ys.SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
+        ys.SCHEDULES_PATH.write_text(json.dumps([
+            {
+                "id": "sched-1",
+                "app_id": "gmail",
+                "label": "Gmail Inbox",
+                "cron": "0 7 * * *",
+                "next_run_iso": "2026-03-09T07:00:00Z",
+                "countdown_seconds": 120,
+                "enabled": True,
+            }
+        ]))
+        _write_schedule_settings(ys, {
+            "esign_pending": [
+                {
+                    "esign_id": "es-1",
+                    "action_type": "release_signoff",
+                    "requested_by": "qa@solace.local",
+                    "requested_at": "2026-03-09T06:50:00Z",
+                    "expires_at": "2026-03-09T07:20:00Z",
+                    "preview_text": "Approve release package",
+                }
+            ]
+        })
+        _seed_schedule_action(ys, "run-pending", 25)
+        with ys._SESSIONS_LOCK:
+            ys._SESSIONS["sess-1"] = {
+                "url": "https://mail.google.com",
+                "profile": "default",
+                "pid": os.getpid(),
+                "started_at": "2026-03-09T06:40:00Z",
+            }
+
+        status, data = _get_json_with_auth("/api/v1/schedule/upcoming")
+
+        assert status == 200
+        assert data["schedules"][0]["app_id"] == "gmail"
+        assert data["schedules"][0]["cron_human"] == "Every day at 7:00 AM"
+        assert data["keepalive"]["active_count"] == 1
+        assert data["pending_approvals"] == 1
+        assert data["pending_esign"] == 1
+
+    def test_approval_queue_timeout_auto_rejects(self, auth_server, schedule_ops_state):
+        ys = schedule_ops_state
+        _seed_schedule_action(ys, "run-expired", -1)
+
+        status, data = _get_json_with_auth("/api/v1/schedule/queue")
+
+        assert status == 200
+        assert data["count"] == 0
+        with ys._PENDING_ACTIONS_LOCK:
+            record = dict(ys._PENDING_ACTIONS["run-expired"])
+        assert record["status"] == "REJECTED"
+        assert record["reject_reason"] == "countdown_expired"
+        assert (ys.PORT_LOCK_PATH.parent / "audit" / "run-expired.jsonl").exists()
+
+    def test_esign_pending_list(self, auth_server, schedule_ops_state):
+        ys = schedule_ops_state
+        _write_schedule_settings(ys, {
+            "esign_pending": [
+                {
+                    "esign_id": "es-42",
+                    "action_type": "attest_record",
+                    "requested_by": "ops@solace.local",
+                    "requested_at": "2026-03-09T07:00:00Z",
+                    "expires_at": "2026-03-09T07:30:00Z",
+                    "preview_text": "Attest that the run output is accurate",
+                }
+            ]
+        })
+
+        status, data = _get_json_with_auth("/api/v1/esign/pending")
+
+        assert status == 200
+        assert isinstance(data, list)
+        assert data[0]["esign_id"] == "es-42"
+        assert data[0]["requested_by"] == "ops@solace.local"
+
+    def test_esign_sign_creates_evidence(self, auth_server, schedule_ops_state):
+        ys = schedule_ops_state
+        _write_schedule_settings(ys, {
+            "esign_pending": [
+                {
+                    "esign_id": "es-77",
+                    "action_type": "release_signoff",
+                    "requested_by": "ops@solace.local",
+                    "requested_at": "2026-03-09T07:00:00Z",
+                    "expires_at": "2026-03-09T07:30:00Z",
+                    "preview_text": "Sign release evidence bundle",
+                }
+            ],
+            "esign_history": [],
+        })
+
+        status, data = _post_with_auth("/api/v1/esign/es-77/sign", {"signature_token": "token-123", "reason": "approved"})
+        history_status, history = _get_json_with_auth("/api/v1/esign/history")
+
+        assert status == 200
+        assert data["signed"] is True
+        assert data["esign_id"] == "es-77"
+        assert history_status == 200
+        assert isinstance(history, list)
+        assert history[0]["esign_id"] == "es-77"
+        assert history[0]["approver"] == VALID_TOKEN
+        assert history[0]["evidence_hash"].startswith("sha256:")
+
+    def test_approval_queue_never_auto_approves(self, auth_server, schedule_ops_state):
+        ys = schedule_ops_state
+        _seed_schedule_action(ys, "run-never-approve", -1)
+
+        status, data = _post_with_auth("/api/v1/schedule/approve/run-never-approve", {})
+
+        assert status in (400, 409)
+        assert data.get("approved") is not True
+        with ys._PENDING_ACTIONS_LOCK:
+            record = dict(ys._PENDING_ACTIONS["run-never-approve"])
+        assert record["status"] == "REJECTED"
+        assert record["reject_reason"] == "countdown_expired"
+
+    def test_history_roi_uses_decimal(self, auth_server, schedule_ops_state):
+        status, data = _get_json_with_auth("/api/v1/schedule/roi")
+
+        assert status == 200
+        assert isinstance(data["week_hours_saved"], str)
+        assert isinstance(data["week_value_usd_at_30_per_hour"], str)
diff --git a/web/css/schedule.css b/web/css/schedule.css
index 76d8e1a1..a74f1159 100644
--- a/web/css/schedule.css
+++ b/web/css/schedule.css
@@ -1,7 +1,4 @@
-/* schedule.css — Schedule 4-Tab Redesign for Solace Hub
-   Laws: var(--hub-*) tokens ONLY in component rules. Token definitions in :root may contain hex values.
-   No CDN. No Bootstrap. No Tailwind. No jQuery. No hardcoded hex outside :root.
-*/
+/* schedule.css — Schedule Operations 4-tab redesign for Solace Hub */
 
 :root {
   --hub-bg: #1a1a2e;
@@ -12,6 +9,15 @@
   --hub-text-muted: #a8a8b3;
   --hub-success: #4caf50;
   --hub-warning: #ff9800;
+  --space-xs: 4px;
+  --space-sm: 8px;
+  --space-md: 12px;
+  --space-lg: 16px;
+  --space-xl: 20px;
+  --space-2xl: 24px;
+  --radius-sm: 4px;
+  --radius-md: 8px;
+  --radius-lg: 12px;
 }
 
 body {
@@ -22,336 +28,246 @@ body {
 }
 
 .schedule-page {
-  padding: 1rem;
-  max-width: 900px;
+  max-width: 960px;
   margin: 0 auto;
+  padding: var(--space-xl);
 }
 
-.schedule-tabs {
+.roi-strip,
+.pending-counters,
+.approval-item__header,
+.approval-item__actions,
+.section-header,
+.history-item__header,
+.esign-item__header {
   display: flex;
-  gap: 0.5rem;
-  border-bottom: 1px solid var(--hub-border);
-  margin-bottom: 1.5rem;
+  gap: var(--space-md);
 }
 
-.tab {
-  background: none;
-  border: none;
-  color: var(--hub-text-muted);
-  cursor: pointer;
-  padding: 0.75rem 1.25rem;
-  font-size: 0.9rem;
-  border-bottom: 2px solid transparent;
-  position: relative;
-  display: flex;
-  align-items: center;
-  gap: 0.5rem;
+.roi-strip,
+.pending-counters {
+  flex-wrap: wrap;
 }
 
-.tab.active {
-  color: var(--hub-text);
-  border-bottom-color: var(--hub-accent);
+.roi-card,
+.summary-card,
+.counter-card,
+.approval-item,
+.history-item,
+.esign-item,
+.empty-state {
+  background: var(--hub-surface);
+  border: 1px solid var(--hub-border);
+  border-radius: var(--radius-lg);
 }
 
-.tab:hover {
-  color: var(--hub-text);
+.roi-strip {
+  margin-bottom: var(--space-lg);
 }
 
-.badge {
-  background: var(--hub-accent);
-  color: var(--hub-text);
-  font-size: 0.7rem;
-  border-radius: 10px;
-  padding: 0.1rem 0.4rem;
-  min-width: 18px;
-  text-align: center;
+.roi-card,
+.counter-card {
+  flex: 1 1 180px;
+  padding: var(--space-lg);
 }
 
-.tab-panel {
-  display: none;
+.roi-label,
+.muted-copy,
+.approval-item__meta,
+.history-item__meta,
+.history-item__evidence,
+.esign-item__status,
+.schedule-row__cron,
+.schedule-row__countdown,
+.empty-state {
+  color: var(--hub-text-muted);
+  font-size: 14px;
 }
 
-.tab-panel.active {
-  display: block;
+.schedule-tabs {
+  display: flex;
+  gap: var(--space-sm);
+  margin-bottom: var(--space-xl);
+  border-bottom: 1px solid var(--hub-border);
+  padding-bottom: var(--space-sm);
 }
 
-.section {
-  margin-bottom: 2rem;
+.tab {
+  display: inline-flex;
+  align-items: center;
+  gap: var(--space-sm);
+  border: none;
+  border-bottom: 2px solid transparent;
+  background: transparent;
+  color: var(--hub-text-muted);
+  cursor: pointer;
+  padding: var(--space-md) var(--space-lg);
 }
 
-.section h3 {
+.tab.active,
+.tab:hover {
   color: var(--hub-text);
-  margin-bottom: 1rem;
-  font-size: 1rem;
 }
 
-/* Approval item */
-.approval-item {
-  background: var(--hub-surface);
-  border: 1px solid var(--hub-border);
-  border-radius: 8px;
-  padding: 1rem;
-  margin-bottom: 1rem;
+.tab.active {
+  border-bottom-color: var(--hub-accent);
 }
 
-.approval-item__countdown {
-  color: var(--hub-warning);
-  font-size: 0.85rem;
-  margin: 0.5rem 0;
+.badge,
+.status-chip,
+.risk-badge {
+  display: inline-flex;
+  align-items: center;
+  justify-content: center;
+  border-radius: 999px;
+  padding: var(--space-xs) var(--space-sm);
+  font-size: 12px;
 }
 
-.approval-item__actions {
-  display: flex;
-  gap: 0.5rem;
-  margin-top: 0.75rem;
+.badge,
+.risk-badge--C,
+.btn-danger {
+  background: var(--hub-accent);
+  color: var(--hub-text);
 }
 
-/* Buttons */
-.btn-approve {
-  background: var(--hub-success);
-  color: var(--hub-text);
-  border: none;
-  border-radius: 4px;
-  padding: 0.5rem 1rem;
-  cursor: pointer;
+.status-chip,
+.risk-badge--B,
+.counter-card--warning {
+  background: var(--hub-warning);
+  color: var(--hub-bg);
 }
 
-.btn-reject {
-  background: var(--hub-accent);
-  color: var(--hub-text);
-  border: none;
-  border-radius: 4px;
-  padding: 0.5rem 1rem;
-  cursor: pointer;
+.tab-panel {
+  display: block;
 }
 
-.btn-secondary {
-  background: var(--hub-surface);
-  color: var(--hub-text);
-  border: 1px solid var(--hub-border);
-  border-radius: 4px;
-  padding: 0.5rem 1rem;
-  cursor: pointer;
-  margin-top: 1rem;
+.section {
+  margin-bottom: var(--space-2xl);
 }
 
-/* Filter bar */
-.filter-bar {
-  display: flex;
-  gap: 1rem;
-  margin-bottom: 1rem;
+.section-header {
+  align-items: center;
+  justify-content: space-between;
 }
 
-.filter-bar select {
-  background: var(--hub-surface);
-  color: var(--hub-text);
-  border: 1px solid var(--hub-border);
-  border-radius: 4px;
-  padding: 0.4rem;
+.summary-card,
+.approval-item,
+.history-item,
+.esign-item,
+.empty-state,
+.drawer {
+  padding: var(--space-lg);
 }
 
-/* Schedule rows */
 .schedule-row {
+  width: 100%;
   display: flex;
   align-items: center;
-  gap: 1rem;
-  background: var(--hub-surface);
+  justify-content: space-between;
+  gap: var(--space-md);
+  padding: var(--space-lg);
+  margin-bottom: var(--space-sm);
   border: 1px solid var(--hub-border);
-  border-radius: 6px;
-  padding: 0.75rem;
-  margin-bottom: 0.5rem;
+  border-radius: var(--radius-md);
+  background: var(--hub-surface);
+  color: var(--hub-text);
   cursor: pointer;
+  text-align: left;
 }
 
-.schedule-row:hover {
-  border-color: var(--hub-accent);
+.schedule-row__identity,
+.schedule-row__meta,
+.approval-item,
+.history-item,
+.esign-item,
+.drawer {
+  display: flex;
+  flex-direction: column;
+  gap: var(--space-sm);
 }
 
-.schedule-row__cron {
-  color: var(--hub-text-muted);
-  font-size: 0.85rem;
+.schedule-row__meta {
+  align-items: flex-end;
 }
 
-/* Drawer */
-.drawer {
-  position: fixed;
-  top: 0;
-  right: 0;
-  width: 320px;
-  height: 100vh;
-  background: var(--hub-surface);
-  border-left: 1px solid var(--hub-border);
-  padding: 1.5rem;
-  z-index: 100;
+.approval-item--rejected {
+  opacity: 0.7;
 }
 
-.drawer h3 {
-  color: var(--hub-text);
-  margin-bottom: 1.5rem;
+.filter-bar {
+  display: flex;
+  gap: var(--space-md);
+  margin-bottom: var(--space-lg);
 }
 
+.filter-bar select,
 .drawer select,
 .drawer input {
   width: 100%;
+  border: 1px solid var(--hub-border);
+  border-radius: var(--radius-sm);
   background: var(--hub-bg);
   color: var(--hub-text);
-  border: 1px solid var(--hub-border);
-  border-radius: 4px;
-  padding: 0.5rem;
-  margin-bottom: 1rem;
-  box-sizing: border-box;
+  padding: var(--space-md);
 }
 
-/* eSign */
-.esign-item {
+.drawer {
+  position: fixed;
+  top: 0;
+  right: 0;
+  width: min(360px, 100%);
+  height: 100vh;
   background: var(--hub-surface);
-  border: 1px solid var(--hub-border);
-  border-radius: 8px;
-  padding: 1rem;
-  margin-bottom: 0.75rem;
-}
-
-.esign-item__status {
-  font-size: 0.8rem;
-  color: var(--hub-text-muted);
+  border-left: 1px solid var(--hub-border);
+  box-sizing: border-box;
 }
 
-.roi-strip {
-  display: grid;
-  grid-template-columns: repeat(3, minmax(0, 1fr));
-  gap: 0.75rem;
-  margin-bottom: 1rem;
+.drawer-header {
+  margin-bottom: var(--space-md);
 }
 
-.roi-card,
-.calendar-day,
-.kanban-column,
-.timeline-item,
-.signoff-item {
-  background: var(--hub-surface);
+.btn-primary,
+.btn-secondary {
   border: 1px solid var(--hub-border);
-  border-radius: 8px;
-  padding: 0.75rem;
-}
-
-.roi-label,
-.empty-state,
-.calendar-pill,
-.schedule-table th,
-.schedule-table td {
-  font-size: 0.85rem;
-}
-
-.roi-card strong,
-.calendar-day h4,
-.kanban-column h4,
-.timeline-item strong {
-  font-size: 1rem;
-}
-
-.calendar-pills,
-.kanban-column,
-.signoff-sheet,
-.signoff-sheet__header {
-  display: flex;
-  gap: 0.5rem;
-}
-
-.calendar-pills,
-.signoff-sheet {
-  flex-wrap: wrap;
-}
-
-.calendar-pill {
-  display: inline-flex;
-  align-items: center;
-  gap: 0.5rem;
-  padding: 0.25rem 0.5rem;
-  border-radius: 999px;
-  background: var(--hub-bg);
+  border-radius: var(--radius-sm);
+  padding: var(--space-sm) var(--space-lg);
+  cursor: pointer;
   color: var(--hub-text);
 }
 
-.status-success {
-  border-color: var(--hub-success);
-}
-
-.status-cancelled,
-.status-failed {
-  border-color: var(--hub-accent);
-}
-
-.status-pending_approval,
-.status-cooldown {
-  border-color: var(--hub-warning);
-}
-
-.status-scheduled,
-.status-queued {
-  border-color: var(--hub-border);
-}
-
-#kanban-board {
-  display: grid;
-  grid-template-columns: repeat(3, minmax(0, 1fr));
-  gap: 0.75rem;
-  margin-bottom: 1rem;
-}
-
-.kanban-column {
-  flex-direction: column;
-}
-
-.kanban-card {
-  display: flex;
-  justify-content: space-between;
-  gap: 0.5rem;
-  background: var(--hub-bg);
-  border: 1px solid var(--hub-border);
-  border-radius: 8px;
-  padding: 0.5rem;
-}
-
-.timeline-item,
-.signoff-sheet__header {
-  display: flex;
-  justify-content: space-between;
-  align-items: center;
-  margin-bottom: 0.5rem;
+.btn-primary {
+  background: var(--hub-success);
 }
 
-.schedule-table {
-  width: 100%;
-  border-collapse: collapse;
+.btn-secondary,
+.drawer-close {
+  background: var(--hub-surface);
 }
 
-.schedule-table th,
-.schedule-table td {
-  text-align: left;
-  padding: 0.5rem;
-  border-bottom: 1px solid var(--hub-border);
+.btn-primary:disabled {
+  cursor: not-allowed;
+  opacity: 0.5;
 }
 
-.signoff-sheet {
-  position: fixed;
-  left: 1rem;
-  right: 1rem;
-  bottom: 1rem;
-  flex-direction: column;
-  background: var(--hub-surface);
-  border: 1px solid var(--hub-border);
-  border-radius: 12px;
-  padding: 0.75rem;
-  box-shadow: 0 0 0 1px var(--hub-border);
-}
+@media (max-width: 720px) {
+  .schedule-page {
+    padding: var(--space-lg);
+  }
 
-@media (max-width: 375px) {
-  .roi-strip,
-  #kanban-board {
-    grid-template-columns: 1fr;
+  .schedule-tabs,
+  .filter-bar,
+  .schedule-row,
+  .section-header,
+  .approval-item__header,
+  .approval-item__actions,
+  .history-item__header,
+  .esign-item__header {
+    flex-direction: column;
+    align-items: stretch;
   }
 
-  .schedule-tabs {
-    overflow-x: auto;
+  .schedule-row__meta {
+    align-items: flex-start;
   }
 }
diff --git a/web/js/schedule.js b/web/js/schedule.js
index 82c6501f..86b7fbd4 100644
--- a/web/js/schedule.js
+++ b/web/js/schedule.js
@@ -1,8 +1,7 @@
 /**
- * schedule.js — Schedule 4-Tab Redesign for Solace Hub
+ * schedule.js — Schedule Operations 4-tab view for Solace Hub
  * Laws:
  *   - No CDN dependencies. No jQuery. No Bootstrap. No Tailwind.
- *   - Port 8888 ONLY (same origin).
  *   - AUTO_APPROVE_ON_TIMEOUT = BANNED. Countdown = auto-REJECT only.
  *   - Solace Hub only. Legacy name BANNED.
  */
@@ -10,85 +9,142 @@
 'use strict';
 
 const TOKEN = localStorage.getItem('solace_token') || '';
+const CRON_PRESETS = {
+  daily_7am: '0 7 * * *',
+  weekdays_9am: '0 9 * * 1-5',
+  hourly: '0 * * * *',
+  every_2h: '0 */2 * * *',
+  weekly_monday: '0 9 * * 1',
+};
+
+let activeScheduleAppId = '';
+let activeScheduleAppLabel = '';
+const countdowns = {};
 
 function apiFetch(path, opts) {
-  var options = opts || {};
+  const options = opts || {};
   return fetch(path, {
+    method: options.method || 'GET',
     headers: Object.assign(
       { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json' },
       options.headers || {}
     ),
-    method: options.method || 'GET',
     body: options.body || undefined,
   });
 }
 
-// --- Tab switching ---
-document.querySelectorAll('.tab').forEach(function(btn) {
-  btn.addEventListener('click', function() {
-    document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
-    document.querySelectorAll('.tab-panel').forEach(function(p) {
-      p.classList.remove('active');
-      p.hidden = true;
-    });
-    btn.classList.add('active');
-    var panel = document.getElementById('tab-' + btn.dataset.tab);
-    panel.hidden = false;
-    panel.classList.add('active');
-    if (btn.dataset.tab === 'upcoming') { loadUpcoming(); }
-    if (btn.dataset.tab === 'approval') { loadApprovalQueue(); }
-    if (btn.dataset.tab === 'history') { loadHistory(); }
-    if (btn.dataset.tab === 'esign') { loadESign(); }
+function escapeHtml(value) {
+  return String(value || '')
+    .replace(/&/g, '&amp;')
+    .replace(/</g, '&lt;')
+    .replace(/>/g, '&gt;')
+    .replace(/"/g, '&quot;')
+    .replace(/'/g, '&#39;');
+}
+
+function emptyState(message) {
+  return '<div class="empty-state">' + escapeHtml(message) + '</div>';
+}
+
+function fmtSecs(seconds) {
+  const value = Math.max(0, Number(seconds) || 0);
+  if (value < 60) {
+    return value + 's';
+  }
+  if (value < 3600) {
+    return Math.floor(value / 60) + 'm';
+  }
+  return Math.floor(value / 3600) + 'h ' + Math.floor((value % 3600) / 60) + 'm';
+}
+
+function switchTab(tabName) {
+  document.querySelectorAll('.tab').forEach(function(tabButton) {
+    tabButton.classList.toggle('active', tabButton.dataset.tab === tabName);
   });
-});
+  document.querySelectorAll('.tab-panel').forEach(function(panel) {
+    const isActive = panel.id === 'tab-' + tabName;
+    panel.hidden = !isActive;
+    panel.classList.toggle('active', isActive);
+  });
+  if (tabName === 'upcoming') {
+    loadUpcoming();
+  }
+  if (tabName === 'approval') {
+    loadApprovalQueue();
+  }
+  if (tabName === 'history') {
+    loadHistory();
+  }
+  if (tabName === 'esign') {
+    loadESign();
+  }
+}
 
-// --- Tab 1: Upcoming ---
 function loadUpcoming() {
   Promise.all([
-    apiFetch('/api/v1/schedule/upcoming').then(function(r) { return r.json(); }),
-    apiFetch('/api/v1/schedule/calendar').then(function(r) { return r.json(); }),
-    apiFetch('/api/v1/schedule/roi').then(function(r) { return r.json(); })
+    apiFetch('/api/v1/schedule/upcoming').then(function(response) { return response.json(); }),
+    apiFetch('/api/v1/schedule/roi').then(function(response) { return response.json(); })
   ])
     .then(function(results) {
-      var upcoming = results[0] || {};
+      const upcoming = results[0] || {};
+      const roi = results[1] || {};
       renderSchedules(upcoming.schedules || []);
       renderKeepalive(upcoming.keepalive || {});
-      renderPendingCounters(upcoming);
+      renderPendingCounters(upcoming.pending_approvals || 0, upcoming.pending_esign || 0);
       updateApprovalBadge(upcoming.pending_approvals || 0);
-      renderCalendar(results[1] || {});
-      renderRoiStrip(results[2] || {});
+      renderRoiStrip(roi);
     })
     .catch(function() {});
 }
 
 function renderSchedules(schedules) {
-  var el = document.getElementById('schedules-list');
+  const element = document.getElementById('schedules-list');
   if (!schedules.length) {
-    el.innerHTML = '';
+    element.innerHTML = emptyState('No scheduled activity yet.');
     return;
   }
-  el.innerHTML = schedules.map(function(s) {
-    return '<div class="schedule-row" onclick="openScheduleEditor(\'' + s.app_id + '\')">' +
-      '<span>' + (s.app_name || s.app_id) + '</span>' +
-      '<span class="schedule-row__cron">' + (s.cron_human || s.cron) + '</span>' +
-      '<span class="schedule-row__cron">' + (s.countdown_seconds ? 'in ' + fmtSecs(s.countdown_seconds) : '') + '</span>' +
-      '</div>';
+  element.innerHTML = schedules.map(function(schedule) {
+    const countdownLabel = schedule.countdown_seconds ? 'Runs in ' + fmtSecs(schedule.countdown_seconds) : 'Awaiting next run';
+    const enabledLabel = schedule.enabled ? 'Enabled' : 'Disabled';
+    return '<button class="schedule-row" type="button" data-app-id="' + escapeHtml(schedule.app_id) + '" data-app-name="' + escapeHtml(schedule.app_name || schedule.app_id) + '">' +
+      '<span class="schedule-row__identity">' +
+        '<strong>' + escapeHtml(schedule.app_name || schedule.app_id) + '</strong>' +
+        '<span class="schedule-row__cron">' + escapeHtml(schedule.cron_human || schedule.cron || 'Custom schedule') + '</span>' +
+      '</span>' +
+      '<span class="schedule-row__meta">' +
+        '<span class="schedule-row__countdown">' + escapeHtml(countdownLabel) + '</span>' +
+        '<span class="status-chip">' + escapeHtml(enabledLabel) + '</span>' +
+      '</span>' +
+    '</button>';
   }).join('');
 }
 
-function renderCalendar(days) {
-  var el = document.getElementById('calendar-view');
-  var keys = Object.keys(days).sort();
-  if (!keys.length) {
-    el.innerHTML = '<div class="empty-state">No scheduled activity yet.</div>';
+function renderKeepalive(keepalive) {
+  const element = document.getElementById('keepalive-summary');
+  if (keepalive.active_count > 0) {
+    element.innerHTML = '<div class="summary-card">' +
+      '<strong>' + escapeHtml(String(keepalive.active_count)) + ' session(s) protected</strong>' +
+      '<p class="muted-copy">Last refresh ' + escapeHtml(keepalive.last_refresh || 'just now') + ' · next refresh in ' + escapeHtml(fmtSecs(keepalive.next_refresh_seconds || 0)) + '.</p>' +
+    '</div>';
     return;
   }
-  el.innerHTML = keys.map(function(day) {
-    var pills = (days[day] || []).map(function(item) {
-      return '<span class="calendar-pill status-' + item.status + '">' + item.time + ' · ' + item.app + '</span>';
-    }).join('');
-    return '<section class="calendar-day"><h4>' + day + '</h4><div class="calendar-pills">' + pills + '</div></section>';
-  }).join('');
+  element.innerHTML = emptyState('No keep-alive sessions right now.');
+}
+
+function renderPendingCounters(pendingApprovals, pendingESign) {
+  const element = document.getElementById('pending-counters');
+  const cards = [];
+  if (pendingApprovals > 0) {
+    cards.push('<div class="counter-card counter-card--warning"><strong>' + escapeHtml(String(pendingApprovals)) + '</strong><span>Approval Queue</span></div>');
+  }
+  if (pendingESign > 0) {
+    cards.push('<div class="counter-card counter-card--warning"><strong>' + escapeHtml(String(pendingESign)) + '</strong><span>eSign pending</span></div>');
+  }
+  if (!cards.length) {
+    element.innerHTML = emptyState('Everything is clear right now.');
+    return;
+  }
+  element.innerHTML = cards.join('');
 }
 
 function renderRoiStrip(roi) {
@@ -97,265 +153,354 @@ function renderRoiStrip(roi) {
   document.getElementById('roi-value-usd').textContent = '$' + String(roi.week_value_usd_at_30_per_hour || '0.00');
 }
 
-function renderKeepalive(ka) {
-  var el = document.getElementById('keepalive-summary');
-  if (ka.active_count != null) {
-    el.innerHTML = '<p>' + ka.active_count + ' active session(s). Next refresh in ' + fmtSecs(ka.next_refresh_seconds || 0) + '.</p>';
-  } else {
-    el.innerHTML = '<p style="color:var(--hub-text-muted)">No keep-alive sessions.</p>';
-  }
-}
-
-function renderPendingCounters(data) {
-  var el = document.getElementById('pending-counters');
-  var parts = [];
-  if (data.pending_approvals) {
-    parts.push('<span style="color:var(--hub-warning)">' + data.pending_approvals + ' awaiting approval</span>');
-  }
-  if (data.pending_esign) {
-    parts.push('<span style="color:var(--hub-warning)">' + data.pending_esign + ' awaiting eSign</span>');
-  }
-  el.innerHTML = parts.join(' &nbsp;|&nbsp; ') || '';
-}
-
 function updateApprovalBadge(count) {
-  var badge = document.getElementById('approval-badge');
+  const badge = document.getElementById('approval-badge');
   badge.hidden = count === 0;
-  badge.textContent = count;
+  badge.textContent = String(count);
 }
 
-// --- Tab 2: Approval Queue ---
-var _countdowns = {};
-
 function loadApprovalQueue() {
-  Promise.all([
-    apiFetch('/api/v1/schedule/queue').then(function(r) { return r.json(); }),
-    apiFetch('/api/v1/schedule').then(function(r) { return r.json(); })
-  ])
-    .then(function(results) {
-      var queueData = results[0] || {};
-      var scheduleData = results[1] || {};
-      renderApprovalQueue(queueData.queue || []);
-      renderKanban(scheduleData.items || []);
+  apiFetch('/api/v1/schedule/queue')
+    .then(function(response) { return response.json(); })
+    .then(function(data) {
+      renderApprovalQueue(data.queue || []);
+      updateApprovalBadge(data.count || 0);
     })
     .catch(function() {});
 }
 
 function renderApprovalQueue(items) {
-  var el = document.getElementById('approval-list');
-  renderSignoffSheet(items);
-  if (!items.length) { el.innerHTML = ''; return; }
-  el.innerHTML = items.map(function(item) {
-    return '<div class="approval-item" id="approval-' + item.run_id + '">' +
-      '<div><strong>' + item.action_type + '</strong> &mdash; ' + item.app_id + '</div>' +
-      '<div class="approval-item__countdown" id="countdown-' + item.run_id + '">' +
-        item.countdown_seconds_remaining + 's &rarr; auto-REJECT' +
+  const element = document.getElementById('approval-list');
+  Object.keys(countdowns).forEach(function(runId) {
+    clearInterval(countdowns[runId]);
+    delete countdowns[runId];
+  });
+  if (!items.length) {
+    element.innerHTML = emptyState('No approvals waiting for sign-off.');
+    return;
+  }
+  element.innerHTML = items.map(function(item) {
+    const riskTier = escapeHtml(item.class || item.risk_tier || 'B');
+    const approveDisabled = Number(item.countdown_seconds_remaining || 0) > 0 ? ' disabled' : '';
+    return '<article class="approval-item" id="approval-' + escapeHtml(item.run_id) + '">' +
+      '<div class="approval-item__header">' +
+        '<strong>' + escapeHtml(item.preview_text || item.action_type || item.run_id) + '</strong>' +
+        '<span class="risk-badge risk-badge--' + riskTier + '">Risk ' + riskTier + '</span>' +
       '</div>' +
+      '<div class="approval-item__meta">' + escapeHtml(item.app_id || '') + ' · ' + escapeHtml(item.action_type || '') + '</div>' +
+      '<div class="approval-item__countdown" id="countdown-' + escapeHtml(item.run_id) + '">' + escapeHtml(String(item.countdown_seconds_remaining || 0)) + 's → auto-REJECT</div>' +
       '<div class="approval-item__actions">' +
-        '<button class="btn-approve" onclick="approveItem(\'' + item.run_id + '\')">Approve</button>' +
-        '<button class="btn-reject" onclick="rejectItem(\'' + item.run_id + '\')">Reject</button>' +
+        '<button class="btn-primary" type="button" data-approve-run-id="' + escapeHtml(item.run_id) + '"' + approveDisabled + '>Approve</button>' +
+        '<button class="btn-secondary btn-danger" type="button" data-reject-run-id="' + escapeHtml(item.run_id) + '">Reject</button>' +
       '</div>' +
-    '</div>';
+    '</article>';
   }).join('');
   items.forEach(function(item) {
-    startCountdown(item.run_id, item.countdown_seconds_remaining);
-  });
-}
-
-function renderKanban(items) {
-  var board = document.getElementById('kanban-board');
-  var groups = { past: [], pending: [], future: [] };
-  items.forEach(function(item) {
-    if (item.status === 'scheduled' || item.status === 'queued') { groups.future.push(item); return; }
-    if (item.status === 'pending_approval' || item.status === 'cooldown') { groups.pending.push(item); return; }
-    groups.past.push(item);
+    startCountdown(item.run_id, item.countdown_seconds_remaining || 0);
   });
-  board.innerHTML = ['past', 'pending', 'future'].map(function(key) {
-    var title = key === 'past' ? 'Past' : key === 'pending' ? 'Pending' : 'Future';
-    var cards = groups[key].map(function(item) {
-      return '<div class="kanban-card status-' + item.status + '"><strong>' + (item.app_name || item.app_id) + '</strong><span>' + item.status + '</span></div>';
-    }).join('') || '<div class="empty-state">None</div>';
-    return '<section class="kanban-column"><h4>' + title + '</h4>' + cards + '</section>';
-  }).join('');
 }
 
-function renderSignoffSheet(items) {
-  var sheet = document.getElementById('signoff-sheet');
-  var list = document.getElementById('signoff-list');
-  sheet.hidden = items.length === 0;
-  list.innerHTML = items.map(function(item) {
-    return '<div class="signoff-item">' +
-      '<strong>' + item.app_id + '</strong>' +
-      '<div>' + item.action_type + '</div>' +
-      '<div class="approval-item__countdown">' + item.countdown_seconds_remaining + 's → auto-REJECT</div>' +
-    '</div>';
-  }).join('');
+function updateCountdownDisplay(runId, remaining) {
+  const countdownElement = document.getElementById('countdown-' + runId);
+  const approveButton = document.querySelector('[data-approve-run-id="' + runId + '"]');
+  if (countdownElement) {
+    countdownElement.textContent = String(Math.max(0, remaining)) + 's → auto-REJECT';
+  }
+  if (approveButton) {
+    approveButton.disabled = remaining > 0;
+  }
 }
 
-// AUTO-REJECT on countdown = 0. NEVER auto-approve.
 function startCountdown(runId, seconds) {
-  if (_countdowns[runId]) { clearInterval(_countdowns[runId]); }
-  var remaining = seconds;
-  _countdowns[runId] = setInterval(function() {
-    remaining--;
-    var el = document.getElementById('countdown-' + runId);
-    if (el) { el.textContent = remaining + 's \u2192 auto-REJECT'; }
+  if (countdowns[runId]) {
+    clearInterval(countdowns[runId]);
+  }
+  let remaining = Math.max(0, Number(seconds) || 0);
+  updateCountdownDisplay(runId, remaining);
+  if (remaining <= 0) {
+    autoRejectItem(runId);
+    return;
+  }
+  countdowns[runId] = setInterval(function() {
+    remaining -= 1;
+    updateCountdownDisplay(runId, remaining);
     if (remaining <= 0) {
-      clearInterval(_countdowns[runId]);
+      clearInterval(countdowns[runId]);
+      delete countdowns[runId];
       autoRejectItem(runId);
     }
   }, 1000);
 }
 
-async function autoRejectItem(runId) {
-  return rejectItem(runId);
+function markAsRejected(runId) {
+  const approvalElement = document.getElementById('approval-' + runId);
+  const countdownElement = document.getElementById('countdown-' + runId);
+  const approveButton = document.querySelector('[data-approve-run-id="' + runId + '"]');
+  if (approvalElement) {
+    approvalElement.classList.add('approval-item--rejected');
+  }
+  if (countdownElement) {
+    countdownElement.textContent = 'Rejected after countdown_expired';
+  }
+  if (approveButton) {
+    approveButton.disabled = true;
+  }
 }
 
-async function refreshSignoffQueue() {
-  return loadApprovalQueue();
+function autoRejectItem(runId) {
+  apiFetch('/api/v1/schedule/cancel/' + runId, {
+    method: 'POST',
+    body: JSON.stringify({ reason: 'countdown_expired' }),
+  })
+    .then(function() {
+      markAsRejected(runId);
+      loadUpcoming();
+      loadApprovalQueue();
+      loadHistory();
+    })
+    .catch(function() {});
 }
 
 function approveItem(runId) {
-  apiFetch('/api/v1/schedule/approve/' + runId, { method: 'POST' })
-    .then(function() { loadApprovalQueue(); })
+  apiFetch('/api/v1/schedule/approve/' + runId, { method: 'POST', body: JSON.stringify({}) })
+    .then(function() {
+      loadUpcoming();
+      loadApprovalQueue();
+      loadHistory();
+    })
     .catch(function() {});
 }
 
 function rejectItem(runId) {
-  if (_countdowns[runId]) { clearInterval(_countdowns[runId]); }
   apiFetch('/api/v1/schedule/cancel/' + runId, {
     method: 'POST',
     body: JSON.stringify({ reason: 'user_rejected' }),
-  }).then(function() {
-    var el = document.getElementById('approval-' + runId);
-    if (el) { el.remove(); }
-  }).catch(function() {});
+  })
+    .then(function() {
+      markAsRejected(runId);
+      loadUpcoming();
+      loadApprovalQueue();
+      loadHistory();
+    })
+    .catch(function() {});
 }
 
-// --- Tab 3: History ---
 function loadHistory() {
-  apiFetch('/api/v1/schedule')
-    .then(function(r) { return r.json(); })
-    .then(function(data) {
-      renderHistory(data.runs || data.items || []);
-    })
-    .catch(function() {});
-  apiFetch('/api/v1/schedule/roi')
-    .then(function(r) { return r.json(); })
-    .then(function(roi) {
-      document.getElementById('roi-display').innerHTML =
-        '<p>This week: ' + (roi.hours_saved_this_week || roi.week_hours_saved || 0) + 'h saved' +
-        ' \u2192 $' + (roi.value_usd_this_week || roi.week_value_usd_at_30_per_hour || '0.00') + ' at $30/hr</p>';
+  Promise.all([
+    apiFetch('/api/v1/schedule').then(function(response) { return response.json(); }),
+    apiFetch('/api/v1/schedule/roi').then(function(response) { return response.json(); })
+  ])
+    .then(function(results) {
+      const historyData = results[0] || {};
+      const roi = results[1] || {};
+      const items = historyData.items || historyData.runs || [];
+      populateHistoryFilter(items);
+      renderHistory(items);
+      renderRoiSummary(roi);
     })
     .catch(function() {});
 }
 
-function renderHistory(runs) {
-  var timeline = document.getElementById('timeline-view');
-  var el = document.getElementById('history-list');
-  if (!runs.length) {
-    timeline.innerHTML = '<div class="empty-state">No activity yet.</div>';
-    el.innerHTML = '';
+function populateHistoryFilter(items) {
+  const select = document.getElementById('history-app-filter');
+  const currentValue = select.value;
+  const appIds = Array.from(new Set(items.map(function(item) {
+    return item.app_id || '';
+  }).filter(Boolean))).sort();
+  const options = ['<option value="">All Apps</option>'];
+  appIds.forEach(function(appId) {
+    const selected = currentValue === appId ? ' selected' : '';
+    options.push('<option value="' + escapeHtml(appId) + '"' + selected + '>' + escapeHtml(appId) + '</option>');
+  });
+  select.innerHTML = options.join('');
+  if (currentValue && appIds.indexOf(currentValue) === -1) {
+    select.value = '';
+  }
+}
+
+function renderHistory(items) {
+  const historyElement = document.getElementById('history-list');
+  const statusFilter = document.getElementById('history-status-filter').value;
+  const appFilter = document.getElementById('history-app-filter').value;
+  const filteredItems = items.filter(function(item) {
+    if (statusFilter && item.status !== statusFilter) {
+      return false;
+    }
+    if (appFilter && item.app_id !== appFilter) {
+      return false;
+    }
+    return true;
+  });
+  if (!filteredItems.length) {
+    historyElement.innerHTML = emptyState('No activity matches the current filters.');
     return;
   }
-  timeline.innerHTML = runs.map(function(r) {
-    return '<div class="timeline-item">' +
-      '<strong>' + (r.app_id || '') + '</strong>' +
-      '<span>' + (r.status || '') + '</span>' +
-      '<span>' + (r.scheduled_at || r.started_at || '') + '</span>' +
-    '</div>';
+  historyElement.innerHTML = filteredItems.map(function(item) {
+    return '<article class="history-item">' +
+      '<div class="history-item__header">' +
+        '<strong>' + escapeHtml(item.app_name || item.app_id || item.action_type || 'Unknown app') + '</strong>' +
+        '<span class="status-chip">' + escapeHtml(item.status || 'unknown') + '</span>' +
+      '</div>' +
+      '<div class="history-item__meta">' + escapeHtml(item.scheduled_at || item.started_at || '') + '</div>' +
+      '<div class="history-item__summary">' + escapeHtml(item.output_summary || item.preview_text || 'No summary yet.') + '</div>' +
+      '<div class="history-item__evidence">Evidence: ' + escapeHtml(item.evidence_hash || item.evidence_path || 'Pending seal') + '</div>' +
+    '</article>';
   }).join('');
-  el.innerHTML = '';
 }
 
-// --- Tab 4: List ---
+function renderRoiSummary(roi) {
+  document.getElementById('roi-display').innerHTML = '<div class="summary-card">' +
+    '<strong>This week: ' + escapeHtml(String(roi.week_hours_saved || '0.00')) + 'h saved</strong>' +
+    '<p class="muted-copy">→ $' + escapeHtml(String(roi.week_value_usd_at_30_per_hour || '0.00')) + ' at $30/hr</p>' +
+  '</div>';
+}
+
 function loadESign() {
-  apiFetch('/api/v1/schedule')
-    .then(function(r) { return r.json(); })
-    .then(function(data) {
-      renderScheduleList(data.items || []);
+  Promise.all([
+    apiFetch('/api/v1/esign/pending').then(function(response) { return response.json(); }),
+    apiFetch('/api/v1/esign/history').then(function(response) { return response.json(); })
+  ])
+    .then(function(results) {
+      renderESignPending(Array.isArray(results[0]) ? results[0] : []);
+      renderESignHistory(Array.isArray(results[1]) ? results[1] : []);
     })
     .catch(function() {});
 }
 
-function renderScheduleList(items) {
-  var el = document.getElementById('list-view');
-  if (!items.length) {
-    el.innerHTML = '<div class="empty-state">No rows yet.</div>';
-    return;
-  }
-  el.innerHTML = '<table class="schedule-table"><thead><tr><th>App</th><th>Status</th><th>When</th><th>Safety</th></tr></thead><tbody>' + items.map(function(item) {
-    return '<tr><td>' + (item.app_name || item.app_id) + '</td><td>' + item.status + '</td><td>' + (item.scheduled_at || item.started_at || '') + '</td><td>' + (item.safety_tier || '') + '</td></tr>';
-  }).join('') + '</tbody></table>';
-}
-
 function renderESignPending(items) {
-  var el = document.getElementById('esign-pending');
+  const element = document.getElementById('esign-pending');
   if (!items.length) {
-    el.innerHTML = '<p style="color:var(--hub-text-muted)">No pending signatures.</p>';
+    element.innerHTML = emptyState('No pending signatures.');
     return;
   }
-  el.innerHTML = '<h4>Pending Signatures</h4>' + items.map(function(i) {
-    return '<div class="esign-item">' +
-      '<div>' + i.preview_text + '</div>' +
-      '<div class="esign-item__status">Requested by ' + i.requested_by + ' \u2022 Expires ' + i.expires_at + '</div>' +
-      '<button class="btn-approve" onclick="signItem(\'' + i.esign_id + '\')">Sign</button>' +
-    '</div>';
+  element.innerHTML = items.map(function(item) {
+    return '<article class="esign-item">' +
+      '<div class="esign-item__header">' +
+        '<strong>' + escapeHtml(item.preview_text || item.action_type || item.esign_id) + '</strong>' +
+        '<span class="status-chip">Pending</span>' +
+      '</div>' +
+      '<div class="esign-item__status">Requested by ' + escapeHtml(item.requested_by || 'unknown') + ' · Expires ' + escapeHtml(item.expires_at || '') + '</div>' +
+      '<button class="btn-primary" type="button" data-esign-id="' + escapeHtml(item.esign_id) + '">Sign</button>' +
+    '</article>';
   }).join('');
 }
 
 function renderESignHistory(items) {
-  var el = document.getElementById('esign-history');
-  if (!items.length) { el.innerHTML = ''; return; }
-  el.innerHTML = '<h4>Signed History</h4>' + items.map(function(i) {
-    return '<div class="esign-item">' +
-      '<div>' + i.action_type + ' \u2014 Signed ' + i.signed_at + '</div>' +
-      '<div class="esign-item__status">By ' + i.approver + ' | Hash: ' + (i.evidence_hash ? i.evidence_hash.slice(0, 12) : '') + '...</div>' +
-    '</div>';
+  const element = document.getElementById('esign-history');
+  if (!items.length) {
+    element.innerHTML = emptyState('No signature history yet.');
+    return;
+  }
+  element.innerHTML = items.map(function(item) {
+    return '<article class="esign-item">' +
+      '<div class="esign-item__header">' +
+        '<strong>' + escapeHtml(item.action_type || item.esign_id) + '</strong>' +
+        '<span class="status-chip">Signed</span>' +
+      '</div>' +
+      '<div class="esign-item__status">Signed ' + escapeHtml(item.signed_at || '') + ' · By ' + escapeHtml(item.approver || '') + '</div>' +
+      '<div class="history-item__evidence">Evidence: ' + escapeHtml(item.evidence_hash || '') + '</div>' +
+    '</article>';
   }).join('');
 }
 
 function signItem(esignId) {
-  var token = prompt('Enter signature token:');
-  if (!token) { return; }
+  const signatureToken = window.prompt('Enter signature token');
+  if (!signatureToken) {
+    return;
+  }
   apiFetch('/api/v1/esign/' + esignId + '/sign', {
     method: 'POST',
-    body: JSON.stringify({ signature_token: token }),
-  }).then(function() { loadESign(); }).catch(function() {});
+    body: JSON.stringify({ signature_token: signatureToken }),
+  })
+    .then(function() {
+      loadUpcoming();
+      loadESign();
+    })
+    .catch(function() {});
 }
 
-// --- Schedule Editor Drawer ---
-function openScheduleEditor(appId) {
+function openScheduleEditor(appId, appLabel) {
+  activeScheduleAppId = appId || 'custom-app';
+  activeScheduleAppLabel = appLabel || appId || 'Custom app';
+  document.getElementById('drawer-app-label').textContent = 'Editing schedule for ' + activeScheduleAppLabel + '.';
   document.getElementById('schedule-drawer').hidden = false;
 }
 
-document.getElementById('cancel-schedule-btn').addEventListener('click', function() {
+function closeScheduleEditor() {
   document.getElementById('schedule-drawer').hidden = true;
+}
+
+function saveSchedule() {
+  const preset = document.getElementById('cron-preset').value;
+  const rawCron = document.getElementById('cron-raw').value.trim();
+  const cronExpression = preset === 'custom' ? rawCron : CRON_PRESETS[preset];
+  if (!cronExpression) {
+    return;
+  }
+  apiFetch('/api/v1/browser/schedules', {
+    method: 'POST',
+    body: JSON.stringify({
+      app_id: activeScheduleAppId || 'custom-app',
+      cron: cronExpression,
+      url: '',
+    }),
+  })
+    .then(function() {
+      closeScheduleEditor();
+      loadUpcoming();
+    })
+    .catch(function() {});
+}
+
+document.querySelectorAll('.tab').forEach(function(tabButton) {
+  tabButton.addEventListener('click', function() {
+    switchTab(tabButton.dataset.tab);
+  });
 });
 
+document.getElementById('history-status-filter').addEventListener('change', loadHistory);
+document.getElementById('history-app-filter').addEventListener('change', loadHistory);
+document.getElementById('add-schedule-btn').addEventListener('click', function() {
+  openScheduleEditor('custom-app', 'Custom app');
+});
+document.getElementById('cancel-schedule-btn').addEventListener('click', closeScheduleEditor);
+document.getElementById('save-schedule-btn').addEventListener('click', saveSchedule);
 document.getElementById('cron-preset').addEventListener('change', function() {
   document.getElementById('cron-raw').hidden = this.value !== 'custom';
 });
+document.getElementById('request-signature-btn').addEventListener('click', function() {
+  window.alert('Signature requests appear here once an app submits them.');
+});
 
-document.getElementById('bulk-approve-a').addEventListener('click', function() {
-  apiFetch('/api/v1/schedule/queue')
-    .then(function(r) { return r.json(); })
-    .then(function(data) {
-      (data.queue || []).filter(function(item) { return item.class === 'A'; }).forEach(function(item) {
-        approveItem(item.run_id);
-      });
-    })
-    .catch(function() {});
+document.getElementById('schedules-list').addEventListener('click', function(event) {
+  const target = event.target.closest('[data-app-id]');
+  if (!target) {
+    return;
+  }
+  openScheduleEditor(target.dataset.appId, target.dataset.appName);
 });
 
-// --- Utility ---
-function fmtSecs(s) {
-  if (s < 60) { return s + 's'; }
-  if (s < 3600) { return Math.floor(s / 60) + 'm'; }
-  return Math.floor(s / 3600) + 'h ' + Math.floor((s % 3600) / 60) + 'm';
-}
+document.getElementById('approval-list').addEventListener('click', function(event) {
+  const approveTarget = event.target.closest('[data-approve-run-id]');
+  const rejectTarget = event.target.closest('[data-reject-run-id]');
+  if (approveTarget) {
+    approveItem(approveTarget.dataset.approveRunId);
+  }
+  if (rejectTarget) {
+    rejectItem(rejectTarget.dataset.rejectRunId);
+  }
+});
+
+document.getElementById('esign-pending').addEventListener('click', function(event) {
+  const signTarget = event.target.closest('[data-esign-id]');
+  if (!signTarget) {
+    return;
+  }
+  signItem(signTarget.dataset.esignId);
+});
 
-// --- Init ---
 loadUpcoming();
 loadApprovalQueue();
+loadHistory();
+loadESign();
 setInterval(loadUpcoming, 30000);
diff --git a/web/schedule.html b/web/schedule.html
index 23801f3c..b53da274 100644
--- a/web/schedule.html
+++ b/web/schedule.html
@@ -12,39 +12,41 @@
     <div class="roi-card"><span class="roi-label">Time Saved</span><strong id="roi-hours-saved">0.00h</strong></div>
     <div class="roi-card"><span class="roi-label">Value</span><strong id="roi-value-usd">$0.00</strong></div>
   </section>
-  <!-- 4-tab layout -->
-  <nav class="schedule-tabs">
-    <button class="tab active" data-tab="upcoming">Calendar</button>
-    <button class="tab" data-tab="approval">
-      Kanban
+
+  <nav class="schedule-tabs" aria-label="Schedule operations tabs">
+    <button class="tab active" data-tab="upcoming" type="button">Upcoming</button>
+    <button class="tab" data-tab="approval" type="button">
+      Approval Queue
       <span class="badge" id="approval-badge" hidden>0</span>
     </button>
-    <button class="tab" data-tab="history">Timeline</button>
-    <button class="tab" data-tab="esign">List</button>
+    <button class="tab" data-tab="history" type="button">History</button>
+    <button class="tab" data-tab="esign" type="button">eSign</button>
   </nav>
 
-  <!-- Tab 1: Calendar -->
   <div id="tab-upcoming" class="tab-panel active">
     <section class="section">
-      <h3>Agent Activity Calendar</h3>
-      <div id="calendar-view"></div>
-      <div id="schedules-list" hidden></div>
-      <button class="btn-secondary" id="add-schedule-btn">+ Add Schedule</button>
+      <div class="section-header">
+        <h3>App Schedules</h3>
+        <button class="btn-secondary" id="add-schedule-btn" type="button">+ Add Schedule</button>
+      </div>
+      <div id="schedules-list"></div>
     </section>
+
     <section class="section">
-      <h3>Upcoming Runs</h3>
+      <h3>Keep-Alive Sessions</h3>
       <div id="keepalive-summary"></div>
-      <div id="pending-counters"></div>
+    </section>
+
+    <section class="section pending-counters-section">
+      <h3>Needs Attention</h3>
+      <div class="pending-counters" id="pending-counters"></div>
     </section>
   </div>
 
-  <!-- Tab 2: Kanban -->
   <div id="tab-approval" class="tab-panel" hidden>
-    <div id="kanban-board"></div>
     <div id="approval-list"></div>
   </div>
 
-  <!-- Tab 3: Timeline -->
   <div id="tab-history" class="tab-panel" hidden>
     <div class="filter-bar">
       <select id="history-status-filter">
@@ -52,43 +54,43 @@
         <option value="success">Success</option>
         <option value="cancelled">Cancelled</option>
       </select>
-      <select id="history-app-filter"><option value="">All Apps</option></select>
+      <select id="history-app-filter">
+        <option value="">All Apps</option>
+      </select>
     </div>
-    <div id="timeline-view"></div>
     <div id="history-list"></div>
     <div id="roi-display"></div>
   </div>
 
-  <!-- Tab 4: List -->
   <div id="tab-esign" class="tab-panel" hidden>
-    <div id="list-view"></div>
-    <div id="esign-pending"></div>
-    <div id="esign-history"></div>
+    <section class="section">
+      <h3>Pending Signatures</h3>
+      <div id="esign-pending"></div>
+    </section>
+    <section class="section">
+      <h3>Signature History</h3>
+      <div id="esign-history"></div>
+    </section>
+    <button class="btn-secondary" id="request-signature-btn" type="button">Request Signature</button>
   </div>
 
-  <!-- Schedule Editor Drawer -->
-  <div id="schedule-drawer" class="drawer" hidden>
-    <h3>Schedule Editor</h3>
+  <aside id="schedule-drawer" class="drawer" hidden>
+    <div class="section-header drawer-header">
+      <h3>Schedule Editor</h3>
+      <button class="btn-secondary drawer-close" id="cancel-schedule-btn" type="button">Cancel</button>
+    </div>
+    <p class="muted-copy" id="drawer-app-label">Choose an app to schedule.</p>
     <select id="cron-preset">
       <option value="daily_7am">Every day at 7:00 AM</option>
       <option value="weekdays_9am">Weekdays at 9:00 AM</option>
       <option value="hourly">Every hour</option>
       <option value="every_2h">Every 2 hours</option>
-      <option value="weekly_monday">Every Monday at 9:00 AM</option>
+      <option value="weekly_monday">Every Monday</option>
       <option value="custom">Custom (advanced)</option>
     </select>
     <input id="cron-raw" type="text" placeholder="0 7 * * *" hidden>
-    <button id="save-schedule-btn">Save</button>
-    <button id="cancel-schedule-btn">Cancel</button>
-  </div>
-
-  <section id="signoff-sheet" class="signoff-sheet" hidden>
-    <div class="signoff-sheet__header">
-      <strong>I paused and waited for you</strong>
-      <button class="btn-secondary" id="bulk-approve-a">Approve Class A</button>
-    </div>
-    <div id="signoff-list"></div>
-  </section>
+    <button id="save-schedule-btn" class="btn-primary" type="button">Save</button>
+  </aside>
 </div>
 <script src="/web/js/schedule.js"></script>
 </body>
diff --git a/yinyang_server.py b/yinyang_server.py
index 4ff4c76d..62dba80e 100644
--- a/yinyang_server.py
+++ b/yinyang_server.py
@@ -24,7 +24,7 @@ Route table:
   POST /api/v1/evidence                → record evidence event
   POST /api/v1/prime-wiki/snapshot     → capture and store compressed page snapshot
   GET  /api/v1/prime-wiki/snapshot/{id} → snapshot metadata + extracted key elements
-  GET  /api/v1/prime-wiki/snapshot/{id}/content → lazy-load gzip content payload
+  GET  /api/v1/prime-wiki/snapshot/{id}/content → lazy-load PZip content payload
   GET  /api/v1/prime-wiki/diff         → structural diff between two snapshots
   GET  /api/v1/prime-wiki/stats        → local Prime Wiki snapshot stats
   GET  /api/v1/session-rules           → list loaded session rule schemas (requires auth)
@@ -61,6 +61,8 @@ Route table:
   GET  /api/v1/budget/status           → spend vs limit with alert/paused flags
   POST /api/v1/budget                  → update budget settings (requires auth)
   POST /api/v1/budget/reset            → reset to defaults (requires auth)
+  GET  /api/v1/session/stats           → current value dashboard session metrics (requires auth)
+  POST /api/v1/session/stats/reset     → reset value dashboard session metrics (requires auth)
   GET  /api/v1/metrics                 → JSON metrics (uptime, request counts, error rates)
   GET  /metrics                        → Prometheus-format metrics (text/plain; version=0.0.4)
   WS   /ws/dashboard                   → WebSocket: push state updates every 5s, accept ping→pong
@@ -108,10 +110,10 @@ import atexit
 import base64
 import binascii
 import functools
-import gzip
 import hashlib
 import hmac
 import http.server
+import inspect
 import json
 import os
 import random
@@ -155,6 +157,10 @@ EVIDENCE_PATH: Path = Path.home() / ".solace" / "evidence.jsonl"
 PART11_EVIDENCE_DIR: Path = Path.home() / ".solace" / "evidence"
 PART11_EVIDENCE_PATH: Path = PART11_EVIDENCE_DIR / "evidence.jsonl"
 PART11_CHAIN_LOCK_PATH: Path = PART11_EVIDENCE_DIR / "chain.lock"
+DEFAULT_EVIDENCE_PATH: Path = EVIDENCE_PATH
+DEFAULT_PART11_EVIDENCE_DIR: Path = PART11_EVIDENCE_DIR
+DEFAULT_PART11_EVIDENCE_PATH: Path = PART11_EVIDENCE_PATH
+DEFAULT_PART11_CHAIN_LOCK_PATH: Path = PART11_CHAIN_LOCK_PATH
 SCHEDULES_PATH: Path = Path.home() / ".solace" / "schedules.json"
 OAUTH3_TOKENS_PATH: Path = Path.home() / ".solace" / "oauth3-tokens.json"
 OAUTH3_VAULT_PATH: Path = Path.home() / ".solace" / "oauth3-vault.enc"
@@ -214,6 +220,11 @@ PRIME_WIKI_CTA_VERBS: tuple[str, ...] = (
     "save",
     "publish",
 )
+PRIME_WIKI_PZIP_WEB_BINARY: Path = Path("/home/phuc/projects/pzip/native/pzip_web_cpp/build/pzweb")
+PRIME_WIKI_PZIP_WEB_CODEC = "pzweb"
+PRIME_WIKI_PZIP_EMPTY_BINARY: Path = Path("/home/phuc/projects/pzip/native/pzip_logs_cpp/build/pzlog")
+PRIME_WIKI_PZIP_EMPTY_CODEC = "pzlog"
+PRIME_WIKI_PZIP_TIMEOUT_SECONDS = 10
 
 MAX_NOTIFICATIONS = 200  # keep last 200
 NOTIF_CATEGORIES: frozenset = frozenset(["budget", "session", "schedule", "error", "info", "recipe"])
@@ -1009,6 +1020,13 @@ VALID_CRON_PRESETS: dict = {
     "weekly-monday": "0 9 * * 1",
     "every-30min":   "*/30 * * * *",
 }
+SCHEDULE_EDITOR_CRON_PRESETS: dict[str, tuple[str, str]] = {
+    "daily_7am": ("0 7 * * *", "Every day at 7:00 AM"),
+    "weekdays_9am": ("0 9 * * 1-5", "Weekdays at 9:00 AM"),
+    "hourly": ("0 * * * *", "Every hour"),
+    "every_2h": ("0 */2 * * *", "Every 2 hours"),
+    "weekly_monday": ("0 9 * * 1", "Every Monday at 9:00 AM"),
+}
 _SCHEDULER_JOBS: list = []
 _JOB_HISTORY: dict = {}
 _SCHED_LOCK_043 = threading.Lock()
@@ -2016,6 +2034,113 @@ MAX_GEO_EVENTS: int = 100000
 _GEO_EVENTS: list[dict] = []
 _GEO_EVENTS_LOCK = threading.Lock()
 
+# ---------------------------------------------------------------------------
+# Task 168 — iFrame Tracker
+# ---------------------------------------------------------------------------
+IFR_FRAME_TYPES: list[str] = [
+    "embed", "widget", "ad", "payment", "auth", "video", "map", "social", "other",
+]
+IFR_SANDBOX_ATTRS: list[str] = [
+    "allow-scripts", "allow-same-origin", "allow-forms", "allow-popups", "allow-top-navigation",
+]
+MAX_IFRAME_RECORDS: int = 500000
+_IFRAME_RECORDS: list[dict] = []
+_IFRAME_LOCK = threading.Lock()
+
+# ---------------------------------------------------------------------------
+# Task 169 — Push Notification Tracker
+# ---------------------------------------------------------------------------
+PNT_EVENT_TYPES: list[str] = [
+    "subscription_created", "subscription_updated", "subscription_deleted",
+    "permission_granted", "permission_denied", "permission_revoked",
+    "notification_received", "notification_clicked", "notification_dismissed",
+]
+MAX_PUSH_EVENTS: int = 200000
+_PUSH_EVENTS: list[dict] = []
+_PUSH_TRACKER_LOCK = threading.Lock()
+
+# ---------------------------------------------------------------------------
+# Task 170 — Canvas Fingerprint Detector
+# ---------------------------------------------------------------------------
+CFP_TECHNIQUES: list[str] = [
+    "toDataURL", "getImageData", "measureText", "font_enum",
+    "webgl_renderer", "webgl_vendor", "audio_oscillator", "battery_api",
+]
+MAX_FP_DETECTIONS: int = 500000
+_FP_DETECTIONS: list[dict] = []
+_FP_DETECTOR_LOCK = threading.Lock()
+
+# ---------------------------------------------------------------------------
+# Task 171 — Service Worker Tracker
+# ---------------------------------------------------------------------------
+SWR_EVENT_TYPES: list[str] = [
+    "install", "activate", "fetch", "push", "sync", "message", "error", "update", "unregister",
+]
+SWR_STATES: list[str] = ["installing", "installed", "activating", "activated", "redundant"]
+MAX_SW_REGISTRATIONS: int = 100000
+_SW_REGISTRATIONS: list[dict] = []
+_SW_TRACKER_LOCK = threading.Lock()
+
+# ---------------------------------------------------------------------------
+# Task 163 — Storage Quota Monitor
+# ---------------------------------------------------------------------------
+SQM_STORAGE_TYPES: list[str] = [
+    "localStorage", "sessionStorage", "indexedDB", "cacheAPI",
+    "cookies", "serviceWorker", "other",
+]
+SQM_MAX_STORAGE_SNAPSHOTS: int = 50000
+_SQM_STORAGE_SNAPSHOTS: list[dict] = []
+_SQM_STORAGE_LOCK = threading.Lock()
+
+# ---------------------------------------------------------------------------
+# Task 164 — Permission Policy Tracker
+# ---------------------------------------------------------------------------
+PPE_PERMISSION_POLICY_TYPES: list[str] = [
+    "camera", "microphone", "geolocation", "notifications",
+    "clipboard-read", "clipboard-write", "payment", "usb",
+    "bluetooth", "screen-wake-lock", "midi", "other",
+]
+PPE_POLICY_ACTIONS: list[str] = ["allow", "deny", "inherit", "violation"]
+PPE_MAX_POLICY_EVENTS: int = 200000
+_PPE_POLICY_EVENTS: list[dict] = []
+_PPE_POLICY_LOCK = threading.Lock()
+
+# ---------------------------------------------------------------------------
+# Task 165 — Web Vitals Tracker
+# ---------------------------------------------------------------------------
+WVM_WEB_VITAL_METRICS: list[str] = [
+    "LCP", "FID", "CLS", "FCP", "TTFB", "INP", "TBT", "TTI",
+]
+WVM_VITAL_RATINGS: list[str] = ["good", "needs_improvement", "poor"]
+WVM_NAVIGATION_TYPES: list[str] = ["navigate", "reload", "back_forward", "prerender"]
+WVM_MAX_MEASUREMENTS: int = 500000
+_WVM_MEASUREMENTS: list[dict] = []
+_WVM_LOCK = threading.Lock()
+
+# ---------------------------------------------------------------------------
+# Task 166 — Resource Timing Tracker
+# ---------------------------------------------------------------------------
+RTE_RESOURCE_TYPES: list[str] = [
+    "script", "stylesheet", "image", "font", "fetch",
+    "xmlhttprequest", "navigation", "iframe", "other",
+]
+RTE_MAX_RESOURCE_ENTRIES: int = 1000000
+_RTE_RESOURCE_ENTRIES: list[dict] = []
+_RTE_LOCK = threading.Lock()
+
+# ---------------------------------------------------------------------------
+# Task 167 — User Agent Tracker
+# ---------------------------------------------------------------------------
+UAT_UA_PLATFORMS: list[str] = [
+    "Windows", "macOS", "Linux", "Android", "iOS", "ChromeOS", "unknown",
+]
+UAT_UA_BROWSERS: list[str] = [
+    "Chrome", "Firefox", "Safari", "Edge", "Opera", "Brave", "unknown",
+]
+UAT_MAX_SNAPSHOTS: int = 100000
+_UAT_SNAPSHOTS: list[dict] = []
+_UAT_LOCK = threading.Lock()
+
 
 def _triage_single_email(email: dict[str, Any], config: dict[str, bool]) -> dict[str, Any]:
     """Deterministic triage — no LLM required. Returns action + confidence."""
@@ -2056,6 +2181,55 @@ def _utc_isoformat(timestamp: float) -> str:
     return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")
 
 
+def _sha256_text(value: str) -> str:
+    return hashlib.sha256(value.encode("utf-8")).hexdigest()
+
+
+def _decimal_2(value: Any) -> str:
+    return str(Decimal(str(value)).quantize(Decimal("0.01")))
+
+
+def _tracker_sha256(value: Any) -> str:
+    text = str(value).strip()
+    if not text:
+        return ""
+    return hashlib.sha256(text.encode("utf-8")).hexdigest()
+
+
+def _tracker_now_iso() -> str:
+    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
+
+
+def _tracker_decimal_str(value: Any) -> str:
+    return str(Decimal(str(value)).quantize(Decimal("0.00")))
+
+
+def _tracker_parse_non_negative_decimal(value: Any, field_name: str) -> tuple[Optional[Decimal], Optional[str]]:
+    try:
+        decimal_value = Decimal(str(value))
+    except InvalidOperation:
+        return None, f"{field_name} must be a non-negative decimal"
+    if decimal_value < Decimal("0"):
+        return None, f"{field_name} must be a non-negative decimal"
+    return decimal_value, None
+
+
+def _tracker_parse_int(value: Any, field_name: str, minimum: int) -> tuple[Optional[int], Optional[str]]:
+    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
+        if minimum == 0:
+            return None, f"{field_name} must be a non-negative integer"
+        if minimum == 1:
+            return None, f"{field_name} must be an integer >= 1"
+        return None, f"{field_name} must be an integer >= {minimum}"
+    return value, None
+
+
+def _tracker_parse_bool(value: Any, field_name: str) -> tuple[Optional[bool], Optional[str]]:
+    if not isinstance(value, bool):
+        return None, f"{field_name} must be a boolean"
+    return value, None
+
+
 def _call_openrouter_chat(user_message: str, api_key: str) -> tuple[str, str, int, str]:
     """Call OpenRouter with meta-llama/llama-3.3-70b-instruct.
 
@@ -2219,19 +2393,70 @@ _REPORTS_LOCK = threading.Lock()
 # ---------------------------------------------------------------------------
 # Session stats globals — Task 061 (Value Dashboard)
 # ---------------------------------------------------------------------------
-_SESSION_STATS: dict = {
-    "session_id": "",
-    "state": "IDLE",
-    "app_name": None,
-    "pages_visited": 0,
-    "llm_calls": 0,
-    "cost_usd": "0.00",
-    "cost_saved_pct": 0,
-    "duration_seconds": 0,
-    "recipes_replayed": 0,
-    "evidence_captured": 0,
-    "session_start": None,
-}
+_SESSION_STATS_STATES: tuple[str, ...] = (
+    "IDLE",
+    "EXECUTING",
+    "PREVIEW_READY",
+    "BUDGET_CHECK",
+    "DONE",
+    "FAILED",
+)
+_ACTIVE_SESSION_STATS_STATES: frozenset[str] = frozenset((
+    "EXECUTING",
+    "PREVIEW_READY",
+    "BUDGET_CHECK",
+))
+
+
+def _session_stats_started_at_iso(started_at: Optional[float]) -> Optional[str]:
+    if started_at is None:
+        return None
+    return datetime.fromtimestamp(started_at, timezone.utc).isoformat().replace("+00:00", "Z")
+
+
+def _new_session_stats(started_at: Optional[float] = None) -> dict:
+    return {
+        "session_id": str(uuid.uuid4()),
+        "state": "IDLE",
+        "app_name": None,
+        "pages_visited": 0,
+        "llm_calls": 0,
+        "cost_usd": "0.00",
+        "cost_saved_pct": 0,
+        "duration_seconds": 0,
+        "recipes_replayed": 0,
+        "evidence_captured": 0,
+        "session_start": started_at,
+    }
+
+
+def _session_stats_snapshot(now: Optional[float] = None) -> dict:
+    current_time = time.time() if now is None else now
+    with _SESSION_STATS_LOCK:
+        stats = dict(_SESSION_STATS)
+    if not stats.get("session_id"):
+        stats["session_id"] = str(uuid.uuid4())
+    if stats.get("state") not in _SESSION_STATS_STATES:
+        stats["state"] = "IDLE"
+    stats["cost_usd"] = str(stats.get("cost_usd", "0.00"))
+    started_at = stats.get("session_start")
+    if started_at is None:
+        stats["duration_seconds"] = int(stats.get("duration_seconds", 0))
+        stats["session_start"] = None
+        return stats
+    stats["duration_seconds"] = max(0, int(current_time - started_at))
+    stats["session_start"] = _session_stats_started_at_iso(started_at)
+    return stats
+
+
+def _reset_session_stats(now: Optional[float] = None) -> None:
+    started_at = time.time() if now is None else now
+    with _SESSION_STATS_LOCK:
+        _SESSION_STATS.clear()
+        _SESSION_STATS.update(_new_session_stats(started_at))
+
+
+_SESSION_STATS: dict = _new_session_stats()
 _SESSION_STATS_LOCK = threading.Lock()
 
 
@@ -2437,9 +2662,23 @@ def _build_cli_evidence_id(output: str) -> str:
 # ---------------------------------------------------------------------------
 # Evidence storage — append-only JSONL log
 # ---------------------------------------------------------------------------
+def _part11_storage_paths() -> tuple[Path, Path, Path]:
+    if (
+        PART11_EVIDENCE_DIR != DEFAULT_PART11_EVIDENCE_DIR
+        or PART11_EVIDENCE_PATH != DEFAULT_PART11_EVIDENCE_PATH
+        or PART11_CHAIN_LOCK_PATH != DEFAULT_PART11_CHAIN_LOCK_PATH
+    ):
+        return PART11_EVIDENCE_DIR, PART11_EVIDENCE_PATH, PART11_CHAIN_LOCK_PATH
+    if EVIDENCE_PATH != DEFAULT_EVIDENCE_PATH:
+        evidence_dir = EVIDENCE_PATH.parent / "evidence"
+        return evidence_dir, evidence_dir / "evidence.jsonl", evidence_dir / "chain.lock"
+    return PART11_EVIDENCE_DIR, PART11_EVIDENCE_PATH, PART11_CHAIN_LOCK_PATH
+
+
 def _read_part11_chain_tip() -> str:
+    _, _, chain_lock_path = _part11_storage_paths()
     try:
-        lines = PART11_CHAIN_LOCK_PATH.read_text().splitlines()
+        lines = chain_lock_path.read_text().splitlines()
     except IOError:
         return ""
     for line in reversed(lines):
@@ -2450,8 +2689,9 @@ def _read_part11_chain_tip() -> str:
 
 
 def _load_part11_evidence_bundles() -> list[dict]:
+    _, evidence_path, _ = _part11_storage_paths()
     try:
-        lines = PART11_EVIDENCE_PATH.read_text().splitlines()
+        lines = evidence_path.read_text().splitlines()
     except IOError:
         return []
     bundles = []
@@ -2476,6 +2716,7 @@ def create_and_store_evidence_bundle(
     user_id: str,
 ) -> dict:
     with _PART11_EVIDENCE_LOCK:
+        evidence_dir, evidence_path, chain_lock_path = _part11_storage_paths()
         previous_bundle_sha256 = _read_part11_chain_tip() or None
         bundle = ALCOABundle.create_bundle(
             action_type,
@@ -2486,10 +2727,10 @@ def create_and_store_evidence_bundle(
             previous_bundle_sha256=previous_bundle_sha256,
         )
         bundle_sha256 = ALCOABundle.bundle_sha256(bundle)
-        PART11_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
-        with PART11_EVIDENCE_PATH.open("a", encoding="utf-8") as handle:
+        evidence_dir.mkdir(parents=True, exist_ok=True)
+        with evidence_path.open("a", encoding="utf-8") as handle:
             handle.write(json.dumps(bundle, sort_keys=True) + "\n")
-        with PART11_CHAIN_LOCK_PATH.open("a", encoding="utf-8") as handle:
+        with chain_lock_path.open("a", encoding="utf-8") as handle:
             handle.write(f"{bundle_sha256}\n")
     return bundle
 
@@ -2582,6 +2823,14 @@ class OAuth3VaultCorruptError(OAuth3VaultError):
     """Raised when the encrypted OAuth3 vault cannot be parsed or decrypted."""
 
 
+class PZipCompressionError(Exception):
+    """Prime Wiki content compression failed."""
+
+
+class PZipRTCError(PZipCompressionError):
+    """Prime Wiki round-trip verification failed."""
+
+
 def _oauth3_now_iso() -> str:
     return datetime.now(timezone.utc).isoformat()
 
@@ -3058,7 +3307,7 @@ def _prime_wiki_url_hash(normalized_url: str) -> str:
 
 
 def _prime_wiki_storage_dir(url_hash: str) -> Path:
-    return PRIME_WIKI_ROOT / url_hash[:16]
+    return PRIME_WIKI_ROOT / url_hash
 
 
 def _prime_wiki_clean_text(value: str) -> str:
@@ -3250,13 +3499,50 @@ def extract_key_elements(html: str) -> dict:
     }
 
 
-def _compress_prime_wiki_content(content: str) -> tuple[str, str, int, int, float]:
+def _prime_wiki_pzip_binary_and_codec(raw_bytes: bytes) -> tuple[Path, str]:
+    if raw_bytes:
+        return PRIME_WIKI_PZIP_WEB_BINARY, PRIME_WIKI_PZIP_WEB_CODEC
+    return PRIME_WIKI_PZIP_EMPTY_BINARY, PRIME_WIKI_PZIP_EMPTY_CODEC
+
+
+def _run_prime_wiki_pzip(binary_path: Path, mode: str, payload: bytes) -> bytes:
+    try:
+        result = subprocess.run(
+            [str(binary_path), mode, "-"],
+            input=payload,
+            capture_output=True,
+            check=False,
+            timeout=PRIME_WIKI_PZIP_TIMEOUT_SECONDS,
+        )
+    except OSError as exc:
+        raise PZipCompressionError(f"pzweb unavailable: {exc}") from exc
+    except subprocess.TimeoutExpired as exc:
+        raise PZipCompressionError("pzweb timed out") from exc
+    if result.returncode != 0:
+        stderr = result.stderr.decode("utf-8", errors="replace").strip()
+        raise PZipCompressionError(stderr or f"pzweb {mode} failed")
+    return result.stdout
+
+
+def _compress_prime_wiki_content(content: str) -> tuple[str, str, int, int, float, str, bool]:
     raw_bytes = content.encode("utf-8")
-    compressed_bytes = gzip.compress(raw_bytes)
+    binary_path, codec = _prime_wiki_pzip_binary_and_codec(raw_bytes)
+    compressed_bytes = _run_prime_wiki_pzip(binary_path, "compress", raw_bytes)
+    restored_bytes = _run_prime_wiki_pzip(binary_path, "decompress", compressed_bytes)
+    if restored_bytes != raw_bytes:
+        raise PZipRTCError("prime wiki snapshot failed round-trip verification")
     compressed_b64 = base64.b64encode(compressed_bytes).decode("ascii")
     sha256_value = hashlib.sha256(raw_bytes).hexdigest()
     compression_ratio = round(len(raw_bytes) / max(len(compressed_bytes), 1), 3)
-    return compressed_b64, sha256_value, len(raw_bytes), len(compressed_bytes), compression_ratio
+    return (
+        compressed_b64,
+        sha256_value,
+        len(raw_bytes),
+        len(compressed_bytes),
+        compression_ratio,
+        codec,
+        True,
+    )
 
 
 def _prime_wiki_snapshot_filename(snapshot_type: str, captured_at: str, snapshot_id: str) -> str:
@@ -3269,6 +3555,7 @@ def _prime_wiki_snapshot_filename(snapshot_type: str, captured_at: str, snapshot
 def _prime_wiki_public_record(record: dict) -> dict:
     public_record = dict(record)
     public_record.pop("content_gzip_b64", None)
+    public_record.pop("content_pzip_b64", None)
     public_record.pop("storage_path", None)
     return public_record
 
@@ -3283,18 +3570,26 @@ def _prime_wiki_snapshot_record(
     normalized_url = _normalize_prime_wiki_url(url)
     captured_at = _prime_wiki_timestamp()
     snapshot_id = str(uuid.uuid4())
-    compressed_b64, sha256_value, size_bytes, compressed_size_bytes, compression_ratio = (
-        _compress_prime_wiki_content(content_html)
-    )
+    (
+        compressed_b64,
+        sha256_value,
+        size_bytes,
+        compressed_size_bytes,
+        compression_ratio,
+        codec,
+        rtc_verified,
+    ) = _compress_prime_wiki_content(content_html)
     return {
         "snapshot_id": snapshot_id,
         "url_hash": _prime_wiki_url_hash(normalized_url),
         "url": normalized_url,
         "domain": urllib.parse.urlsplit(normalized_url).netloc.lower(),
         "snapshot_type": snapshot_type,
-        "content_gzip_b64": compressed_b64,
+        "content_pzip_b64": compressed_b64,
         "key_elements": extract_key_elements(content_html),
         "compression_ratio": compression_ratio,
+        "codec": codec,
+        "rtc_verified": rtc_verified,
         "captured_at": captured_at,
         "captured_at_ts": time.time(),
         "app_id": app_id,
@@ -5062,6 +5357,25 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             return False
         return True
 
+    def _require_auth(self) -> bool:
+        return self._check_auth()
+
+    def _send_json_compat(self, status: int, body: dict[str, Any]) -> None:
+        param_names = list(inspect.signature(self._send_json).parameters)
+        if len(param_names) >= 2 and param_names[0] in {"code", "status", "response_code"}:
+            self._send_json(status, body)
+            return
+        self._send_json(body, status)
+
+    def _tracker_body(self, payload: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
+        body = payload if payload is not None else self._read_json_body()
+        if body is None:
+            return None
+        if not isinstance(body, dict):
+            self._send_json_compat(400, {"error": "body must be a JSON object"})
+            return None
+        return body
+
     # --- GET routing ---
     def do_GET(self) -> None:
         path = self.path.split("?")[0]
@@ -5237,7 +5551,7 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         elif path == "/api/v1/sync/status":
             self._handle_sync_status()
         elif path == "/api/v1/recipes":
-            self._handle_recipes_list()
+            self._handle_recipes_list(query)
         elif path == "/api/v1/recipes/my-library":
             self._handle_community_recipes_my_library()
         elif path == "/api/v1/recipes/templates":
@@ -6520,7 +6834,7 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_visit_list()
         # --- Task 113: Storage Quota Monitor ---
         elif path == "/api/v1/storage-quota/storage-types":
-            self._handle_quota_storage_types()
+            self._handle_storage_quota_types()
         elif path == "/api/v1/storage-quota/measurements/latest":
             self._handle_quota_latest()
         elif path == "/api/v1/storage-quota/measurements":
@@ -7174,6 +7488,123 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_static_file("web/js/geolocation-tracker.js", "application/javascript")
         elif path == "/web/css/geolocation-tracker.css":
             self._handle_static_file("web/css/geolocation-tracker.css", "text/css")
+        # --- Task 168: iFrame Tracker ---
+        elif path == "/api/v1/iframe-tracker/frame-types":
+            self._handle_iframe_tracker_frame_types()
+        elif path == "/api/v1/iframe-tracker/frames":
+            self._handle_iframe_tracker_list()
+        elif path == "/api/v1/iframe-tracker/stats":
+            self._handle_iframe_tracker_stats()
+        elif path == "/web/iframe-tracker.html":
+            self._handle_static_file("web/iframe-tracker.html", "text/html; charset=utf-8")
+        elif path == "/web/js/iframe-tracker.js":
+            self._handle_static_file("web/js/iframe-tracker.js", "application/javascript")
+        elif path == "/web/css/iframe-tracker.css":
+            self._handle_static_file("web/css/iframe-tracker.css", "text/css")
+        # --- Task 169: Push Notification Tracker ---
+        elif path == "/api/v1/push-tracker/event-types":
+            self._handle_push_notification_tracker_event_types()
+        elif path == "/api/v1/push-tracker/events":
+            self._handle_push_notification_tracker_list()
+        elif path == "/api/v1/push-tracker/stats":
+            self._handle_push_notification_tracker_stats()
+        elif path == "/web/push-notification-tracker.html":
+            self._handle_static_file("web/push-notification-tracker.html", "text/html; charset=utf-8")
+        elif path == "/web/js/push-notification-tracker.js":
+            self._handle_static_file("web/js/push-notification-tracker.js", "application/javascript")
+        elif path == "/web/css/push-notification-tracker.css":
+            self._handle_static_file("web/css/push-notification-tracker.css", "text/css")
+        # --- Task 170: Canvas Fingerprint Detector ---
+        elif path == "/api/v1/canvas-fp/techniques":
+            self._handle_canvas_fingerprint_detector_techniques()
+        elif path == "/api/v1/canvas-fp/detections":
+            self._handle_canvas_fingerprint_detector_list()
+        elif path == "/api/v1/canvas-fp/stats":
+            self._handle_canvas_fingerprint_detector_stats()
+        elif path == "/web/canvas-fingerprint-detector.html":
+            self._handle_static_file("web/canvas-fingerprint-detector.html", "text/html; charset=utf-8")
+        elif path == "/web/js/canvas-fingerprint-detector.js":
+            self._handle_static_file("web/js/canvas-fingerprint-detector.js", "application/javascript")
+        elif path == "/web/css/canvas-fingerprint-detector.css":
+            self._handle_static_file("web/css/canvas-fingerprint-detector.css", "text/css")
+        # --- Task 171: Service Worker Tracker ---
+        elif path == "/api/v1/sw-tracker/sw-events":
+            self._handle_service_worker_tracker_sw_events()
+        elif path == "/api/v1/sw-tracker/registrations":
+            self._handle_service_worker_tracker_list()
+        elif path == "/api/v1/sw-tracker/stats":
+            self._handle_service_worker_tracker_stats()
+        elif path == "/web/service-worker-tracker.html":
+            self._handle_static_file("web/service-worker-tracker.html", "text/html; charset=utf-8")
+        elif path == "/web/js/service-worker-tracker.js":
+            self._handle_static_file("web/js/service-worker-tracker.js", "application/javascript")
+        elif path == "/web/css/service-worker-tracker.css":
+            self._handle_static_file("web/css/service-worker-tracker.css", "text/css")
+        # --- Task 163: Storage Quota Monitor ---
+        elif path == "/api/v1/storage-quota/storage-types":
+            self._handle_storage_quota_types()
+        elif path == "/api/v1/storage-quota/snapshots":
+            self._handle_storage_quota_list()
+        elif path == "/api/v1/storage-quota/stats":
+            self._handle_storage_quota_stats()
+        elif path == "/web/storage-quota-monitor.html":
+            self._handle_static_file("web/storage-quota-monitor.html", "text/html; charset=utf-8")
+        elif path == "/web/js/storage-quota-monitor.js":
+            self._handle_static_file("web/js/storage-quota-monitor.js", "application/javascript")
+        elif path == "/web/css/storage-quota-monitor.css":
+            self._handle_static_file("web/css/storage-quota-monitor.css", "text/css")
+        # --- Task 164: Permission Policy Tracker ---
+        elif path == "/api/v1/permission-policy/policy-types":
+            self._handle_permission_policy_types()
+        elif path == "/api/v1/permission-policy/events":
+            self._handle_permission_policy_list()
+        elif path == "/api/v1/permission-policy/stats":
+            self._handle_permission_policy_stats()
+        elif path == "/web/permission-policy-tracker.html":
+            self._handle_static_file("web/permission-policy-tracker.html", "text/html; charset=utf-8")
+        elif path == "/web/js/permission-policy-tracker.js":
+            self._handle_static_file("web/js/permission-policy-tracker.js", "application/javascript")
+        elif path == "/web/css/permission-policy-tracker.css":
+            self._handle_static_file("web/css/permission-policy-tracker.css", "text/css")
+        # --- Task 165: Web Vitals Tracker ---
+        elif path == "/api/v1/web-vitals/metric-types":
+            self._handle_web_vitals_metric_types()
+        elif path == "/api/v1/web-vitals/measurements":
+            self._handle_web_vitals_list()
+        elif path == "/api/v1/web-vitals/stats":
+            self._handle_web_vitals_stats()
+        elif path == "/web/web-vitals-tracker.html":
+            self._handle_static_file("web/web-vitals-tracker.html", "text/html; charset=utf-8")
+        elif path == "/web/js/web-vitals-tracker.js":
+            self._handle_static_file("web/js/web-vitals-tracker.js", "application/javascript")
+        elif path == "/web/css/web-vitals-tracker.css":
+            self._handle_static_file("web/css/web-vitals-tracker.css", "text/css")
+        # --- Task 166: Resource Timing Tracker ---
+        elif path == "/api/v1/resource-timing/resource-types":
+            self._handle_resource_timing_types()
+        elif path == "/api/v1/resource-timing/entries":
+            self._handle_resource_timing_list()
+        elif path == "/api/v1/resource-timing/stats":
+            self._handle_resource_timing_stats()
+        elif path == "/web/resource-timing-tracker.html":
+            self._handle_static_file("web/resource-timing-tracker.html", "text/html; charset=utf-8")
+        elif path == "/web/js/resource-timing-tracker.js":
+            self._handle_static_file("web/js/resource-timing-tracker.js", "application/javascript")
+        elif path == "/web/css/resource-timing-tracker.css":
+            self._handle_static_file("web/css/resource-timing-tracker.css", "text/css")
+        # --- Task 167: User Agent Tracker ---
+        elif path == "/api/v1/user-agent/platforms":
+            self._handle_user_agent_platforms()
+        elif path == "/api/v1/user-agent/snapshots":
+            self._handle_user_agent_list()
+        elif path == "/api/v1/user-agent/stats":
+            self._handle_user_agent_stats()
+        elif path == "/web/user-agent-tracker.html":
+            self._handle_static_file("web/user-agent-tracker.html", "text/html; charset=utf-8")
+        elif path == "/web/js/user-agent-tracker.js":
+            self._handle_static_file("web/js/user-agent-tracker.js", "application/javascript")
+        elif path == "/web/css/user-agent-tracker.css":
+            self._handle_static_file("web/css/user-agent-tracker.css", "text/css")
         else:
             self._send_json({"error": "not found"}, 404)
 
@@ -7979,6 +8410,33 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         # --- Task 162: Geolocation Tracker ---
         elif path == "/api/v1/geo-tracker/events":
             self._handle_geo_event_create()
+        # --- Task 168: iFrame Tracker ---
+        elif path == "/api/v1/iframe-tracker/frames":
+            self._handle_iframe_tracker_create()
+        # --- Task 169: Push Notification Tracker ---
+        elif path == "/api/v1/push-tracker/events":
+            self._handle_push_notification_tracker_create()
+        # --- Task 170: Canvas Fingerprint Detector ---
+        elif path == "/api/v1/canvas-fp/detections":
+            self._handle_canvas_fingerprint_detector_create()
+        # --- Task 171: Service Worker Tracker ---
+        elif path == "/api/v1/sw-tracker/registrations":
+            self._handle_service_worker_tracker_create()
+        # --- Task 163: Storage Quota Monitor ---
+        elif path == "/api/v1/storage-quota/snapshots":
+            self._handle_storage_quota_create()
+        # --- Task 164: Permission Policy Tracker ---
+        elif path == "/api/v1/permission-policy/events":
+            self._handle_permission_policy_create()
+        # --- Task 165: Web Vitals Tracker ---
+        elif path == "/api/v1/web-vitals/measurements":
+            self._handle_web_vitals_create()
+        # --- Task 166: Resource Timing Tracker ---
+        elif path == "/api/v1/resource-timing/entries":
+            self._handle_resource_timing_create()
+        # --- Task 167: User Agent Tracker ---
+        elif path == "/api/v1/user-agent/snapshots":
+            self._handle_user_agent_create()
         else:
             self._send_json({"error": "not found"}, 404)
 
@@ -8518,6 +8976,42 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         elif re.match(r"^/api/v1/geo-tracker/events/[^/]+$", path):
             event_id = path.split("/")[-1]
             self._handle_geo_event_delete(event_id)
+        # --- Task 168: iFrame Tracker ---
+        elif re.match(r"^/api/v1/iframe-tracker/frames/[^/]+$", path):
+            frame_id = path.split("/")[-1]
+            self._handle_iframe_tracker_delete(frame_id)
+        # --- Task 169: Push Notification Tracker ---
+        elif re.match(r"^/api/v1/push-tracker/events/[^/]+$", path):
+            event_id = path.split("/")[-1]
+            self._handle_push_notification_tracker_delete(event_id)
+        # --- Task 170: Canvas Fingerprint Detector ---
+        elif re.match(r"^/api/v1/canvas-fp/detections/[^/]+$", path):
+            detection_id = path.split("/")[-1]
+            self._handle_canvas_fingerprint_detector_delete(detection_id)
+        # --- Task 171: Service Worker Tracker ---
+        elif re.match(r"^/api/v1/sw-tracker/registrations/[^/]+$", path):
+            reg_id = path.split("/")[-1]
+            self._handle_service_worker_tracker_delete(reg_id)
+        # --- Task 163: Storage Quota Monitor ---
+        elif re.match(r"^/api/v1/storage-quota/snapshots/[^/]+$", path):
+            snapshot_id = path.split("/")[-1]
+            self._handle_storage_quota_delete(snapshot_id)
+        # --- Task 164: Permission Policy Tracker ---
+        elif re.match(r"^/api/v1/permission-policy/events/[^/]+$", path):
+            event_id = path.split("/")[-1]
+            self._handle_permission_policy_delete(event_id)
+        # --- Task 165: Web Vitals Tracker ---
+        elif re.match(r"^/api/v1/web-vitals/measurements/[^/]+$", path):
+            measurement_id = path.split("/")[-1]
+            self._handle_web_vitals_delete(measurement_id)
+        # --- Task 166: Resource Timing Tracker ---
+        elif re.match(r"^/api/v1/resource-timing/entries/[^/]+$", path):
+            entry_id = path.split("/")[-1]
+            self._handle_resource_timing_delete(entry_id)
+        # --- Task 167: User Agent Tracker ---
+        elif re.match(r"^/api/v1/user-agent/snapshots/[^/]+$", path):
+            snapshot_id = path.split("/")[-1]
+            self._handle_user_agent_delete(snapshot_id)
         else:
             self._send_json({"error": "not found"}, 404)
 
@@ -8730,13 +9224,21 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._send_json({"error": "invalid content_html"}, 400)
             return
 
-        snapshot_record = _prime_wiki_snapshot_record(
-            normalized_url,
-            content_html,
-            snapshot_type,
-            app_id,
-            action_id,
-        )
+        try:
+            snapshot_record = _prime_wiki_snapshot_record(
+                normalized_url,
+                content_html,
+                snapshot_type,
+                app_id,
+                action_id,
+            )
+        except PZipRTCError:
+            self._send_json({"error": "snapshot rtc verification failed"}, 500)
+            return
+        except PZipCompressionError:
+            self._send_json({"error": "failed to compress snapshot"}, 500)
+            return
+
         try:
             _store_prime_wiki_snapshot(snapshot_record)
         except OSError:
@@ -8760,6 +9262,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
                 "url_hash": snapshot_record["url_hash"],
                 "sha256": snapshot_record["sha256"],
                 "compression_ratio": snapshot_record["compression_ratio"],
+                "codec": snapshot_record["codec"],
+                "rtc_verified": snapshot_record["rtc_verified"],
                 "key_elements": snapshot_record["key_elements"],
                 "cloud_sync_started": cloud_sync_started,
             },
@@ -8780,9 +9284,11 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             return
         self._send_json(
             {
-                "content_gzip_b64": snapshot_record.get("content_gzip_b64", ""),
+                "content_pzip_b64": snapshot_record.get("content_pzip_b64", ""),
                 "sha256": snapshot_record.get("sha256", ""),
                 "size_bytes": snapshot_record.get("size_bytes", 0),
+                "codec": snapshot_record.get("codec", ""),
+                "rtc_verified": snapshot_record.get("rtc_verified", False),
             }
         )
 
@@ -10801,36 +11307,26 @@ function choose(mode) {
                     return json.loads(recipe_file.read_text())
                 except json.JSONDecodeError:
                     return None
+        task059_root = COMMUNITY_RECIPES_059_PATH.parent / "apps"
+        if task059_root.exists():
+            for recipe_file in sorted(task059_root.glob(f"*/recipes/{recipe_id}.json")):
+                try:
+                    return json.loads(recipe_file.read_text())
+                except json.JSONDecodeError:
+                    return None
         return None
 
-    def _handle_recipes_list(self) -> None:
-        recipes = []
-        seen: set = set()
-        for search_path in [RECIPES_DIR, Path.home() / ".solace" / "recipes"]:
-            if search_path.exists():
-                for f in sorted(search_path.glob("*.json")):
-                    if f.stem in seen:
-                        continue
-                    seen.add(f.stem)
-                    try:
-                        r = json.loads(f.read_text())
-                        recipes.append({
-                            "id": r.get("id", f.stem),
-                            "name": r.get("name", f.stem),
-                            "description": r.get("description", ""),
-                            "cost_estimate": r.get("cost_estimate", 0.001),
-                            "version": r.get("version", "1.0"),
-                        })
-                    except json.JSONDecodeError:
-                        pass
-        self._send_json({"recipes": recipes, "count": len(recipes)})
+    def _handle_recipes_list(self, query: str = "") -> None:
+        self._handle_community_recipes_list(query)
 
     def _handle_recipe_detail(self, recipe_id: str) -> None:
-        r = self._load_recipe(recipe_id)
+        r = self._find_task059_recipe(recipe_id)
         if r is None:
             self._send_json({"error": f"recipe '{recipe_id}' not found"}, 404)
             return
-        self._send_json(r)
+        detail = dict(r)
+        detail.pop("steps", None)
+        self._send_json(detail)
 
     def _handle_recipe_preview(self, recipe_id: str) -> None:
         r = self._load_recipe(recipe_id)
@@ -10900,22 +11396,114 @@ function choose(mode) {
     # Task 059 — Community Recipe Browsing + Installation UI
     # ---------------------------------------------------------------------------
 
+    def _task059_stub_recipes(self) -> list[dict[str, Any]]:
+        return [
+            {
+                "recipe_id": "gmail-inbox-triage-v1",
+                "name": "Gmail Inbox Triage",
+                "app_id": "gmail",
+                "description": "Triages Gmail inbox by priority using labels",
+                "creator": "solace-team",
+                "version": "1.0.0",
+                "runs_count": 142,
+                "hit_rate_pct": 78,
+                "avg_cost_usd": "0.001",
+                "tags": ["email", "productivity"],
+                "is_installed": False,
+                "source": "community",
+            },
+            {
+                "recipe_id": "linkedin-connect-v2",
+                "name": "LinkedIn Auto-Connect",
+                "app_id": "linkedin",
+                "description": "Sends personalized connection requests",
+                "creator": "community",
+                "version": "2.0.0",
+                "runs_count": 89,
+                "hit_rate_pct": 65,
+                "avg_cost_usd": "0.002",
+                "tags": ["social", "networking"],
+                "is_installed": False,
+                "source": "community",
+            },
+            {
+                "recipe_id": "github-pr-summary-v1",
+                "name": "GitHub PR Summary",
+                "app_id": "github",
+                "description": "Summarizes open pull requests for standup",
+                "creator": "solace-team",
+                "version": "1.0.0",
+                "runs_count": 567,
+                "hit_rate_pct": 91,
+                "avg_cost_usd": "0.001",
+                "tags": ["development", "github"],
+                "is_installed": False,
+                "source": "community",
+            },
+        ]
+
+    def _task059_storage_root(self) -> Path:
+        return COMMUNITY_RECIPES_059_PATH.parent / "apps"
+
+    def _task059_recipe_file_path(self, app_id: str, recipe_id: str) -> Path:
+        safe_app_id = re.sub(r"[^a-z0-9_-]+", "-", app_id.lower()).strip("-") or "custom"
+        safe_recipe_id = re.sub(r"[^a-z0-9_-]+", "-", recipe_id.lower()).strip("-") or "recipe"
+        return self._task059_storage_root() / safe_app_id / "recipes" / f"{safe_recipe_id}.json"
+
+    def _task059_upsert_library_entry(self, recipe: dict[str, Any]) -> None:
+        library = self._load_community_library()
+        recipe_id = str(recipe.get("recipe_id", ""))
+        library = [entry for entry in library if str(entry.get("recipe_id", "")) != recipe_id]
+        library.append(dict(recipe))
+        self._save_community_library(library)
+
+    def _task059_write_recipe_file(self, recipe: dict[str, Any]) -> None:
+        app_id = str(recipe.get("app_id", "")).strip() or "custom"
+        recipe_id = str(recipe.get("recipe_id", "")).strip()
+        recipe_path = self._task059_recipe_file_path(app_id, recipe_id)
+        recipe_path.parent.mkdir(parents=True, exist_ok=True)
+        recipe_path.write_text(json.dumps(recipe, indent=2))
+
+    def _find_task059_recipe(self, recipe_id: str) -> Optional[dict[str, Any]]:
+        local_recipe = self._load_recipe(recipe_id)
+        if local_recipe is not None:
+            return local_recipe
+        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
+        for recipe in self._load_recipes_from_local(repo_root):
+            if recipe.get("recipe_id") == recipe_id:
+                return recipe
+        for recipe in self._load_community_library():
+            if recipe.get("recipe_id") == recipe_id:
+                return recipe
+        for recipe in self._task059_stub_recipes():
+            if recipe.get("recipe_id") == recipe_id:
+                return recipe
+        return None
+
     def _load_recipes_from_local(self, repo_root: str) -> list:
         """Read recipe JSON files from {repo_root}/data/default/apps/{app_id}/recipes/*.json."""
         results = []
-        apps_dir = Path(repo_root) / "data" / "default" / "apps"
-        if not apps_dir.exists():
-            return results
-        for app_dir in sorted(apps_dir.iterdir()):
-            recipes_dir = app_dir / "recipes"
-            if not recipes_dir.is_dir():
+        seen_ids: set[str] = set()
+        apps_dirs = [Path(repo_root) / "data" / "default" / "apps", self._task059_storage_root()]
+        for apps_dir in apps_dirs:
+            if not apps_dir.exists():
                 continue
-            app_id = app_dir.name
-            for recipe_file in sorted(recipes_dir.glob("*.json")):
-                try:
-                    r = json.loads(recipe_file.read_text())
+            for app_dir in sorted(apps_dir.iterdir()):
+                recipes_dir = app_dir / "recipes"
+                if not recipes_dir.is_dir():
+                    continue
+                app_id = app_dir.name
+                for recipe_file in sorted(recipes_dir.glob("*.json")):
+                    try:
+                        r = json.loads(recipe_file.read_text())
+                    except json.JSONDecodeError:
+                        continue
+                    recipe_id = str(r.get("recipe_id", recipe_file.stem))
+                    if recipe_id in seen_ids:
+                        continue
+                    seen_ids.add(recipe_id)
                     results.append({
-                        "recipe_id": r.get("recipe_id", recipe_file.stem),
+                        "recipe_id": recipe_id,
                         "name": r.get("name", recipe_file.stem),
                         "app_id": r.get("app_id", app_id),
                         "description": r.get("description", ""),
@@ -10925,11 +11513,10 @@ function choose(mode) {
                         "hit_rate_pct": int(r.get("hit_rate_pct", 0)),
                         "avg_cost_usd": str(r.get("avg_cost_usd", "0.001")),
                         "tags": r.get("tags", []),
+                        "steps": r.get("steps", []),
                         "is_installed": True,
-                        "source": "local",
+                        "source": r.get("source", "local"),
                     })
-                except json.JSONDecodeError:
-                    pass
         return results
 
     def _load_community_library(self) -> list:
@@ -10963,54 +11550,8 @@ function choose(mode) {
 
         repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
         local_recipes = self._load_recipes_from_local(repo_root)
+        stub_community = self._task059_stub_recipes()
 
-        # Stub community data merged with local
-        stub_community = [
-            {
-                "recipe_id": "gmail-inbox-triage-v1",
-                "name": "Gmail Inbox Triage",
-                "app_id": "gmail",
-                "description": "Triages Gmail inbox by priority using labels",
-                "creator": "solace-team",
-                "version": "1.0.0",
-                "runs_count": 142,
-                "hit_rate_pct": 78,
-                "avg_cost_usd": "0.001",
-                "tags": ["email", "productivity"],
-                "is_installed": False,
-                "source": "community",
-            },
-            {
-                "recipe_id": "linkedin-connect-v2",
-                "name": "LinkedIn Auto-Connect",
-                "app_id": "linkedin",
-                "description": "Sends personalized connection requests",
-                "creator": "community",
-                "version": "2.0.0",
-                "runs_count": 89,
-                "hit_rate_pct": 65,
-                "avg_cost_usd": "0.002",
-                "tags": ["social", "networking"],
-                "is_installed": False,
-                "source": "community",
-            },
-            {
-                "recipe_id": "github-pr-summary-v1",
-                "name": "GitHub PR Summary",
-                "app_id": "github",
-                "description": "Summarizes open pull requests for standup",
-                "creator": "solace-team",
-                "version": "1.0.0",
-                "runs_count": 567,
-                "hit_rate_pct": 91,
-                "avg_cost_usd": "0.001",
-                "tags": ["development", "github"],
-                "is_installed": False,
-                "source": "community",
-            },
-        ]
-
-        # Mark installed status from community library
         installed_lib = self._load_community_library()
         installed_ids = {r.get("recipe_id") for r in installed_lib}
         for r in stub_community:
@@ -11039,36 +11580,31 @@ function choose(mode) {
         """POST /api/v1/recipes/{recipe_id}/install — install with scope confirmation data."""
         if not self._check_auth():
             return
-        # Merge local + stub community to find recipe metadata
-        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
-        all_recipes = self._load_recipes_from_local(repo_root)
-        stub_community = [
-            {"recipe_id": "gmail-inbox-triage-v1", "app_id": "gmail", "tags": ["email", "productivity"], "name": "Gmail Inbox Triage", "version": "1.0.0", "creator": "solace-team"},
-            {"recipe_id": "linkedin-connect-v2", "app_id": "linkedin", "tags": ["social", "networking"], "name": "LinkedIn Auto-Connect", "version": "2.0.0", "creator": "community"},
-            {"recipe_id": "github-pr-summary-v1", "app_id": "github", "tags": ["development", "github"], "name": "GitHub PR Summary", "version": "1.0.0", "creator": "solace-team"},
-        ]
-        all_recipes += stub_community
-
-        recipe = next((r for r in all_recipes if r.get("recipe_id") == recipe_id), None)
+        recipe = self._find_task059_recipe(recipe_id)
         if recipe is None:
             self._send_json({"error": f"recipe '{recipe_id}' not found"}, 404)
             return
 
-        # Persist installation
-        installed = self._load_community_library()
-        if not any(r.get("recipe_id") == recipe_id for r in installed):
-            installed.append({**recipe, "installed_at": int(time.time()), "is_installed": True})
-            self._save_community_library(installed)
+        installed_recipe = dict(recipe)
+        installed_recipe["is_installed"] = True
+        installed_recipe["source"] = installed_recipe.get("source", "community")
+        installed_recipe["installed_at"] = int(time.time())
+        try:
+            self._task059_write_recipe_file(installed_recipe)
+            self._task059_upsert_library_entry(installed_recipe)
+        except OSError as e:
+            self._send_json({"error": f"install failed: {e}"}, 500)
+            return
 
         # CRITICAL: scope_required MUST be present — UI must show confirmation modal
         self._send_json({
             "installed": True,
             "recipe_id": recipe_id,
-            "version": recipe.get("version", "1.0.0"),
+            "version": installed_recipe.get("version", "1.0.0"),
             "scope_required": {
-                "app_id": recipe.get("app_id", "unknown"),
-                "tags": recipe.get("tags", []),
-                "description": f"Install '{recipe.get('name', recipe_id)}' by {recipe.get('creator', 'unknown')}",
+                "app_id": installed_recipe.get("app_id", "unknown"),
+                "tags": installed_recipe.get("tags", []),
+                "description": f"Install '{installed_recipe.get('name', recipe_id)}' by {installed_recipe.get('creator', 'unknown')}",
             },
         })
 
@@ -11087,6 +11623,11 @@ function choose(mode) {
             self._send_json({"error": "'name' exceeds 128 chars"}, 400)
             return
 
+        source_recipe = self._find_task059_recipe(recipe_id)
+        if source_recipe is None:
+            self._send_json({"error": f"recipe '{recipe_id}' not found"}, 404)
+            return
+
         new_recipe_id = f"fork-{recipe_id}-{int(time.time())}"
         fork_record = {
             "recipe_id": new_recipe_id,
@@ -11096,16 +11637,22 @@ function choose(mode) {
             "source": "local",
             "is_installed": True,
             "version": "1.0.0",
-            "app_id": "",
-            "tags": [],
+            "app_id": source_recipe.get("app_id", "custom"),
+            "description": source_recipe.get("description", ""),
+            "creator": "local",
+            "tags": source_recipe.get("tags", []),
+            "steps": source_recipe.get("steps", []),
             "runs_count": 0,
             "hit_rate_pct": 0,
             "avg_cost_usd": "0.001",
         }
 
-        installed = self._load_community_library()
-        installed.append(fork_record)
-        self._save_community_library(installed)
+        try:
+            self._task059_write_recipe_file(fork_record)
+            self._task059_upsert_library_entry(fork_record)
+        except OSError as e:
+            self._send_json({"error": f"fork failed: {e}"}, 500)
+            return
 
         self._send_json({
             "new_recipe_id": new_recipe_id,
@@ -11156,9 +11703,12 @@ function choose(mode) {
             "created_at": int(time.time()),
         }
 
-        installed = self._load_community_library()
-        installed.append(new_recipe)
-        self._save_community_library(installed)
+        try:
+            self._task059_write_recipe_file(new_recipe)
+            self._task059_upsert_library_entry(new_recipe)
+        except OSError as e:
+            self._send_json({"error": f"create failed: {e}"}, 500)
+            return
 
         self._send_json({"recipe_id": recipe_id, "local": True}, 201)
 
@@ -11168,47 +11718,33 @@ function choose(mode) {
             return
 
         # Validate recipe exists in local FS, apps recipes, community library, or known stub IDs
-        local_recipe = self._load_recipe(recipe_id)
-        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
-        app_recipes = self._load_recipes_from_local(repo_root)
-        app_recipe_ids = {r.get("recipe_id") for r in app_recipes}
-        installed_lib = self._load_community_library()
-        _community_stub_ids = {"gmail-inbox-triage-v1", "linkedin-connect-v2", "github-pr-summary-v1"}
-        installed_ids = {r.get("recipe_id") or r.get("id") for r in installed_lib}
-        all_known_ids = _community_stub_ids | installed_ids | app_recipe_ids
-        if local_recipe is None and recipe_id not in all_known_ids:
+        recipe = self._find_task059_recipe(recipe_id)
+        if recipe is None:
             self._send_json({"error": f"Recipe '{recipe_id}' not found"}, 404)
             return
 
-        # Build a preview record via actions preview logic — never bypass
-        preview_id = str(uuid.uuid4())
         now_ts = time.time()
-        preview_text = f"Recipe '{recipe_id}' will execute its automation steps."
-        action_class = "B"  # recipe runs are reputation-impact by default
-        cooldown_secs = COOLDOWN_SECONDS[action_class]
-        cooldown_ends_ts = now_ts + cooldown_secs
-        cooldown_ends_at = datetime.fromtimestamp(cooldown_ends_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
-
-        preview = {
-            "preview_id": preview_id,
-            "action_type": f"recipe.run.{recipe_id}",
-            "class": action_class,
-            "status": "PENDING_APPROVAL",
-            "preview_text": preview_text,
-            "estimated_cost": "0.001",
-            "reversal_possible": True,
-            "cooldown_ends_at": cooldown_ends_ts,
-            "created_at": now_ts,
-        }
+        action_class = "B"
+        record = _create_pending_action_record(
+            f"recipe.run.{recipe_id}",
+            {"recipe_id": recipe_id, "tags": recipe.get("tags", [])},
+            str(recipe.get("app_id", "")),
+            "",
+            now_ts,
+        )
+        record["class"] = action_class
+        record["preview"]["preview_text"] = (
+            f"Preview recipe '{recipe.get('name', recipe_id)}' for {recipe.get('app_id', 'community')} before approval."
+        )
         with _PENDING_ACTIONS_LOCK:
-            _PENDING_ACTIONS[preview_id] = preview
+            _PENDING_ACTIONS[record["action_id"]] = record
 
         self._send_json({
-            "preview_id": preview_id,
+            "preview_id": record["action_id"],
             "action_class": action_class,
-            "preview_text": preview_text,
+            "preview_text": record["preview"]["preview_text"],
             "requires_approval": True,
-            "cooldown_ends_at": cooldown_ends_at,
+            "cooldown_ends_at": _utc_isoformat(record["cooldown_ends_at"]),
         }, 202)
 
     def _handle_community_recipes_my_library(self) -> None:
@@ -13917,6 +14453,90 @@ function choose(mode) {
         path.parent.mkdir(parents=True, exist_ok=True)
         path.write_text(json.dumps(settings, indent=2))
 
+    def _load_esign_pending_items(self) -> list[dict]:
+        pending_items = self._load_schedule_settings().get("esign_pending", [])
+        if not isinstance(pending_items, list):
+            return []
+        normalized: list[dict] = []
+        for item in pending_items:
+            if not isinstance(item, dict):
+                continue
+            esign_id = str(item.get("esign_id", "")).strip()
+            action_type = str(item.get("action_type", "")).strip()
+            requested_by = str(item.get("requested_by", "")).strip()
+            requested_at = str(item.get("requested_at", "")).strip()
+            expires_at = str(item.get("expires_at", "")).strip()
+            preview_text = str(item.get("preview_text", "")).strip()
+            if not esign_id:
+                continue
+            normalized.append({
+                "esign_id": esign_id,
+                "action_type": action_type,
+                "requested_by": requested_by,
+                "requested_at": requested_at,
+                "expires_at": expires_at,
+                "preview_text": preview_text,
+            })
+        return normalized
+
+    def _load_esign_history_items(self) -> list[dict]:
+        history_items = self._load_schedule_settings().get("esign_history", [])
+        if not isinstance(history_items, list):
+            return []
+        normalized: list[dict] = []
+        for item in history_items:
+            if not isinstance(item, dict):
+                continue
+            esign_id = str(item.get("esign_id", "")).strip()
+            if not esign_id:
+                continue
+            normalized.append({
+                "esign_id": esign_id,
+                "action_type": str(item.get("action_type", "")).strip(),
+                "signed_at": str(item.get("signed_at", "")).strip(),
+                "approver": str(item.get("approver", "")).strip(),
+                "evidence_hash": str(item.get("evidence_hash", "")).strip(),
+            })
+        return normalized
+
+    def _save_esign_items(self, pending_items: list[dict], history_items: list[dict], chain_head: str) -> None:
+        settings = self._load_schedule_settings()
+        settings["esign_pending"] = pending_items
+        settings["esign_history"] = history_items
+        settings["esign_chain_head"] = chain_head
+        self._save_schedule_settings(settings)
+
+    def _auto_reject_expired_schedule_actions(self, now_ts: float) -> None:
+        with _PENDING_ACTIONS_LOCK:
+            expired_ids = [
+                action_id
+                for action_id, action in _PENDING_ACTIONS.items()
+                if action.get("status") == "PENDING_APPROVAL"
+                and float(action.get("cooldown_ends_at") or 0) <= now_ts
+            ]
+        for action_id in expired_ids:
+            rejected_at = _utc_isoformat(now_ts)
+            with _PENDING_ACTIONS_LOCK:
+                action = _PENDING_ACTIONS.get(action_id)
+                if action is None:
+                    continue
+                if action.get("status") != "PENDING_APPROVAL":
+                    continue
+                cooldown_end = float(action.get("cooldown_ends_at") or 0)
+                if cooldown_end > now_ts:
+                    continue
+                action["status"] = "REJECTED"
+                action["reject_reason"] = "countdown_expired"
+                action["rejected_at"] = rejected_at
+                action_copy = dict(action)
+            item = self._build_activity_item(action_copy, now_ts)
+            evidence_hash = self._write_schedule_audit_item(item, "schedule_auto_rejected")
+            with _PENDING_ACTIONS_LOCK:
+                current = _PENDING_ACTIONS.get(action_id)
+                if current is not None and not current.get("action_hash"):
+                    current["action_hash"] = evidence_hash
+            record_evidence("schedule_cancelled", {"run_id": action_id, "reason": "countdown_expired"})
+
     def _schedule_audit_dir(self) -> Path:
         return PORT_LOCK_PATH.parent / "audit"
 
@@ -14009,6 +14629,7 @@ function choose(mode) {
         return planned_items
 
     def _collect_schedule_items(self, now_ts: float) -> list[dict]:
+        self._auto_reject_expired_schedule_actions(now_ts)
         items = self._load_schedule_audit_items()
         with _PENDING_ACTIONS_LOCK:
             pending_snapshot = list(_PENDING_ACTIONS.values())
@@ -14132,6 +14753,7 @@ function choose(mode) {
         if body is None:
             body = {}
         now_ts = time.time()
+        self._auto_reject_expired_schedule_actions(now_ts)
         with _PENDING_ACTIONS_LOCK:
             action = _PENDING_ACTIONS.get(run_id)
         if action is None:
@@ -14198,6 +14820,7 @@ function choose(mode) {
     def _handle_schedule_viewer_queue(self) -> None:
         """GET /api/v1/schedule/queue — Class B+C items pending sign-off."""
         now_ts = time.time()
+        self._auto_reject_expired_schedule_actions(now_ts)
         with _PENDING_ACTIONS_LOCK:
             snapshot = list(_PENDING_ACTIONS.values())
         result = []
@@ -14225,24 +14848,20 @@ function choose(mode) {
         """GET /api/v1/schedule/upcoming — schedules + keepalive + pending counts (4-tab Tab 1)."""
         if not self._check_auth():
             return
+        now_ts = time.time()
+        self._auto_reject_expired_schedule_actions(now_ts)
         planned_items = self._load_schedule_plan_items()
         schedules = load_schedules()
+        cron_human_by_value = {value: label for value, label in SCHEDULE_EDITOR_CRON_PRESETS.values()}
         pending_approvals = 0
         with _PENDING_ACTIONS_LOCK:
             for action in _PENDING_ACTIONS.values():
                 if action.get("status") == "PENDING_APPROVAL":
                     pending_approvals += 1
-        CRON_PRESETS = {
-            "0 7 * * *":   "Every day at 7:00 AM",
-            "0 9 * * 1-5": "Weekdays at 9:00 AM",
-            "0 * * * *":   "Every hour",
-            "0 */2 * * *": "Every 2 hours",
-            "0 9 * * 1":   "Every Monday at 9:00 AM",
-        }
         result_schedules = []
         for s in schedules:
             cron = s.get("cron", "")
-            cron_human = CRON_PRESETS.get(cron, cron)
+            cron_human = cron_human_by_value.get(cron, cron)
             result_schedules.append({
                 "app_id": s.get("app_id", ""),
                 "app_name": s.get("label", s.get("app_id", "")),
@@ -14262,18 +14881,29 @@ function choose(mode) {
                 "countdown_seconds": 0,
                 "enabled": True,
             })
+        with _SESSIONS_LOCK:
+            session_snapshot = list(_SESSIONS.values())
+        active_sessions = 0
+        for session in session_snapshot:
+            if self._is_session_alive(int(session.get("pid", 0))):
+                active_sessions += 1
+        pending_esign = len(self._load_esign_pending_items())
         self._send_json({
             "schedules": result_schedules,
-            "keepalive": {"active_count": 0, "last_refresh": "", "next_refresh_seconds": 300},
+            "keepalive": {
+                "active_count": active_sessions,
+                "last_refresh": _utc_isoformat(now_ts),
+                "next_refresh_seconds": 60,
+            },
             "pending_approvals": pending_approvals,
-            "pending_esign": 0,
+            "pending_esign": pending_esign,
         })
 
     def _handle_esign_pending(self) -> None:
         """GET /api/v1/esign/pending — list pending eSign requests."""
         if not self._check_auth():
             return
-        self._send_json({"pending": []})
+        self._send_json(self._load_esign_pending_items())
 
     def _handle_esign_sign(self, esign_id: str) -> None:
         """POST /api/v1/esign/{esign_id}/sign — sign an eSign request."""
@@ -14290,15 +14920,48 @@ function choose(mode) {
         if not signature_token:
             self._send_json({"error": "signature_token required"}, 400)
             return
-        from datetime import datetime, timezone
-        sealed_at = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
+        pending_items = self._load_esign_pending_items()
+        current = next((item for item in pending_items if item.get("esign_id") == esign_id), None)
+        if current is None:
+            self._send_json({"error": "esign request not found"}, 404)
+            return
+        settings = self._load_schedule_settings()
+        history_items = self._load_esign_history_items()
+        approver = self._chat_session_key()
+        sealed_at = _utc_isoformat(time.time())
+        previous_hash = str(settings.get("esign_chain_head", ""))
+        evidence_payload = {
+            "esign_id": esign_id,
+            "action_type": current.get("action_type", ""),
+            "requested_by": current.get("requested_by", ""),
+            "requested_at": current.get("requested_at", ""),
+            "expires_at": current.get("expires_at", ""),
+            "preview_text": current.get("preview_text", ""),
+            "approver": approver,
+            "reason": str(body.get("reason", "")).strip(),
+            "signed_at": sealed_at,
+            "previous_hash": previous_hash,
+            "signature_token_sha256": hashlib.sha256(str(signature_token).encode("utf-8")).hexdigest(),
+        }
+        encoded = json.dumps(evidence_payload, sort_keys=True)
+        evidence_hash = "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
+        history_items.insert(0, {
+            "esign_id": esign_id,
+            "action_type": current.get("action_type", ""),
+            "signed_at": sealed_at,
+            "approver": approver,
+            "evidence_hash": evidence_hash,
+        })
+        remaining_pending = [item for item in pending_items if item.get("esign_id") != esign_id]
+        self._save_esign_items(remaining_pending, history_items, evidence_hash)
+        record_evidence("esign_signed", {"esign_id": esign_id, "evidence_hash": evidence_hash})
         self._send_json({"signed": True, "esign_id": esign_id, "sealed_at": sealed_at})
 
     def _handle_esign_history(self) -> None:
         """GET /api/v1/esign/history — eSign completed signatures."""
         if not self._check_auth():
             return
-        self._send_json({"history": []})
+        self._send_json(self._load_esign_history_items())
 
     def _handle_schedule_viewer_calendar(self, query: str) -> None:
         """GET /api/v1/schedule/calendar — group activity items by day for calendar view."""
@@ -14765,29 +15428,13 @@ function choose(mode) {
         """GET /api/v1/session/stats — current session metrics."""
         if not self._check_auth():
             return
-        with _SESSION_STATS_LOCK:
-            stats = dict(_SESSION_STATS)
-        if stats["session_start"] is not None:
-            stats["duration_seconds"] = int(time.time() - stats["session_start"])
-        self._send_json(stats)
+        self._send_json(_session_stats_snapshot())
 
     def _handle_session_stats_reset(self) -> None:
         """POST /api/v1/session/stats/reset — clear session counters."""
         if not self._check_auth():
             return
-        import uuid
-        with _SESSION_STATS_LOCK:
-            _SESSION_STATS["session_id"] = str(uuid.uuid4())
-            _SESSION_STATS["state"] = "IDLE"
-            _SESSION_STATS["app_name"] = None
-            _SESSION_STATS["pages_visited"] = 0
-            _SESSION_STATS["llm_calls"] = 0
-            _SESSION_STATS["cost_usd"] = "0.00"
-            _SESSION_STATS["cost_saved_pct"] = 0
-            _SESSION_STATS["duration_seconds"] = 0
-            _SESSION_STATS["recipes_replayed"] = 0
-            _SESSION_STATS["evidence_captured"] = 0
-            _SESSION_STATS["session_start"] = time.time()
+        _reset_session_stats()
         self._send_json({"reset": True})
 
     def _handle_dashboard_html(self) -> None:
@@ -14906,6 +15553,117 @@ function choose(mode) {
     # Task 062 — App Onboarding: Grey-to-Green 4-State Lifecycle UI
     # ---------------------------------------------------------------------------
 
+    def _app_name(self, app_id: str) -> str:
+        return app_id.replace("-", " ").title()
+
+    def _app_icon(self, app_id: str) -> str:
+        normalized = app_id.lower()
+        if "gmail" in normalized:
+            return "📧"
+        if "slack" in normalized:
+            return "💬"
+        if "drive" in normalized:
+            return "📁"
+        if "linkedin" in normalized:
+            return "💼"
+        return "📦"
+
+    def _app_setup_fields(self, app_id: str) -> list[dict[str, Any]]:
+        normalized = app_id.lower()
+        if "gmail" in normalized:
+            return [{
+                "name": "oauth_token",
+                "type": "oauth",
+                "required": True,
+                "description": "Gmail OAuth token",
+                "placeholder": "Paste Gmail OAuth token",
+            }]
+        if "slack" in normalized:
+            return [{
+                "name": "oauth_token",
+                "type": "oauth",
+                "required": True,
+                "description": "Slack OAuth token",
+                "placeholder": "Paste Slack OAuth token",
+            }]
+        if "drive" in normalized:
+            return [{
+                "name": "oauth_token",
+                "type": "oauth",
+                "required": True,
+                "description": "Google Drive OAuth token",
+                "placeholder": "Paste Google Drive OAuth token",
+            }]
+        if "linkedin" in normalized:
+            return [{
+                "name": "oauth_token",
+                "type": "oauth",
+                "required": True,
+                "description": "LinkedIn OAuth token",
+                "placeholder": "Paste LinkedIn OAuth token",
+            }]
+        return []
+
+    def _app_setup_requirements_payload(self, app_id: str) -> dict[str, Any]:
+        fields = self._app_setup_fields(app_id)
+        vault_key = f"oauth3:{app_id}" if any(field.get("type") == "oauth" for field in fields) else None
+        return {
+            "app_id": app_id,
+            "fields": fields,
+            "vault_key": vault_key,
+        }
+
+    def _app_config_path(self, app_id: str) -> Path:
+        return Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
+
+    def _app_config_key(self, app_id: str) -> bytes:
+        session_token_sha256 = getattr(self.server, "session_token_sha256", "")
+        normalized_token = session_token_sha256 if _SHA256_HEX_RE.fullmatch(session_token_sha256) else ("0" * 64)
+        salt_hex = hashlib.sha256(app_id.encode("utf-8")).hexdigest()
+        kdf = PBKDF2HMAC(
+            algorithm=hashes.SHA256(),
+            length=32,
+            salt=bytes.fromhex(salt_hex),
+            iterations=OAUTH3_PBKDF2_ITERATIONS,
+        )
+        return kdf.derive(normalized_token.encode("utf-8"))
+
+    def _encrypt_app_config(self, app_id: str, config: dict[str, Any]) -> dict[str, Any]:
+        plaintext = json.dumps(
+            {"app_id": app_id, "config": config},
+            sort_keys=True,
+            separators=(",", ":"),
+        ).encode("utf-8")
+        nonce = secrets.token_bytes(12)
+        ciphertext = AESGCM(self._app_config_key(app_id)).encrypt(nonce, plaintext, None)
+        return {
+            "app_id": app_id,
+            "cipher": "AES-256-GCM",
+            "nonce_b64": base64.b64encode(nonce).decode("ascii"),
+            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
+            "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
+            "kdf": {
+                "algorithm": "PBKDF2-HMAC-SHA256",
+                "iterations": OAUTH3_PBKDF2_ITERATIONS,
+                "salt_hex": hashlib.sha256(app_id.encode("utf-8")).hexdigest(),
+            },
+        }
+
+    def _app_config_complete(self, app_id: str) -> bool:
+        config_path = self._app_config_path(app_id)
+        try:
+            envelope = json.loads(config_path.read_text())
+        except FileNotFoundError:
+            return False
+        except json.JSONDecodeError:
+            return False
+        except OSError:
+            return False
+        if not isinstance(envelope, dict):
+            return False
+        required_keys = {"cipher", "nonce_b64", "ciphertext_b64", "ciphertext_sha256", "kdf"}
+        return envelope.get("cipher") == "AES-256-GCM" and required_keys.issubset(envelope)
+
     def _handle_apps_lifecycle(self) -> None:
         """GET /api/v1/apps/lifecycle — list all apps with their current state."""
         if not self._check_auth():
@@ -14913,14 +15671,14 @@ function choose(mode) {
         apps = getattr(self.server, "apps", [])
         result = []
         for app_id in (apps if isinstance(apps, list) else []):
-            config_path = Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
-            is_configured = config_path.exists()
+            setup_requirements = self._app_setup_requirements_payload(app_id)
+            is_configured = self._app_config_complete(app_id)
             result.append({
                 "app_id": app_id,
-                "name": app_id.replace("-", " ").title(),
-                "icon": "\U0001F4E6",
+                "name": self._app_name(app_id),
+                "icon": self._app_icon(app_id),
                 "state": "activated" if is_configured else "installed",
-                "config_required": [],
+                "config_required": [field["name"] for field in setup_requirements["fields"] if field.get("required")],
                 "config_complete": is_configured,
             })
         self._send_json({"apps": result})
@@ -14929,48 +15687,64 @@ function choose(mode) {
         """GET /api/v1/apps/{app_id}/setup-requirements — fields needed to activate."""
         if not self._check_auth():
             return
-        self._send_json({
-            "app_id": app_id,
-            "fields": [],
-            "vault_key": None,
-        })
+        self._send_json(self._app_setup_requirements_payload(app_id))
 
     def _handle_app_activate(self, app_id: str) -> None:
         """POST /api/v1/apps/{app_id}/activate — store encrypted config, mark activated."""
         if not self._check_auth():
             return
-        try:
-            content_length = int(self.headers.get("Content-Length", 0))
-            body = json.loads(self.rfile.read(content_length) or b"{}") if content_length else {}
-        except json.JSONDecodeError:
-            self._send_json({"error": "Invalid JSON"}, 400)
+        body = self._read_json_body()
+        if body is None:
+            return
+        config = body.get("config", {})
+        if not isinstance(config, dict):
+            self._send_json({"error": "config must be an object"}, 400)
             return
-        config_dir = Path.home() / ".solace" / "app-configs"
+        required_fields = [field["name"] for field in self._app_setup_fields(app_id) if field.get("required")]
+        missing_fields = []
+        for field_name in required_fields:
+            value = config.get(field_name)
+            if value is None or (isinstance(value, str) and not value.strip()):
+                missing_fields.append(field_name)
+        if missing_fields:
+            self._send_json({"error": "missing required config fields", "missing_fields": missing_fields}, 400)
+            return
+        config_path = self._app_config_path(app_id)
         try:
-            config_dir.mkdir(parents=True, exist_ok=True)
+            config_path.parent.mkdir(parents=True, exist_ok=True)
         except OSError as e:
             self._send_json({"error": f"Could not create config dir: {e}"}, 500)
             return
-        config_path = config_dir / f"{app_id}.json"
+        envelope = self._encrypt_app_config(app_id, config)
         try:
-            config_path.write_text(json.dumps({"app_id": app_id, "configured": True}))
+            config_path.write_text(json.dumps(envelope, sort_keys=True, separators=(",", ":")))
         except OSError as e:
             self._send_json({"error": f"Could not save config: {e}"}, 500)
             return
-        self._send_json({"activated": True, "app_id": app_id, "state": "activated"})
+        self._send_json({
+            "activated": True,
+            "app_id": app_id,
+            "state": "activated",
+            "local_storage": {"key": f"app:{app_id}:state", "value": "activated"},
+        })
 
     def _handle_app_deactivate(self, app_id: str) -> None:
         """DELETE /api/v1/apps/{app_id}/activate — reset to installed state."""
         if not self._check_auth():
             return
-        config_path = Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
+        config_path = self._app_config_path(app_id)
         try:
             if config_path.exists():
                 config_path.unlink()
         except OSError as e:
             self._send_json({"error": f"Could not remove config: {e}"}, 500)
             return
-        self._send_json({"deactivated": True, "app_id": app_id, "state": "installed"})
+        self._send_json({
+            "deactivated": True,
+            "app_id": app_id,
+            "state": "installed",
+            "local_storage": {"key": f"app:{app_id}:state", "value": "installed"},
+        })
 
     def _handle_apps_html(self) -> None:
         """GET /web/apps.html — serve the app onboarding page."""
@@ -29293,6 +30067,838 @@ function choose(mode) {
         """GET /api/v1/geo-tracker/event-types — list event types (public)."""
         self._send_json({"event_types": GEO_EVENT_TYPES})
 
+    # ---------------------------------------------------------------------------
+    # Task 168 — iFrame Tracker handlers
+    # ---------------------------------------------------------------------------
+    def _handle_iframe_tracker_create(self, payload: Optional[dict[str, Any]] = None) -> None:
+        """POST /api/v1/iframe-tracker/frames — record iframe event (auth required)."""
+        if self._require_auth() is False:
+            return
+        body = self._tracker_body(payload)
+        if body is None:
+            return
+        frame_type = str(body.get("frame_type", "")).strip()
+        if frame_type not in IFR_FRAME_TYPES:
+            self._send_json_compat(400, {"error": f"frame_type must be one of {IFR_FRAME_TYPES}"})
+            return
+        page_url = body.get("page_url", "")
+        if not isinstance(page_url, str) or not page_url.strip():
+            self._send_json_compat(400, {"error": "page_url is required"})
+            return
+        src_url = body.get("src_url", "")
+        if not isinstance(src_url, str) or not src_url.strip():
+            self._send_json_compat(400, {"error": "src_url is required"})
+            return
+        is_cross_origin = body.get("is_cross_origin")
+        if not isinstance(is_cross_origin, bool):
+            self._send_json_compat(400, {"error": "is_cross_origin must be a boolean"})
+            return
+        sandbox_attrs = body.get("sandbox_attrs", [])
+        if not isinstance(sandbox_attrs, list) or any(not isinstance(attr, str) for attr in sandbox_attrs):
+            self._send_json_compat(400, {"error": "sandbox_attrs must be a list of strings"})
+            return
+        invalid_attrs = [attr for attr in sandbox_attrs if attr not in IFR_SANDBOX_ATTRS]
+        if invalid_attrs:
+            self._send_json_compat(400, {"error": f"unknown sandbox_attrs: {invalid_attrs}"})
+            return
+        load_time_ms = body.get("load_time_ms")
+        if not isinstance(load_time_ms, int) or isinstance(load_time_ms, bool) or load_time_ms < 0:
+            self._send_json_compat(400, {"error": "load_time_ms must be int >= 0"})
+            return
+        frame = {
+            "frame_id": "ifr_" + str(uuid.uuid4()),
+            "frame_type": frame_type,
+            "page_url_hash": _sha256_text(page_url),
+            "src_url_hash": _sha256_text(src_url),
+            "is_cross_origin": is_cross_origin,
+            "sandbox_attrs": list(sandbox_attrs),
+            "load_time_ms": load_time_ms,
+            "recorded_at": _utc_isoformat(time.time()),
+        }
+        with _IFRAME_LOCK:
+            if len(_IFRAME_RECORDS) >= MAX_IFRAME_RECORDS:
+                _IFRAME_RECORDS.pop(0)
+            _IFRAME_RECORDS.append(frame)
+        self._send_json_compat(201, frame)
+
+    def _handle_iframe_tracker_list(self) -> None:
+        """GET /api/v1/iframe-tracker/frames — list frames (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _IFRAME_LOCK:
+            frames = [dict(frame) for frame in _IFRAME_RECORDS]
+        self._send_json_compat(200, {"frames": frames, "total": len(frames)})
+
+    def _handle_iframe_tracker_delete(self, frame_id: str) -> None:
+        """DELETE /api/v1/iframe-tracker/frames/{frame_id} — delete frame record (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _IFRAME_LOCK:
+            index = next((i for i, frame in enumerate(_IFRAME_RECORDS) if frame["frame_id"] == frame_id), None)
+            if index is None:
+                self._send_json_compat(404, {"error": "frame not found"})
+                return
+            _IFRAME_RECORDS.pop(index)
+        self._send_json_compat(200, {"status": "deleted", "frame_id": frame_id})
+
+    def _handle_iframe_tracker_stats(self) -> None:
+        """GET /api/v1/iframe-tracker/stats — iframe stats (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _IFRAME_LOCK:
+            frames = list(_IFRAME_RECORDS)
+        total = len(frames)
+        by_type = {frame_type: 0 for frame_type in IFR_FRAME_TYPES}
+        cross_origin_count = 0
+        total_load_ms = 0
+        for frame in frames:
+            frame_type = frame.get("frame_type", "")
+            by_type[frame_type] = by_type.get(frame_type, 0) + 1
+            if frame.get("is_cross_origin"):
+                cross_origin_count += 1
+            total_load_ms += int(frame.get("load_time_ms", 0))
+        cross_origin_rate = _decimal_2(Decimal(str(cross_origin_count / total))) if total > 0 else "0.00"
+        avg_load_ms = _decimal_2(Decimal(str(total_load_ms / total))) if total > 0 else "0.00"
+        self._send_json_compat(200, {
+            "total_frames": total,
+            "by_type": by_type,
+            "cross_origin_count": cross_origin_count,
+            "cross_origin_rate": cross_origin_rate,
+            "avg_load_ms": avg_load_ms,
+        })
+
+    def _handle_iframe_tracker_frame_types(self) -> None:
+        """GET /api/v1/iframe-tracker/frame-types — list frame types (public)."""
+        self._send_json_compat(200, {"frame_types": IFR_FRAME_TYPES})
+
+    # ---------------------------------------------------------------------------
+    # Task 169 — Push Notification Tracker handlers
+    # ---------------------------------------------------------------------------
+    def _handle_push_notification_tracker_create(self, payload: Optional[dict[str, Any]] = None) -> None:
+        """POST /api/v1/push-tracker/events — record push event (auth required)."""
+        if self._require_auth() is False:
+            return
+        body = self._tracker_body(payload)
+        if body is None:
+            return
+        event_type = str(body.get("event_type", "")).strip()
+        if event_type not in PNT_EVENT_TYPES:
+            self._send_json_compat(400, {"error": f"event_type must be one of {PNT_EVENT_TYPES}"})
+            return
+        origin = body.get("origin", "")
+        if not isinstance(origin, str) or not origin.strip():
+            self._send_json_compat(400, {"error": "origin is required"})
+            return
+        endpoint = body.get("endpoint", None)
+        if endpoint is not None and not isinstance(endpoint, str):
+            self._send_json_compat(400, {"error": "endpoint must be a string or null"})
+            return
+        is_https = body.get("is_https")
+        if not isinstance(is_https, bool):
+            self._send_json_compat(400, {"error": "is_https must be a boolean"})
+            return
+        event = {
+            "event_id": "pnt_" + str(uuid.uuid4()),
+            "event_type": event_type,
+            "origin_hash": _sha256_text(origin),
+            "endpoint_hash": _sha256_text(endpoint) if endpoint else None,
+            "is_https": is_https,
+            "recorded_at": _utc_isoformat(time.time()),
+        }
+        with _PUSH_TRACKER_LOCK:
+            if len(_PUSH_EVENTS) >= MAX_PUSH_EVENTS:
+                _PUSH_EVENTS.pop(0)
+            _PUSH_EVENTS.append(event)
+        self._send_json_compat(201, event)
+
+    def _handle_push_notification_tracker_list(self) -> None:
+        """GET /api/v1/push-tracker/events — list events (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _PUSH_TRACKER_LOCK:
+            events = [dict(event) for event in _PUSH_EVENTS]
+        self._send_json_compat(200, {"events": events, "total": len(events)})
+
+    def _handle_push_notification_tracker_delete(self, event_id: str) -> None:
+        """DELETE /api/v1/push-tracker/events/{event_id} — delete event (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _PUSH_TRACKER_LOCK:
+            index = next((i for i, event in enumerate(_PUSH_EVENTS) if event["event_id"] == event_id), None)
+            if index is None:
+                self._send_json_compat(404, {"error": "event not found"})
+                return
+            _PUSH_EVENTS.pop(index)
+        self._send_json_compat(200, {"status": "deleted", "event_id": event_id})
+
+    def _handle_push_notification_tracker_stats(self) -> None:
+        """GET /api/v1/push-tracker/stats — push stats (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _PUSH_TRACKER_LOCK:
+            events = list(_PUSH_EVENTS)
+        by_event_type = {event_type: 0 for event_type in PNT_EVENT_TYPES}
+        subscription_count = 0
+        permission_events = 0
+        permission_granted = 0
+        for event in events:
+            event_type = event.get("event_type", "")
+            by_event_type[event_type] = by_event_type.get(event_type, 0) + 1
+            if isinstance(event_type, str) and event_type.startswith("subscription_"):
+                subscription_count += 1
+            if isinstance(event_type, str) and event_type.startswith("permission_"):
+                permission_events += 1
+            if event_type == "permission_granted":
+                permission_granted += 1
+        permission_grant_rate = _decimal_2(Decimal(str(permission_granted / permission_events))) if permission_events > 0 else "0.00"
+        self._send_json_compat(200, {
+            "total_events": len(events),
+            "by_event_type": by_event_type,
+            "subscription_count": subscription_count,
+            "permission_grant_rate": permission_grant_rate,
+        })
+
+    def _handle_push_notification_tracker_event_types(self) -> None:
+        """GET /api/v1/push-tracker/event-types — list event types (public)."""
+        self._send_json_compat(200, {"event_types": PNT_EVENT_TYPES})
+
+    # ---------------------------------------------------------------------------
+    # Task 170 — Canvas Fingerprint Detector handlers
+    # ---------------------------------------------------------------------------
+    def _handle_canvas_fingerprint_detector_create(self, payload: Optional[dict[str, Any]] = None) -> None:
+        """POST /api/v1/canvas-fp/detections — record detection (auth required)."""
+        if self._require_auth() is False:
+            return
+        body = self._tracker_body(payload)
+        if body is None:
+            return
+        technique = str(body.get("technique", "")).strip()
+        if technique not in CFP_TECHNIQUES:
+            self._send_json_compat(400, {"error": f"technique must be one of {CFP_TECHNIQUES}"})
+            return
+        url = body.get("url", "")
+        if not isinstance(url, str) or not url.strip():
+            self._send_json_compat(400, {"error": "url is required"})
+            return
+        script_url = body.get("script_url", None)
+        if script_url is not None and not isinstance(script_url, str):
+            self._send_json_compat(400, {"error": "script_url must be a string or null"})
+            return
+        was_blocked = body.get("was_blocked")
+        if not isinstance(was_blocked, bool):
+            self._send_json_compat(400, {"error": "was_blocked must be a boolean"})
+            return
+        try:
+            confidence_value = Decimal(str(body.get("confidence_score", "")))
+        except (InvalidOperation, TypeError, ValueError):
+            self._send_json_compat(400, {"error": "confidence_score must be a decimal between 0 and 1"})
+            return
+        if confidence_value < Decimal("0") or confidence_value > Decimal("1"):
+            self._send_json_compat(400, {"error": "confidence_score must be between 0 and 1"})
+            return
+        detection = {
+            "detection_id": "cfp_" + str(uuid.uuid4()),
+            "technique": technique,
+            "url_hash": _sha256_text(url),
+            "script_hash": _sha256_text(script_url) if script_url else None,
+            "was_blocked": was_blocked,
+            "confidence_score": _decimal_2(confidence_value),
+            "recorded_at": _utc_isoformat(time.time()),
+        }
+        with _FP_DETECTOR_LOCK:
+            if len(_FP_DETECTIONS) >= MAX_FP_DETECTIONS:
+                _FP_DETECTIONS.pop(0)
+            _FP_DETECTIONS.append(detection)
+        self._send_json_compat(201, detection)
+
+    def _handle_canvas_fingerprint_detector_list(self) -> None:
+        """GET /api/v1/canvas-fp/detections — list detections (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _FP_DETECTOR_LOCK:
+            detections = [dict(detection) for detection in _FP_DETECTIONS]
+        self._send_json_compat(200, {"detections": detections, "total": len(detections)})
+
+    def _handle_canvas_fingerprint_detector_delete(self, detection_id: str) -> None:
+        """DELETE /api/v1/canvas-fp/detections/{detection_id} — delete detection (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _FP_DETECTOR_LOCK:
+            index = next((i for i, detection in enumerate(_FP_DETECTIONS) if detection["detection_id"] == detection_id), None)
+            if index is None:
+                self._send_json_compat(404, {"error": "detection not found"})
+                return
+            _FP_DETECTIONS.pop(index)
+        self._send_json_compat(200, {"status": "deleted", "detection_id": detection_id})
+
+    def _handle_canvas_fingerprint_detector_stats(self) -> None:
+        """GET /api/v1/canvas-fp/stats — detection stats (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _FP_DETECTOR_LOCK:
+            detections = list(_FP_DETECTIONS)
+        by_technique = {technique: 0 for technique in CFP_TECHNIQUES}
+        blocked_count = 0
+        confidence_sum = Decimal("0")
+        for detection in detections:
+            technique = detection.get("technique", "")
+            by_technique[technique] = by_technique.get(technique, 0) + 1
+            if detection.get("was_blocked"):
+                blocked_count += 1
+            confidence_sum += Decimal(str(detection.get("confidence_score", "0")))
+        total = len(detections)
+        block_rate = _decimal_2(Decimal(str(blocked_count / total))) if total > 0 else "0.00"
+        avg_confidence = _decimal_2(confidence_sum / Decimal(str(total))) if total > 0 else "0.00"
+        self._send_json_compat(200, {
+            "total_detections": total,
+            "by_technique": by_technique,
+            "blocked_count": blocked_count,
+            "block_rate": block_rate,
+            "avg_confidence": avg_confidence,
+        })
+
+    def _handle_canvas_fingerprint_detector_techniques(self) -> None:
+        """GET /api/v1/canvas-fp/techniques — list techniques (public)."""
+        self._send_json_compat(200, {"techniques": CFP_TECHNIQUES})
+
+    # ---------------------------------------------------------------------------
+    # Task 171 — Service Worker Tracker handlers
+    # ---------------------------------------------------------------------------
+    def _handle_service_worker_tracker_create(self, payload: Optional[dict[str, Any]] = None) -> None:
+        """POST /api/v1/sw-tracker/registrations — record SW registration (auth required)."""
+        if self._require_auth() is False:
+            return
+        body = self._tracker_body(payload)
+        if body is None:
+            return
+        event_type = str(body.get("event_type", "")).strip()
+        if event_type not in SWR_EVENT_TYPES:
+            self._send_json_compat(400, {"error": f"event_type must be one of {SWR_EVENT_TYPES}"})
+            return
+        state = str(body.get("state", "")).strip()
+        if state not in SWR_STATES:
+            self._send_json_compat(400, {"error": f"state must be one of {SWR_STATES}"})
+            return
+        scope_url = body.get("scope_url", "")
+        if not isinstance(scope_url, str) or not scope_url.strip():
+            self._send_json_compat(400, {"error": "scope_url is required"})
+            return
+        script_url = body.get("script_url", "")
+        if not isinstance(script_url, str) or not script_url.strip():
+            self._send_json_compat(400, {"error": "script_url is required"})
+            return
+        is_https = body.get("is_https")
+        if not isinstance(is_https, bool):
+            self._send_json_compat(400, {"error": "is_https must be a boolean"})
+            return
+        registration = {
+            "reg_id": "swr_" + str(uuid.uuid4()),
+            "event_type": event_type,
+            "state": state,
+            "scope_hash": _sha256_text(scope_url),
+            "script_hash": _sha256_text(script_url),
+            "is_https": is_https,
+            "recorded_at": _utc_isoformat(time.time()),
+        }
+        with _SW_TRACKER_LOCK:
+            if len(_SW_REGISTRATIONS) >= MAX_SW_REGISTRATIONS:
+                _SW_REGISTRATIONS.pop(0)
+            _SW_REGISTRATIONS.append(registration)
+        self._send_json_compat(201, registration)
+
+    def _handle_service_worker_tracker_list(self) -> None:
+        """GET /api/v1/sw-tracker/registrations — list registrations (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _SW_TRACKER_LOCK:
+            registrations = [dict(registration) for registration in _SW_REGISTRATIONS]
+        self._send_json_compat(200, {"registrations": registrations, "total": len(registrations)})
+
+    def _handle_service_worker_tracker_delete(self, reg_id: str) -> None:
+        """DELETE /api/v1/sw-tracker/registrations/{reg_id} — delete registration (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _SW_TRACKER_LOCK:
+            index = next((i for i, registration in enumerate(_SW_REGISTRATIONS) if registration["reg_id"] == reg_id), None)
+            if index is None:
+                self._send_json_compat(404, {"error": "registration not found"})
+                return
+            _SW_REGISTRATIONS.pop(index)
+        self._send_json_compat(200, {"status": "deleted", "reg_id": reg_id})
+
+    def _handle_service_worker_tracker_stats(self) -> None:
+        """GET /api/v1/sw-tracker/stats — SW stats (auth required)."""
+        if self._require_auth() is False:
+            return
+        with _SW_TRACKER_LOCK:
+            registrations = list(_SW_REGISTRATIONS)
+        by_event = {event_type: 0 for event_type in SWR_EVENT_TYPES}
+        by_state = {state: 0 for state in SWR_STATES}
+        https_count = 0
+        for registration in registrations:
+            event_type = registration.get("event_type", "")
+            state = registration.get("state", "")
+            by_event[event_type] = by_event.get(event_type, 0) + 1
+            by_state[state] = by_state.get(state, 0) + 1
+            if registration.get("is_https"):
+                https_count += 1
+        self._send_json_compat(200, {
+            "total_registrations": len(registrations),
+            "by_event": by_event,
+            "by_state": by_state,
+            "https_count": https_count,
+        })
+
+    def _handle_service_worker_tracker_sw_events(self) -> None:
+        """GET /api/v1/sw-tracker/sw-events — list service worker event types (public)."""
+        self._send_json_compat(200, {"sw_events": SWR_EVENT_TYPES, "states": SWR_STATES})
+
+    def _handle_service_worker_tracker_event_types(self) -> None:
+        self._handle_service_worker_tracker_sw_events()
+
+    # ---------------------------------------------------------------------------
+    # Task 163 — Storage Quota Monitor handlers
+    # ---------------------------------------------------------------------------
+    def _handle_storage_quota_create(self, body: Optional[dict] = None) -> None:
+        if not self._check_auth():
+            return
+        if body is None:
+            body = self._read_json_body()
+        if body is None:
+            return
+        storage_type = str(body.get("storage_type", "")).strip()
+        if storage_type not in SQM_STORAGE_TYPES:
+            self._send_json({"error": f"storage_type must be one of {SQM_STORAGE_TYPES}"}, 400)
+            return
+        used_bytes, used_error = _tracker_parse_int(body.get("used_bytes"), "used_bytes", 0)
+        if used_error:
+            self._send_json({"error": used_error}, 400)
+            return
+        quota_bytes, quota_error = _tracker_parse_int(body.get("quota_bytes"), "quota_bytes", 1)
+        if quota_error:
+            self._send_json({"error": quota_error}, 400)
+            return
+        usage_pct = _tracker_decimal_str((Decimal(str(used_bytes)) / Decimal(str(quota_bytes))) * Decimal("100"))
+        snapshot = {
+            "snapshot_id": "sqm_" + str(uuid.uuid4()),
+            "storage_type": storage_type,
+            "url_hash": _tracker_sha256(body.get("url", "")),
+            "used_bytes": used_bytes,
+            "quota_bytes": quota_bytes,
+            "usage_pct": usage_pct,
+            "recorded_at": _tracker_now_iso(),
+        }
+        with _SQM_STORAGE_LOCK:
+            if len(_SQM_STORAGE_SNAPSHOTS) >= SQM_MAX_STORAGE_SNAPSHOTS:
+                _SQM_STORAGE_SNAPSHOTS.pop(0)
+            _SQM_STORAGE_SNAPSHOTS.append(snapshot)
+        self._send_json(snapshot, 201)
+
+    def _handle_storage_quota_list(self) -> None:
+        if not self._check_auth():
+            return
+        with _SQM_STORAGE_LOCK:
+            snapshots = [dict(snapshot) for snapshot in _SQM_STORAGE_SNAPSHOTS]
+        self._send_json({"snapshots": snapshots, "total": len(snapshots)})
+
+    def _handle_storage_quota_delete(self, snapshot_id: str) -> None:
+        if not self._check_auth():
+            return
+        with _SQM_STORAGE_LOCK:
+            index = next((i for i, snapshot in enumerate(_SQM_STORAGE_SNAPSHOTS) if snapshot["snapshot_id"] == snapshot_id), None)
+            if index is None:
+                self._send_json({"error": "snapshot not found"}, 404)
+                return
+            _SQM_STORAGE_SNAPSHOTS.pop(index)
+        self._send_json({"status": "deleted", "snapshot_id": snapshot_id})
+
+    def _handle_storage_quota_stats(self) -> None:
+        if not self._check_auth():
+            return
+        with _SQM_STORAGE_LOCK:
+            snapshots = [dict(snapshot) for snapshot in _SQM_STORAGE_SNAPSHOTS]
+        by_storage_type = {storage_type: 0 for storage_type in SQM_STORAGE_TYPES}
+        total_usage_pct = Decimal("0")
+        max_usage_pct = Decimal("0")
+        for snapshot in snapshots:
+            storage_type = snapshot.get("storage_type", "")
+            by_storage_type[storage_type] = by_storage_type.get(storage_type, 0) + 1
+            usage_pct = Decimal(snapshot.get("usage_pct", "0.00"))
+            total_usage_pct += usage_pct
+            if usage_pct > max_usage_pct:
+                max_usage_pct = usage_pct
+        total_snapshots = len(snapshots)
+        avg_usage_pct = _tracker_decimal_str(total_usage_pct / Decimal(str(total_snapshots))) if total_snapshots else "0.00"
+        self._send_json({
+            "total_snapshots": total_snapshots,
+            "by_storage_type": by_storage_type,
+            "avg_usage_pct": avg_usage_pct,
+            "max_usage_pct": _tracker_decimal_str(max_usage_pct),
+        })
+
+    def _handle_storage_quota_types(self) -> None:
+        self._send_json({"storage_types": SQM_STORAGE_TYPES})
+
+    # ---------------------------------------------------------------------------
+    # Task 164 — Permission Policy Tracker handlers
+    # ---------------------------------------------------------------------------
+    def _handle_permission_policy_create(self, body: Optional[dict] = None) -> None:
+        if not self._check_auth():
+            return
+        if body is None:
+            body = self._read_json_body()
+        if body is None:
+            return
+        policy_type = str(body.get("policy_type", "")).strip()
+        if policy_type not in PPE_PERMISSION_POLICY_TYPES:
+            self._send_json({"error": f"policy_type must be one of {PPE_PERMISSION_POLICY_TYPES}"}, 400)
+            return
+        action = str(body.get("action", "")).strip()
+        if action not in PPE_POLICY_ACTIONS:
+            self._send_json({"error": f"action must be one of {PPE_POLICY_ACTIONS}"}, 400)
+            return
+        origin_raw = str(body.get("origin", "")).strip()
+        if not origin_raw:
+            url_value = str(body.get("url", "")).strip()
+            if url_value:
+                parsed = urllib.parse.urlsplit(url_value)
+                if parsed.scheme and parsed.netloc:
+                    origin_raw = f"{parsed.scheme}://{parsed.netloc}"
+        is_violation, violation_error = _tracker_parse_bool(body.get("is_violation", action == "violation"), "is_violation")
+        if violation_error:
+            self._send_json({"error": violation_error}, 400)
+            return
+        event = {
+            "event_id": "ppe_" + str(uuid.uuid4()),
+            "policy_type": policy_type,
+            "action": action,
+            "url_hash": _tracker_sha256(body.get("url", "")),
+            "origin_hash": _tracker_sha256(origin_raw),
+            "is_violation": is_violation,
+            "recorded_at": _tracker_now_iso(),
+        }
+        with _PPE_POLICY_LOCK:
+            if len(_PPE_POLICY_EVENTS) >= PPE_MAX_POLICY_EVENTS:
+                _PPE_POLICY_EVENTS.pop(0)
+            _PPE_POLICY_EVENTS.append(event)
+        self._send_json(event, 201)
+
+    def _handle_permission_policy_list(self) -> None:
+        if not self._check_auth():
+            return
+        with _PPE_POLICY_LOCK:
+            events = [dict(event) for event in _PPE_POLICY_EVENTS]
+        self._send_json({"events": events, "total": len(events)})
+
+    def _handle_permission_policy_delete(self, event_id: str) -> None:
+        if not self._check_auth():
+            return
+        with _PPE_POLICY_LOCK:
+            index = next((i for i, event in enumerate(_PPE_POLICY_EVENTS) if event["event_id"] == event_id), None)
+            if index is None:
+                self._send_json({"error": "event not found"}, 404)
+                return
+            _PPE_POLICY_EVENTS.pop(index)
+        self._send_json({"status": "deleted", "event_id": event_id})
+
+    def _handle_permission_policy_stats(self) -> None:
+        if not self._check_auth():
+            return
+        with _PPE_POLICY_LOCK:
+            events = [dict(event) for event in _PPE_POLICY_EVENTS]
+        by_policy_type = {policy_type: 0 for policy_type in PPE_PERMISSION_POLICY_TYPES}
+        by_action = {action: 0 for action in PPE_POLICY_ACTIONS}
+        violation_count = 0
+        for event in events:
+            policy_type = event.get("policy_type", "")
+            action = event.get("action", "")
+            by_policy_type[policy_type] = by_policy_type.get(policy_type, 0) + 1
+            by_action[action] = by_action.get(action, 0) + 1
+            if event.get("is_violation"):
+                violation_count += 1
+        total_events = len(events)
+        violation_rate = _tracker_decimal_str(Decimal(str(violation_count)) / Decimal(str(total_events))) if total_events else "0.00"
+        self._send_json({
+            "total_events": total_events,
+            "by_policy_type": by_policy_type,
+            "by_action": by_action,
+            "violation_count": violation_count,
+            "violation_rate": violation_rate,
+        })
+
+    def _handle_permission_policy_types(self) -> None:
+        self._send_json({"policy_types": PPE_PERMISSION_POLICY_TYPES, "actions": PPE_POLICY_ACTIONS})
+
+    # ---------------------------------------------------------------------------
+    # Task 165 — Web Vitals Tracker handlers
+    # ---------------------------------------------------------------------------
+    def _handle_web_vitals_create(self, body: Optional[dict] = None) -> None:
+        if not self._check_auth():
+            return
+        if body is None:
+            body = self._read_json_body()
+        if body is None:
+            return
+        metric_type = str(body.get("metric_type", "")).strip()
+        if metric_type not in WVM_WEB_VITAL_METRICS:
+            self._send_json({"error": f"metric_type must be one of {WVM_WEB_VITAL_METRICS}"}, 400)
+            return
+        rating = str(body.get("rating", "")).strip()
+        if rating not in WVM_VITAL_RATINGS:
+            self._send_json({"error": f"rating must be one of {WVM_VITAL_RATINGS}"}, 400)
+            return
+        navigation_type = str(body.get("navigation_type", "")).strip()
+        if navigation_type not in WVM_NAVIGATION_TYPES:
+            self._send_json({"error": f"navigation_type must be one of {WVM_NAVIGATION_TYPES}"}, 400)
+            return
+        value_ms, value_error = _tracker_parse_non_negative_decimal(body.get("value_ms"), "value_ms")
+        if value_error:
+            self._send_json({"error": value_error}, 400)
+            return
+        measurement = {
+            "measurement_id": "wvm_" + str(uuid.uuid4()),
+            "metric_type": metric_type,
+            "url_hash": _tracker_sha256(body.get("url", "")),
+            "value_ms": _tracker_decimal_str(value_ms),
+            "rating": rating,
+            "navigation_type": navigation_type,
+            "recorded_at": _tracker_now_iso(),
+        }
+        with _WVM_LOCK:
+            if len(_WVM_MEASUREMENTS) >= WVM_MAX_MEASUREMENTS:
+                _WVM_MEASUREMENTS.pop(0)
+            _WVM_MEASUREMENTS.append(measurement)
+        self._send_json(measurement, 201)
+
+    def _handle_web_vitals_list(self) -> None:
+        if not self._check_auth():
+            return
+        with _WVM_LOCK:
+            measurements = [dict(measurement) for measurement in _WVM_MEASUREMENTS]
+        self._send_json({"measurements": measurements, "total": len(measurements)})
+
+    def _handle_web_vitals_delete(self, measurement_id: str) -> None:
+        if not self._check_auth():
+            return
+        with _WVM_LOCK:
+            index = next((i for i, measurement in enumerate(_WVM_MEASUREMENTS) if measurement["measurement_id"] == measurement_id), None)
+            if index is None:
+                self._send_json({"error": "measurement not found"}, 404)
+                return
+            _WVM_MEASUREMENTS.pop(index)
+        self._send_json({"status": "deleted", "measurement_id": measurement_id})
+
+    def _handle_web_vitals_stats(self) -> None:
+        if not self._check_auth():
+            return
+        with _WVM_LOCK:
+            measurements = [dict(measurement) for measurement in _WVM_MEASUREMENTS]
+        by_metric = {metric: 0 for metric in WVM_WEB_VITAL_METRICS}
+        by_rating = {rating: 0 for rating in WVM_VITAL_RATINGS}
+        totals_by_metric: dict[str, Decimal] = {metric: Decimal("0") for metric in WVM_WEB_VITAL_METRICS}
+        avg_by_metric: dict[str, str] = {metric: "0.00" for metric in WVM_WEB_VITAL_METRICS}
+        for measurement in measurements:
+            metric_type = measurement.get("metric_type", "")
+            rating = measurement.get("rating", "")
+            by_metric[metric_type] = by_metric.get(metric_type, 0) + 1
+            by_rating[rating] = by_rating.get(rating, 0) + 1
+            totals_by_metric[metric_type] = totals_by_metric.get(metric_type, Decimal("0")) + Decimal(measurement.get("value_ms", "0.00"))
+        for metric_type in WVM_WEB_VITAL_METRICS:
+            if by_metric[metric_type] > 0:
+                avg_by_metric[metric_type] = _tracker_decimal_str(totals_by_metric[metric_type] / Decimal(str(by_metric[metric_type])))
+        self._send_json({
+            "total_measurements": len(measurements),
+            "by_metric": by_metric,
+            "by_rating": by_rating,
+            "avg_by_metric": avg_by_metric,
+        })
+
+    def _handle_web_vitals_metric_types(self) -> None:
+        self._send_json({
+            "metric_types": WVM_WEB_VITAL_METRICS,
+            "ratings": WVM_VITAL_RATINGS,
+            "navigation_types": WVM_NAVIGATION_TYPES,
+        })
+
+    # ---------------------------------------------------------------------------
+    # Task 166 — Resource Timing Tracker handlers
+    # ---------------------------------------------------------------------------
+    def _handle_resource_timing_create(self, body: Optional[dict] = None) -> None:
+        if not self._check_auth():
+            return
+        if body is None:
+            body = self._read_json_body()
+        if body is None:
+            return
+        resource_type = str(body.get("resource_type", "")).strip()
+        if resource_type not in RTE_RESOURCE_TYPES:
+            self._send_json({"error": f"resource_type must be one of {RTE_RESOURCE_TYPES}"}, 400)
+            return
+        duration_ms, duration_error = _tracker_parse_non_negative_decimal(body.get("duration_ms"), "duration_ms")
+        if duration_error:
+            self._send_json({"error": duration_error}, 400)
+            return
+        transfer_size_bytes, transfer_error = _tracker_parse_int(body.get("transfer_size_bytes"), "transfer_size_bytes", 0)
+        if transfer_error:
+            self._send_json({"error": transfer_error}, 400)
+            return
+        cache_hit_default = transfer_size_bytes == 0
+        cache_hit, cache_error = _tracker_parse_bool(body.get("cache_hit", cache_hit_default), "cache_hit")
+        if cache_error:
+            self._send_json({"error": cache_error}, 400)
+            return
+        entry = {
+            "entry_id": "rte_" + str(uuid.uuid4()),
+            "resource_type": resource_type,
+            "url_hash": _tracker_sha256(body.get("url", "")),
+            "page_url_hash": _tracker_sha256(body.get("page_url", "")),
+            "duration_ms": _tracker_decimal_str(duration_ms),
+            "transfer_size_bytes": transfer_size_bytes,
+            "cache_hit": cache_hit,
+            "recorded_at": _tracker_now_iso(),
+        }
+        with _RTE_LOCK:
+            if len(_RTE_RESOURCE_ENTRIES) >= RTE_MAX_RESOURCE_ENTRIES:
+                _RTE_RESOURCE_ENTRIES.pop(0)
+            _RTE_RESOURCE_ENTRIES.append(entry)
+        self._send_json(entry, 201)
+
+    def _handle_resource_timing_list(self) -> None:
+        if not self._check_auth():
+            return
+        with _RTE_LOCK:
+            entries = [dict(entry) for entry in _RTE_RESOURCE_ENTRIES]
+        self._send_json({"entries": entries, "total": len(entries)})
+
+    def _handle_resource_timing_delete(self, entry_id: str) -> None:
+        if not self._check_auth():
+            return
+        with _RTE_LOCK:
+            index = next((i for i, entry in enumerate(_RTE_RESOURCE_ENTRIES) if entry["entry_id"] == entry_id), None)
+            if index is None:
+                self._send_json({"error": "entry not found"}, 404)
+                return
+            _RTE_RESOURCE_ENTRIES.pop(index)
+        self._send_json({"status": "deleted", "entry_id": entry_id})
+
+    def _handle_resource_timing_stats(self) -> None:
+        if not self._check_auth():
+            return
+        with _RTE_LOCK:
+            entries = [dict(entry) for entry in _RTE_RESOURCE_ENTRIES]
+        by_resource_type = {resource_type: 0 for resource_type in RTE_RESOURCE_TYPES}
+        duration_total = Decimal("0")
+        cache_hit_count = 0
+        total_transfer_bytes = 0
+        for entry in entries:
+            resource_type = entry.get("resource_type", "")
+            by_resource_type[resource_type] = by_resource_type.get(resource_type, 0) + 1
+            duration_total += Decimal(entry.get("duration_ms", "0.00"))
+            total_transfer_bytes += int(entry.get("transfer_size_bytes", 0))
+            if entry.get("cache_hit"):
+                cache_hit_count += 1
+        total_entries = len(entries)
+        avg_duration_ms = _tracker_decimal_str(duration_total / Decimal(str(total_entries))) if total_entries else "0.00"
+        cache_hit_rate = _tracker_decimal_str(Decimal(str(cache_hit_count)) / Decimal(str(total_entries))) if total_entries else "0.00"
+        self._send_json({
+            "total_entries": total_entries,
+            "by_resource_type": by_resource_type,
+            "avg_duration_ms": avg_duration_ms,
+            "cache_hit_rate": cache_hit_rate,
+            "total_transfer_bytes": total_transfer_bytes,
+        })
+
+    def _handle_resource_timing_types(self) -> None:
+        self._send_json({"resource_types": RTE_RESOURCE_TYPES})
+
+    # ---------------------------------------------------------------------------
+    # Task 167 — User Agent Tracker handlers
+    # ---------------------------------------------------------------------------
+    def _handle_user_agent_create(self, body: Optional[dict] = None) -> None:
+        if not self._check_auth():
+            return
+        if body is None:
+            body = self._read_json_body()
+        if body is None:
+            return
+        platform = str(body.get("platform", "")).strip()
+        if platform not in UAT_UA_PLATFORMS:
+            self._send_json({"error": f"platform must be one of {UAT_UA_PLATFORMS}"}, 400)
+            return
+        browser = str(body.get("browser", "")).strip()
+        if browser not in UAT_UA_BROWSERS:
+            self._send_json({"error": f"browser must be one of {UAT_UA_BROWSERS}"}, 400)
+            return
+        is_mobile, mobile_error = _tracker_parse_bool(body.get("is_mobile", False), "is_mobile")
+        if mobile_error:
+            self._send_json({"error": mobile_error}, 400)
+            return
+        is_spoofed, spoofed_error = _tracker_parse_bool(body.get("is_spoofed", False), "is_spoofed")
+        if spoofed_error:
+            self._send_json({"error": spoofed_error}, 400)
+            return
+        snapshot = {
+            "snapshot_id": "uat_" + str(uuid.uuid4()),
+            "ua_hash": _tracker_sha256(body.get("user_agent", "")),
+            "platform": platform,
+            "browser": browser,
+            "is_mobile": is_mobile,
+            "is_spoofed": is_spoofed,
+            "recorded_at": _tracker_now_iso(),
+        }
+        with _UAT_LOCK:
+            if len(_UAT_SNAPSHOTS) >= UAT_MAX_SNAPSHOTS:
+                _UAT_SNAPSHOTS.pop(0)
+            _UAT_SNAPSHOTS.append(snapshot)
+        self._send_json(snapshot, 201)
+
+    def _handle_user_agent_list(self) -> None:
+        if not self._check_auth():
+            return
+        with _UAT_LOCK:
+            snapshots = [dict(snapshot) for snapshot in _UAT_SNAPSHOTS]
+        self._send_json({"snapshots": snapshots, "total": len(snapshots)})
+
+    def _handle_user_agent_delete(self, snapshot_id: str) -> None:
+        if not self._check_auth():
+            return
+        with _UAT_LOCK:
+            index = next((i for i, snapshot in enumerate(_UAT_SNAPSHOTS) if snapshot["snapshot_id"] == snapshot_id), None)
+            if index is None:
+                self._send_json({"error": "snapshot not found"}, 404)
+                return
+            _UAT_SNAPSHOTS.pop(index)
+        self._send_json({"status": "deleted", "snapshot_id": snapshot_id})
+
+    def _handle_user_agent_stats(self) -> None:
+        if not self._check_auth():
+            return
+        with _UAT_LOCK:
+            snapshots = [dict(snapshot) for snapshot in _UAT_SNAPSHOTS]
+        by_platform = {platform: 0 for platform in UAT_UA_PLATFORMS}
+        by_browser = {browser: 0 for browser in UAT_UA_BROWSERS}
+        spoofed_count = 0
+        mobile_count = 0
+        for snapshot in snapshots:
+            platform = snapshot.get("platform", "")
+            browser = snapshot.get("browser", "")
+            by_platform[platform] = by_platform.get(platform, 0) + 1
+            by_browser[browser] = by_browser.get(browser, 0) + 1
+            if snapshot.get("is_spoofed"):
+                spoofed_count += 1
+            if snapshot.get("is_mobile"):
+                mobile_count += 1
+        self._send_json({
+            "total_snapshots": len(snapshots),
+            "by_platform": by_platform,
+            "by_browser": by_browser,
+            "spoofed_count": spoofed_count,
+            "mobile_count": mobile_count,
+        })
+
+    def _handle_user_agent_platforms(self) -> None:
+        self._send_json({"platforms": UAT_UA_PLATFORMS, "browsers": UAT_UA_BROWSERS})
+
 
 # ---------------------------------------------------------------------------
 # Server factory — theorem: build_server isolates configuration from startup.
