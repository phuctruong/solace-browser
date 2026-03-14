# Diagram: 05-solace-runtime-architecture
"""tests/test_url_categorizer.py — Task 079: URL Categorizer | 10 tests"""
import sys
import json
import hashlib
from decimal import Decimal

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
    ys._URL_HISTORY.clear()
    return h


def categorize(h, url="https://github.com", domain="github.com",
               category="technology", confidence="0.90"):
    h._body = json.dumps({
        "url": url,
        "domain": domain,
        "category": category,
        "confidence_score": confidence,
    }).encode()
    h._handle_url_cat_categorize()
    return h._responses[-1]


def test_url_categorize():
    h = make_handler()
    code, data = categorize(h)
    assert code == 201
    assert data["entry_id"].startswith("urc_")


def test_url_hashed():
    h = make_handler()
    url = "https://private.internal.example.com/secret-path"
    categorize(h, url=url)
    entry = ys._URL_HISTORY[-1]
    expected = hashlib.sha256(url.encode()).hexdigest()
    assert entry["url_hash"] == expected
    assert url not in str(entry)


def test_url_domain_hashed():
    h = make_handler()
    domain = "internal.secret.corp"
    categorize(h, domain=domain)
    entry = ys._URL_HISTORY[-1]
    expected = hashlib.sha256(domain.encode()).hexdigest()
    assert entry["domain_hash"] == expected
    assert domain not in str(entry)


def test_url_invalid_category():
    h = make_handler()
    h._body = json.dumps({
        "url": "https://x.com",
        "domain": "x.com",
        "category": "malware",
    }).encode()
    h._handle_url_cat_categorize()
    code, data = h._responses[-1]
    assert code == 400
    assert "category" in data["error"].lower()


def test_url_history_list():
    h = make_handler()
    categorize(h, url="https://a.com", domain="a.com", category="news")
    categorize(h, url="https://b.com", domain="b.com", category="finance")
    h2 = FakeHandler()
    h2._handle_url_cat_history()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] == 2
    assert len(data["history"]) == 2


def test_url_history_clear():
    h = make_handler()
    categorize(h)
    h2 = FakeHandler()
    h2._handle_url_cat_history_clear()
    code, data = h2._responses[-1]
    assert code == 200
    assert len(ys._URL_HISTORY) == 0


def test_url_summary():
    h = make_handler()
    categorize(h, category="news")
    categorize(h, category="news")
    categorize(h, url="https://shop.com", domain="shop.com", category="shopping")
    h2 = FakeHandler()
    h2._handle_url_cat_summary()
    code, data = h2._responses[-1]
    assert code == 200
    assert "by_category" in data
    assert data["by_category"]["news"] == 2
    assert data["by_category"]["shopping"] == 1
    assert data["total"] == 3


def test_url_categories_list():
    h = make_handler()
    h._handle_url_cat_categories()
    code, data = h._responses[-1]
    assert code == 200
    cats = data["categories"]
    assert len(cats) == 11
    assert "productivity" in cats
    assert "other" in cats


def test_url_confidence_score_format():
    h = make_handler()
    categorize(h, confidence="0.75")
    entry = ys._URL_HISTORY[-1]
    score = entry["confidence_score"]
    # Must be a Decimal-string with 2 decimal places
    parsed = Decimal(score)
    assert "." in score
    assert 0 <= float(score) <= 1
    assert len(score.split(".")[1]) == 2


def test_no_port_9222_in_url_cat():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        source = f.read()
    assert "9222" not in source
