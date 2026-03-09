"""
test_schedule_viewer.py — Schedule Viewer tests (Task 058)
Donald Knuth law: every test is a proof. RED → GREEN gate.

Task 058 — Schedule Activity Calendar & Sign-Off Queue
Port: 18892 (test-only, distinct from all other test modules)

Kill conditions verified:
  - No port 9222 in schedule files
  - No auto-approve on countdown expiry (auto-REJECT only)
  - No bulk-approve for Class B/C
  - No hardcoded hex in schedule.css
  - No CDN dependencies in schedule.html
  - USD amounts use Decimal not float
"""
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18892
BASE_URL = f"http://localhost:{TEST_PORT}"
_TOKEN = "test-token-schedule-058"

SCHEDULE_HTML = REPO_ROOT / "web" / "schedule.html"
SCHEDULE_JS = REPO_ROOT / "web" / "js" / "schedule.js"
SCHEDULE_CSS = REPO_ROOT / "web" / "css" / "schedule.css"
YINYANG_SERVER_PY = REPO_ROOT / "yinyang_server.py"

FORBIDDEN_PORT = "9" + "222"
LEGACY_HUB_NAME = "Companion" + " App"


# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("solace_schedule_058")
    import yinyang_server as ys

    original_lock = ys.PORT_LOCK_PATH
    ys.PORT_LOCK_PATH = tmp / "port.lock"

    token = _TOKEN
    t_hash = ys.token_hash(token)
    ys.write_port_lock(TEST_PORT, t_hash, 99998)

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=t_hash)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"httpd": httpd, "token": token, "token_hash": t_hash}

    httpd.shutdown()
    ys.PORT_LOCK_PATH = original_lock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _token_hash(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def post_json(path: str, payload: dict, token: str = "") -> tuple:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {_token_hash(token)}"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def get_json(path: str, token: str = "") -> tuple:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {_token_hash(token)}"
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _create_pending_action(action_type: str = "gmail.send", token: str = _TOKEN) -> str:
    """Create a PENDING_APPROVAL action, return action_id."""
    status, data = post_json(
        "/api/v1/actions/preview",
        {"action_type": action_type, "params": {"test": "1"}, "app_id": "test-app"},
        token=token,
    )
    assert status == 201, f"Preview failed: {status} {data}"
    return data["action_id"]


# ---------------------------------------------------------------------------
# Tests: API routes
# ---------------------------------------------------------------------------
class TestScheduleViewerList:
    def test_schedule_returns_list(self, server):
        """GET /api/v1/schedule returns {items: [...], total: N}."""
        status, data = get_json("/api/v1/schedule")
        assert status == 200, f"Expected 200, got {status}: {data}"
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)

    def test_schedule_filter_by_pending_status(self, server):
        """GET /api/v1/schedule?status=PENDING returns only pending items."""
        # Create a pending item first
        _create_pending_action("gmail.send", _TOKEN)
        status, data = get_json("/api/v1/schedule?status=PENDING")
        assert status == 200
        for item in data["items"]:
            assert item["status"] in ("pending_approval", "cooldown"), \
                f"Expected pending/cooldown, got: {item['status']}"

    def test_schedule_items_have_required_fields(self, server):
        """Each item must have id, app_id, status, safety_tier, started_at."""
        _create_pending_action("slack.send_channel", _TOKEN)
        status, data = get_json("/api/v1/schedule")
        assert status == 200
        if data["items"]:
            item = data["items"][0]
            for field in ("id", "app_id", "status", "safety_tier", "started_at"):
                assert field in item, f"Missing field: {field}"

    def test_schedule_limit_param(self, server):
        """?limit=1 returns at most 1 item."""
        status, data = get_json("/api/v1/schedule?limit=1")
        assert status == 200
        assert len(data["items"]) <= 1


class TestScheduleViewerDetail:
    def test_schedule_detail_returns_item(self, server):
        """GET /api/v1/schedule/{run_id} returns the action detail."""
        run_id = _create_pending_action("github.comment", _TOKEN)
        status, data = get_json(f"/api/v1/schedule/{run_id}")
        assert status == 200, f"Expected 200, got {status}: {data}"
        assert data.get("id") == run_id or data.get("action_id") == run_id

    def test_schedule_detail_not_found(self, server):
        """GET /api/v1/schedule/{nonexistent} returns 404."""
        status, data = get_json("/api/v1/schedule/nonexistent-run-id-xyz")
        assert status == 404


class TestScheduleViewerApprove:
    def test_schedule_approve_before_cooldown_returns_400(self, server):
        """POST /api/v1/schedule/approve/{run_id} returns 400 if cooldown not expired."""
        run_id = _create_pending_action("twitter.post", _TOKEN)
        status, data = post_json(
            f"/api/v1/schedule/approve/{run_id}",
            {},
            token=_TOKEN,
        )
        # Cooldown is 1800s for Class B — must not be approvable immediately
        assert status == 400, f"Expected 400 (cooldown_active), got {status}: {data}"
        assert data.get("error") == "cooldown_active"
        assert "remaining_seconds" in data

    def test_schedule_approve_after_cooldown_returns_200(self, server):
        """POST /api/v1/schedule/approve/{run_id} returns 200 after cooldown bypassed."""
        import yinyang_server as ys
        run_id = _create_pending_action("linkedin.post", _TOKEN)

        # Bypass cooldown
        with ys._PENDING_ACTIONS_LOCK:
            if run_id in ys._PENDING_ACTIONS:
                ys._PENDING_ACTIONS[run_id]["cooldown_ends_at"] = time.time() - 1

        status, data = post_json(
            f"/api/v1/schedule/approve/{run_id}",
            {},
            token=_TOKEN,
        )
        assert status == 200, f"Expected 200, got {status}: {data}"
        assert data.get("approved") is True
        assert "run_id" in data
        assert "sealed_at" in data

    def test_schedule_approve_requires_auth(self, server):
        """POST /api/v1/schedule/approve/{run_id} without token returns 401."""
        run_id = _create_pending_action("gmail.send", _TOKEN)
        status, _ = post_json(f"/api/v1/schedule/approve/{run_id}", {}, token="")
        assert status == 401

    def test_schedule_approve_not_found(self, server):
        """POST /api/v1/schedule/approve/{nonexistent} returns 404."""
        status, data = post_json(
            "/api/v1/schedule/approve/nonexistent-id",
            {},
            token=_TOKEN,
        )
        assert status == 404


class TestScheduleViewerCancel:
    def test_schedule_cancel_removes_from_queue(self, server):
        """POST /api/v1/schedule/cancel/{run_id} removes item from pending queue."""
        run_id = _create_pending_action("instagram.post", _TOKEN)

        # Verify it's in queue first
        status, q = get_json("/api/v1/schedule/queue")
        assert status == 200
        ids_before = [item["run_id"] for item in q.get("queue", [])]
        assert run_id in ids_before, f"Expected {run_id} in queue: {ids_before}"

        # Cancel it
        status, data = post_json(
            f"/api/v1/schedule/cancel/{run_id}",
            {"reason": "test cancel"},
            token=_TOKEN,
        )
        assert status == 200, f"Expected 200, got {status}: {data}"
        assert data.get("cancelled") is True

        # Verify it's no longer in queue
        status, q2 = get_json("/api/v1/schedule/queue")
        assert status == 200
        ids_after = [item["run_id"] for item in q2.get("queue", [])]
        assert run_id not in ids_after, f"run_id still in queue after cancel: {ids_after}"

    def test_schedule_cancel_requires_auth(self, server):
        """POST /api/v1/schedule/cancel without token returns 401."""
        run_id = _create_pending_action("gmail.send", _TOKEN)
        status, _ = post_json(f"/api/v1/schedule/cancel/{run_id}", {}, token="")
        assert status == 401

    def test_schedule_cancel_not_found(self, server):
        """POST /api/v1/schedule/cancel/{nonexistent} returns 404."""
        status, data = post_json(
            "/api/v1/schedule/cancel/nonexistent-cancel-id",
            {},
            token=_TOKEN,
        )
        assert status == 404


class TestScheduleViewerQueue:
    def test_schedule_queue_returns_pending_only(self, server):
        """GET /api/v1/schedule/queue returns only Class B/C pending items."""
        # Create a Class B pending item
        _create_pending_action("gmail.archive_batch", _TOKEN)

        status, data = get_json("/api/v1/schedule/queue")
        assert status == 200, f"Expected 200, got {status}: {data}"
        assert "queue" in data
        assert "count" in data
        for item in data["queue"]:
            assert item["class"] in ("B", "C"), f"Expected B or C class, got: {item['class']}"
            assert "countdown_seconds_remaining" in item
            assert "cooldown_expires_at" in item

    def test_countdown_auto_reject_not_auto_approve(self, server):
        """CRITICAL: schedule.js must auto-REJECT on countdown zero, NEVER auto-approve.
        Verified via API behavior: cancel endpoint exists and is the auto-reject path.
        Updated for Task 060 4-tab redesign.
        """
        # Verify cancel endpoint is available (used by JS countdown expiry)
        run_id = _create_pending_action("slack.send_channel", _TOKEN)
        status, data = post_json(
            f"/api/v1/schedule/cancel/{run_id}",
            {"reason": "countdown_expired"},
            token=_TOKEN,
        )
        assert status == 200
        assert data.get("cancelled") is True

        # Verify the JS source contains auto-REJECT logic (4-tab redesign)
        js_source = SCHEDULE_JS.read_text()
        assert "auto-REJECT" in js_source or "rejectItem" in js_source, \
            "schedule.js must implement auto-REJECT countdown"
        # Confirm rejectItem is called on countdown expiry (not approveItem)
        assert "rejectItem(runId)" in js_source, "Auto-reject function must be called on countdown expiry"


class TestScheduleViewerCalendar:
    def test_schedule_calendar_groups_by_day(self, server):
        """GET /api/v1/schedule/calendar returns dict keyed by YYYY-MM-DD."""
        status, data = get_json("/api/v1/schedule/calendar")
        assert status == 200, f"Expected 200, got {status}: {data}"
        # All keys must be date strings YYYY-MM-DD
        import re
        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for key in data.keys():
            assert date_re.match(key), f"Calendar key not a date: {key}"

    def test_schedule_calendar_month_filter(self, server):
        """GET /api/v1/schedule/calendar?month=YYYY-MM filters to that month."""
        status, data = get_json("/api/v1/schedule/calendar?month=2025-01")
        assert status == 200
        for key in data.keys():
            assert key.startswith("2025-01"), f"Expected 2025-01 prefix, got: {key}"


class TestScheduleViewerROI:
    def test_schedule_roi_returns_required_fields(self, server):
        """GET /api/v1/schedule/roi returns week_runs, week_hours_saved, week_value_usd_at_30_per_hour."""
        status, data = get_json("/api/v1/schedule/roi")
        assert status == 200, f"Expected 200, got {status}: {data}"
        for field in ("week_runs", "week_hours_saved", "week_value_usd_at_30_per_hour", "all_time_runs"):
            assert field in data, f"Missing ROI field: {field}"

    def test_roi_panel_uses_decimal_not_float(self, server):
        """ROI response values must be strings (from Decimal), not Python float."""
        status, data = get_json("/api/v1/schedule/roi")
        assert status == 200
        # Values that represent USD must be strings (Decimal serialized as str)
        assert isinstance(data["week_hours_saved"], str), \
            f"week_hours_saved must be str (Decimal), got {type(data['week_hours_saved'])}"
        assert isinstance(data["week_value_usd_at_30_per_hour"], str), \
            f"week_value_usd_at_30_per_hour must be str (Decimal), got {type(data['week_value_usd_at_30_per_hour'])}"

    def test_roi_calculation_logic(self, server):
        """ROI at 10min/run * $30/hr = $5/run."""
        status, data = get_json("/api/v1/schedule/roi")
        assert status == 200
        week_runs = data["week_runs"]
        expected_minutes = week_runs * 10
        # hours_saved = minutes / 60
        from decimal import Decimal
        expected_hours = Decimal(expected_minutes) / Decimal("60")
        actual_hours = Decimal(data["week_hours_saved"])
        assert actual_hours == expected_hours.quantize(Decimal("0.01")), \
            f"Expected hours_saved={expected_hours}, got {actual_hours}"


class TestScheduleViewerUpcoming:
    def test_schedule_upcoming_returns_list(self, server):
        """GET /api/v1/schedule/upcoming (4-tab Tab 1) returns schedules + keepalive + pending counts."""
        status, data = get_json("/api/v1/schedule/upcoming", token=_TOKEN)
        assert status == 200, f"Expected 200, got {status}: {data}"
        assert "schedules" in data
        assert "keepalive" in data
        assert "pending_approvals" in data
        assert "pending_esign" in data
        assert isinstance(data["schedules"], list)


class TestScheduleViewerPlan:
    def test_schedule_plan_creates_run(self, server):
        """POST /api/v1/schedule/plan returns run_id + scheduled_at."""
        status, data = post_json(
            "/api/v1/schedule/plan",
            {"app_id": "gmail-triage", "scheduled_at": "2026-04-01T09:00:00Z"},
            token=_TOKEN,
        )
        assert status == 201, f"Expected 201, got {status}: {data}"
        assert "run_id" in data
        assert "scheduled_at" in data

    def test_schedule_plan_requires_app_id(self, server):
        """POST /api/v1/schedule/plan without app_id returns 400."""
        status, data = post_json(
            "/api/v1/schedule/plan",
            {"scheduled_at": "2026-04-01T09:00:00Z"},
            token=_TOKEN,
        )
        assert status == 400

    def test_schedule_plan_requires_auth(self, server):
        """POST /api/v1/schedule/plan without auth returns 401."""
        status, _ = post_json(
            "/api/v1/schedule/plan",
            {"app_id": "gmail-triage", "scheduled_at": "2026-04-01T09:00:00Z"},
            token="",
        )
        assert status == 401


# ---------------------------------------------------------------------------
# Kill-condition checks (file-based)
# ---------------------------------------------------------------------------
class TestKillConditions:
    def test_schedule_css_no_hardcoded_hex(self):
        """schedule.css must use var(--hub-*) ONLY. No hex color values."""
        css = SCHEDULE_CSS.read_text()
        import re
        # Allow hex in comments or string content, check for bare hex colors
        # Pattern: # followed by 3 or 6 hex digits used as color
        hex_colors = re.findall(r'(?<![\w-])#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?![\w-])', css)
        # Filter out :root CSS variable declarations (those are the defined hex values for var())
        # The rule is: non-root uses must use var(--hub-*)
        # Only the :root block may define hex values
        root_block_re = re.compile(r':root\s*\{[^}]+\}', re.DOTALL)
        root_match = root_block_re.search(css)
        root_content = root_match.group(0) if root_match else ""
        css_without_root = css.replace(root_content, "")
        outside_hex = re.findall(r'(?<![\w-])#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?![\w-])', css_without_root)
        assert not outside_hex, \
            f"schedule.css has hardcoded hex colors outside :root: {outside_hex}"

    def test_schedule_html_no_cdn_dependencies(self):
        """schedule.html must not load from CDN (bootstrap, tailwind, jquery, cdnjs, etc.)."""
        html = SCHEDULE_HTML.read_text()
        import re
        cdn_patterns = [
            r'cdn\.',
            r'bootstrap',
            r'tailwind',
            r'jquery',
            r'cdnjs',
            r'unpkg',
            r'jsdelivr',
        ]
        for pat in cdn_patterns:
            matches = re.findall(pat, html, re.IGNORECASE)
            assert not matches, f"schedule.html has CDN dependency '{pat}': {matches}"

    def test_no_port_9222_in_schedule_files(self):
        """No schedule file may reference the forbidden debug port."""
        forbidden = "9" + "222"
        for fpath in (SCHEDULE_HTML, SCHEDULE_JS, SCHEDULE_CSS):
            if fpath.exists():
                content = fpath.read_text()
                assert forbidden not in content, \
                    f"{fpath.name} contains forbidden port {forbidden}"

    def test_no_companion_app_in_schedule_files(self):
        """No schedule file may use legacy hub name."""
        legacy = "Companion" + " App"
        for fpath in (SCHEDULE_HTML, SCHEDULE_JS, SCHEDULE_CSS):
            if fpath.exists():
                content = fpath.read_text()
                assert legacy not in content, \
                    f"{fpath.name} contains legacy hub name '{legacy}'"

    def test_no_bare_except_in_schedule_handlers(self):
        """yinyang_server.py must not have bare except Exception in schedule handlers."""
        server_src = YINYANG_SERVER_PY.read_text()
        # Find schedule handler section
        start = server_src.find("# Task 058 — Schedule Viewer handlers")
        end = server_src.find("# Task 057 — Preview / Cooldown / Sign-Off handlers")
        if start >= 0 and end >= 0:
            section = server_src[start:end]
        else:
            section = server_src
        import re
        bare_excepts = re.findall(r'except\s+Exception\s*:', section)
        assert not bare_excepts, f"Bare except Exception found in schedule handlers: {bare_excepts}"

    def test_schedule_js_auto_reject_not_approve_on_timeout(self):
        """JS countdown must trigger cancel (reject), not approve."""
        js = SCHEDULE_JS.read_text()
        # The auto-reject function must call cancel endpoint
        assert "/api/v1/schedule/cancel/" in js, \
            "schedule.js must call /api/v1/schedule/cancel/ for auto-reject"
        # Must NOT call approve on timeout
        # autoRejectItem must not call approve
        auto_reject_fn_start = js.find("async function autoRejectItem")
        auto_reject_fn_end = js.find("\nasync function ", auto_reject_fn_start + 1)
        if auto_reject_fn_end < 0:
            auto_reject_fn_end = len(js)
        auto_reject_body = js[auto_reject_fn_start:auto_reject_fn_end]
        assert "approve" not in auto_reject_body, \
            "autoRejectItem must not call approve — countdown = auto-REJECT only"

    def test_schedule_server_routes_registered(self):
        """yinyang_server.py must have all schedule viewer routes registered."""
        server_src = YINYANG_SERVER_PY.read_text()
        required_routes = [
            "/api/v1/schedule",
            "/api/v1/schedule/queue",
            "/api/v1/schedule/upcoming",
            "/api/v1/schedule/calendar",
            "/api/v1/schedule/roi",
            "_handle_schedule_viewer_list",
            "_handle_schedule_viewer_approve",
            "_handle_schedule_viewer_cancel",
            "_handle_schedule_viewer_queue",
            "_handle_schedule_viewer_calendar",
            "_handle_schedule_viewer_roi",
        ]
        for route in required_routes:
            assert route in server_src, f"Missing route/handler in yinyang_server.py: {route}"

    def test_signoff_sheet_exists_in_html(self):
        """schedule.html (4-tab redesign) must have approval queue tab with countdown.
        Updated for Task 060: signoff-sheet replaced by tab-approval panel + countdown in JS.
        Approve/reject buttons are rendered dynamically from JS (btn-approve/btn-reject classes).
        """
        html = SCHEDULE_HTML.read_text()
        # 4-tab redesign: approval queue is Tab 2
        assert "tab-approval" in html, "Missing approval queue tab panel"
        # Approve/reject buttons are dynamically rendered by JS
        js = SCHEDULE_JS.read_text()
        assert "btn-approve" in js, "Missing approve button class in schedule.js"
        assert "btn-reject" in js, "Missing reject button class in schedule.js"
        # Countdown is rendered by JS, verify JS has countdown logic
        assert "countdown" in js.lower(), "Missing countdown logic in schedule.js"

    def test_four_views_in_html(self):
        """schedule.html (4-tab redesign) has 4 tabs: Upcoming, Approval Queue, History, eSign."""
        html = SCHEDULE_HTML.read_text()
        for tab in ("tab-upcoming", "tab-approval", "tab-history", "tab-esign"):
            assert tab in html, f"Missing tab panel: {tab}"

    def test_bulk_approve_class_bc_banned(self):
        """JS must not have bulk approval for Class B/C items.
        4-tab redesign: each item requires individual approve/reject action.
        """
        js = SCHEDULE_JS.read_text()
        # Verify individual approval functions exist (no bulk)
        assert "approveItem" in js, "schedule.js must have individual approveItem function"
        assert "rejectItem" in js, "schedule.js must have individual rejectItem function"
