"""tests/test_privacy_dashboard.py — Task 077: Privacy Dashboard | 10 tests"""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0", "authorization": f"Bearer {VALID_TOKEN}"}

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
    ys._PRIVACY_EVENTS.clear()
    return h


def report(h, event_type="tracker_blocked", domain="evil.tracker.com", details="test"):
    h._body = json.dumps({
        "event_type": event_type,
        "domain": domain,
        "details": details,
    }).encode()
    h._handle_privacy_report()
    return h._responses[-1]


def test_privacy_report():
    h = make_handler()
    code, data = report(h)
    assert code == 201
    assert data["event_id"].startswith("prv_")


def test_privacy_domain_hashed():
    h = make_handler()
    domain = "tracker.secret.example.com"
    report(h, domain=domain)
    event = ys._PRIVACY_EVENTS[-1]
    expected = hashlib.sha256(domain.encode()).hexdigest()
    assert event["domain_hash"] == expected
    assert domain not in str(event)


def test_privacy_invalid_type():
    h = make_handler()
    h._body = json.dumps({"event_type": "unknown_type", "domain": "x.com"}).encode()
    h._handle_privacy_report()
    code, data = h._responses[-1]
    assert code == 400
    assert "event_type" in data["error"].lower()


def test_privacy_events_list():
    h = make_handler()
    report(h, event_type="tracker_blocked")
    report(h, event_type="cookie_cleared")
    h2 = FakeHandler()
    h2._handle_privacy_events_list()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] == 2
    assert len(data["events"]) == 2


def test_privacy_clear():
    h = make_handler()
    report(h)
    report(h)
    h2 = FakeHandler()
    h2._handle_privacy_events_clear()
    code, data = h2._responses[-1]
    assert code == 200
    assert len(ys._PRIVACY_EVENTS) == 0


def test_privacy_summary():
    h = make_handler()
    report(h, event_type="tracker_blocked")
    report(h, event_type="tracker_blocked")
    report(h, event_type="cookie_cleared")
    h2 = FakeHandler()
    h2._handle_privacy_summary()
    code, data = h2._responses[-1]
    assert code == 200
    assert "privacy_score" in data
    assert "by_type" in data
    assert data["by_type"]["tracker_blocked"] == 2
    assert data["by_type"]["cookie_cleared"] == 1


def test_privacy_event_types():
    h = make_handler()
    h._handle_privacy_event_types()
    code, data = h._responses[-1]
    assert code == 200
    types = data["event_types"]
    assert len(types) == 7
    assert "tracker_blocked" in types
    assert "dns_leak_detected" in types


def test_privacy_details_hashed():
    h = make_handler()
    details = "sensitive-detail-string"
    report(h, details=details)
    event = ys._PRIVACY_EVENTS[-1]
    expected = hashlib.sha256(details.encode()).hexdigest()
    assert event["details_hash"] == expected
    assert details not in str(event)


def test_privacy_score_bounded():
    h = make_handler()
    # Add 100 events — score should cap at 100
    for i in range(100):
        report(h, event_type="tracker_blocked", domain=f"tracker{i}.com")
    h2 = FakeHandler()
    h2._handle_privacy_summary()
    _, data = h2._responses[-1]
    assert data["privacy_score"] <= 100


def test_no_port_9222_in_privacy():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        source = f.read()
    assert "9222" not in source
