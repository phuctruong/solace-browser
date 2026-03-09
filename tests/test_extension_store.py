"""tests/test_extension_store.py — Task 080: Extension Store | 10 tests"""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64
TOKEN_HASH = hashlib.sha256(VALID_TOKEN.encode()).hexdigest()


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
    ys._EXT_LISTINGS.clear()
    ys._EXT_INSTALLS.clear()
    return h


def publish(h, name="My Extension", category="productivity", version="1.0.0"):
    h._body = json.dumps({
        "name": name,
        "category": category,
        "version": version,
        "manifest": '{"name": "' + name + '"}',
        "rating": "4.50",
    }).encode()
    h._handle_ext_listing_publish()
    return h._responses[-1]


def test_ext_publish():
    h = make_handler()
    code, data = publish(h)
    assert code == 201
    assert data["ext_id"].startswith("ext_")


def test_ext_list():
    h = make_handler()
    publish(h, name="Ext A")
    publish(h, name="Ext B")
    h2 = FakeHandler()
    h2._handle_ext_listings_list()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] == 2
    assert len(data["listings"]) == 2


def test_ext_get():
    h = make_handler()
    code, created = publish(h)
    ext_id = created["ext_id"]
    h2 = FakeHandler()
    h2._handle_ext_listing_get(ext_id)
    code2, data2 = h2._responses[-1]
    assert code2 == 200
    assert data2["extension"]["ext_id"] == ext_id


def test_ext_invalid_category():
    h = make_handler()
    h._body = json.dumps({
        "name": "Bad Ext",
        "category": "games",
        "version": "1.0.0",
        "manifest": "{}",
    }).encode()
    h._handle_ext_listing_publish()
    code, data = h._responses[-1]
    assert code == 400
    assert "category" in data["error"].lower()


def test_ext_install():
    h = make_handler()
    code, created = publish(h)
    ext_id = created["ext_id"]
    h2 = FakeHandler()
    h2._handle_ext_install(ext_id)
    code2, data2 = h2._responses[-1]
    assert code2 == 201
    assert data2["status"] == "installed"
    assert data2["ext_id"] == ext_id


def test_ext_duplicate_install():
    h = make_handler()
    code, created = publish(h)
    ext_id = created["ext_id"]
    h2 = FakeHandler()
    h2._handle_ext_install(ext_id)
    # Second install — same token
    h3 = FakeHandler()
    h3._handle_ext_install(ext_id)
    code3, data3 = h3._responses[-1]
    assert code3 == 409
    assert "already" in data3["error"].lower()


def test_ext_installed_list():
    h = make_handler()
    code, created = publish(h)
    ext_id = created["ext_id"]
    h2 = FakeHandler()
    h2._handle_ext_install(ext_id)
    h3 = FakeHandler()
    h3._handle_ext_installed_list()
    code3, data3 = h3._responses[-1]
    assert code3 == 200
    assert data3["total"] == 1
    assert data3["installed"][0]["ext_id"] == ext_id


def test_ext_uninstall():
    h = make_handler()
    code, created = publish(h)
    ext_id = created["ext_id"]
    h2 = FakeHandler()
    h2._handle_ext_install(ext_id)
    h3 = FakeHandler()
    h3._handle_ext_uninstall(ext_id)
    code3, data3 = h3._responses[-1]
    assert code3 == 200
    assert data3["status"] == "uninstalled"
    assert TOKEN_HASH not in ys._EXT_INSTALLS or ext_id not in ys._EXT_INSTALLS.get(TOKEN_HASH, [])


def test_ext_uninstall_not_found():
    h = make_handler()
    h._handle_ext_uninstall("ext_notinstalled")
    code, data = h._responses[-1]
    assert code == 404
    assert "not installed" in data["error"].lower()


def test_no_port_9222_in_ext_store():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        source = f.read()
    assert "9222" not in source
