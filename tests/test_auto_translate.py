"""tests/test_auto_translate.py — Task 128: Auto Translate | 10 tests"""
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
    ys._TRANSLATE_PREFS.clear()
    ys._TRANSLATE_LOG.clear()
    return h


def create_pref(h, source="en", target="fr", engine="google", site_domain="example.com"):
    h._body = json.dumps({
        "source_language": source,
        "target_language": target,
        "engine": engine,
        "site_domain": site_domain,
    }).encode()
    h._handle_translate_pref_create()
    return h._responses[-1]


def test_pref_create():
    h = make_handler()
    code, data = create_pref(h)
    assert code == 201
    assert data["preference"]["pref_id"].startswith("atp_")


def test_pref_site_hashed():
    h = make_handler()
    domain = "example.com"
    code, data = create_pref(h, site_domain=domain)
    assert code == 201
    pref = data["preference"]
    expected = hashlib.sha256(domain.encode()).hexdigest()
    assert pref["site_hash"] == expected
    assert domain not in str(pref)


def test_pref_invalid_source():
    h = make_handler()
    h._body = json.dumps({
        "source_language": "klingon",
        "target_language": "fr",
        "engine": "google",
    }).encode()
    h._handle_translate_pref_create()
    code, data = h._responses[-1]
    assert code == 400


def test_pref_invalid_target():
    h = make_handler()
    h._body = json.dumps({
        "source_language": "en",
        "target_language": "klingon",
        "engine": "google",
    }).encode()
    h._handle_translate_pref_create()
    code, data = h._responses[-1]
    assert code == 400


def test_pref_same_language():
    h = make_handler()
    h._body = json.dumps({
        "source_language": "en",
        "target_language": "en",
        "engine": "google",
    }).encode()
    h._handle_translate_pref_create()
    code, data = h._responses[-1]
    assert code == 400


def test_pref_list():
    h = make_handler()
    create_pref(h, source="en", target="fr")
    create_pref(h, source="de", target="es")
    h2 = FakeHandler()
    h2._handle_translate_prefs_list()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] == 2


def test_pref_delete():
    h = make_handler()
    code, created = create_pref(h)
    pref_id = created["preference"]["pref_id"]
    h2 = FakeHandler()
    h2._handle_translate_pref_delete(pref_id)
    code2, data2 = h2._responses[-1]
    assert code2 == 200
    assert data2["pref_id"] == pref_id
    assert len(ys._TRANSLATE_PREFS) == 0


def test_translation_log():
    h = make_handler()
    h._body = json.dumps({
        "source_language": "en",
        "target_language": "fr",
        "engine": "deepl",
        "word_count": 150,
        "page_url": "https://example.com/page",
    }).encode()
    h._handle_translate_log_create()
    code, data = h._responses[-1]
    assert code == 201
    assert data["translation"]["translation_id"].startswith("atl_")


def test_translation_stats():
    h = make_handler()
    h._body = json.dumps({
        "source_language": "en",
        "target_language": "fr",
        "engine": "google",
        "word_count": 100,
    }).encode()
    h._handle_translate_log_create()
    h._body = json.dumps({
        "source_language": "de",
        "target_language": "es",
        "engine": "deepl",
        "word_count": 200,
    }).encode()
    h._handle_translate_log_create()
    h2 = FakeHandler()
    h2._handle_translate_stats()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total_translations"] == 2
    assert data["total_words"] == 300
    assert "google" in data["by_engine"]
    assert "deepl" in data["by_engine"]
    assert "en-fr" in data["by_language_pair"]


def test_no_port_9222_in_translate():
    result = subprocess.run(
        ["grep", "-c", "9222", "/home/phuc/projects/solace-browser/yinyang_server.py"],
        capture_output=True, text=True
    )
    count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
    assert count == 0, f"Found {count} occurrences of 9222 in yinyang_server.py"
