"""tests/test_screenshot_scheduler.py — Task 126: Screenshot Scheduler | 10 tests"""
import sys
import json
import hashlib
import subprocess

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass


def make_handler():
    h = FakeHandler()
    ys._SS_SCHEDULES.clear()
    ys._SS_CAPTURES.clear()
    return h


def create_schedule(h, url="https://example.com", interval="5min"):
    h._body = json.dumps({"url": url, "interval": interval}).encode()
    h._handle_ss_schedule_create()
    return h._responses[-1]


def test_schedule_create():
    h = make_handler()
    code, data = create_schedule(h)
    assert code == 201
    assert data["schedule"]["schedule_id"].startswith("ssc_")


def test_schedule_url_hashed():
    h = make_handler()
    url = "https://secret.example.com/page"
    code, data = create_schedule(h, url=url)
    assert code == 201
    sched = data["schedule"]
    expected_hash = hashlib.sha256(url.encode()).hexdigest()
    assert sched["url_hash"] == expected_hash
    assert url not in str(sched)


def test_schedule_invalid_interval():
    h = make_handler()
    h._body = json.dumps({"url": "https://x.com", "interval": "99years"}).encode()
    h._handle_ss_schedule_create()
    code, data = h._responses[-1]
    assert code == 400


def test_schedule_list():
    h = make_handler()
    create_schedule(h, url="https://a.com")
    create_schedule(h, url="https://b.com")
    h2 = FakeHandler()
    h2._handle_ss_schedules_list()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] == 2
    assert len(data["schedules"]) == 2


def test_schedule_delete():
    h = make_handler()
    code, created = create_schedule(h)
    sched_id = created["schedule"]["schedule_id"]
    h2 = FakeHandler()
    h2._handle_ss_schedule_delete(sched_id)
    code2, data2 = h2._responses[-1]
    assert code2 == 200
    assert data2["schedule_id"] == sched_id
    assert len(ys._SS_SCHEDULES) == 0


def test_capture_create():
    h = make_handler()
    _, created = create_schedule(h)
    sched_id = created["schedule"]["schedule_id"]
    h2 = FakeHandler()
    h2._body = json.dumps({"schedule_id": sched_id, "image_data": "fake-binary"}).encode()
    h2._handle_ss_capture_create()
    code, data = h2._responses[-1]
    assert code == 201
    assert data["capture"]["capture_id"].startswith("scp_")
    # capture_count incremented
    sched = next(s for s in ys._SS_SCHEDULES if s["schedule_id"] == sched_id)
    assert sched["capture_count"] == 1


def test_capture_invalid_schedule():
    h = make_handler()
    h._body = json.dumps({"schedule_id": "ssc_notexist"}).encode()
    h._handle_ss_capture_create()
    code, data = h._responses[-1]
    assert code == 404


def test_capture_list():
    h = make_handler()
    _, created = create_schedule(h)
    sched_id = created["schedule"]["schedule_id"]
    h2 = FakeHandler()
    h2._body = json.dumps({"schedule_id": sched_id, "image_hash": "a" * 64}).encode()
    h2._handle_ss_capture_create()
    h3 = FakeHandler()
    h3._handle_ss_captures_list()
    code, data = h3._responses[-1]
    assert code == 200
    assert data["total"] == 1


def test_intervals_list():
    h = make_handler()
    h._handle_ss_intervals()
    code, data = h._responses[-1]
    assert code == 200
    assert len(data["intervals"]) == 9
    assert "daily" in data["intervals"]
    assert "weekly" in data["intervals"]


def test_no_port_9222_in_scheduler():
    result = subprocess.run(
        ["grep", "-c", "9222", "/home/phuc/projects/solace-browser/yinyang_server.py"],
        capture_output=True, text=True
    )
    count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
    assert count == 0, f"Found {count} occurrences of 9222 in yinyang_server.py"
