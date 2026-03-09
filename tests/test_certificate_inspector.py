"""tests/test_certificate_inspector.py — Task 078: Certificate Inspector | 10 tests"""
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
    ys._CERTIFICATES.clear()
    return h


def record(h, domain="example.com", grade="A", validity_days=365):
    h._body = json.dumps({
        "domain": domain,
        "fingerprint": "fp:sha256:abc123",
        "issuer": "CN=Let's Encrypt",
        "subject": f"CN={domain}",
        "grade": grade,
        "validity_days_remaining": validity_days,
    }).encode()
    h._handle_cert_record()
    return h._responses[-1]


def test_cert_record():
    h = make_handler()
    code, data = record(h)
    assert code == 201
    assert data["cert_id"].startswith("crt_")


def test_cert_domain_hashed():
    h = make_handler()
    domain = "secret.internal.example.com"
    record(h, domain=domain)
    cert = ys._CERTIFICATES[-1]
    expected = hashlib.sha256(domain.encode()).hexdigest()
    assert cert["domain_hash"] == expected
    assert domain not in str(cert)


def test_cert_invalid_grade():
    h = make_handler()
    h._body = json.dumps({
        "domain": "x.com",
        "grade": "Z",
        "validity_days_remaining": 365,
    }).encode()
    h._handle_cert_record()
    code, data = h._responses[-1]
    assert code == 400
    assert "grade" in data["error"].lower()


def test_cert_list():
    h = make_handler()
    record(h, domain="a.com")
    record(h, domain="b.com")
    h2 = FakeHandler()
    h2._handle_cert_list()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] == 2


def test_cert_get():
    h = make_handler()
    code, created = record(h)
    cert_id = created["cert_id"]
    h2 = FakeHandler()
    h2._handle_cert_get(cert_id)
    code2, data2 = h2._responses[-1]
    assert code2 == 200
    assert data2["certificate"]["cert_id"] == cert_id


def test_cert_not_found():
    h = make_handler()
    h._handle_cert_get("crt_notexist")
    code, data = h._responses[-1]
    assert code == 404


def test_cert_delete():
    h = make_handler()
    code, created = record(h)
    cert_id = created["cert_id"]
    h2 = FakeHandler()
    h2._handle_cert_delete(cert_id)
    code2, data2 = h2._responses[-1]
    assert code2 == 200
    assert len(ys._CERTIFICATES) == 0


def test_cert_alerts_expiring():
    h = make_handler()
    record(h, domain="expiring.com", grade="A", validity_days=10)
    h2 = FakeHandler()
    h2._handle_cert_alerts()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] >= 1
    assert any(a["alert_type"] is not None for a in data["alerts"])


def test_cert_alerts_bad_grade():
    h = make_handler()
    record(h, domain="bad-grade.com", grade="F", validity_days=200)
    h2 = FakeHandler()
    h2._handle_cert_alerts()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] >= 1
    # F grade → in alerts
    assert any(a["grade"] == "F" for a in data["alerts"])


def test_no_port_9222_in_cert():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        source = f.read()
    assert "9222" not in source
