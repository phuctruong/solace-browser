"""Tests for Task 085 — AI Page Summarizer."""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "e" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0", "Authorization": f"Bearer {VALID_TOKEN}"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass


def make_handler(body=None):
    h = FakeHandler()
    if body is not None:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def clear_state():
    with ys._SUMMARIZER_LOCK:
        ys._PAGE_SUMMARIES.clear()


SAMPLE_BODY = {
    "model": "sonnet",
    "length_type": "standard",
    "page_url": "https://example.com/article",
    "page_title": "Example Article",
    "page_content": "This is the content of the article.",
    "summary": "The article is about examples.",
    "word_count": 7,
}


def test_summarizer_record():
    """POST → psum_ prefix returned."""
    clear_state()
    h = make_handler(SAMPLE_BODY)
    h._handle_summarizer_record()
    code, data = h._responses[0]
    assert code == 201
    assert data["summary_id"].startswith("psum_")


def test_summarizer_url_hashed():
    """url_hash present, no raw URL stored."""
    clear_state()
    h = make_handler(SAMPLE_BODY)
    h._handle_summarizer_record()
    with ys._SUMMARIZER_LOCK:
        entry = ys._PAGE_SUMMARIES[-1]
    assert "url_hash" in entry
    assert "page_url" not in entry
    expected = hashlib.sha256("https://example.com/article".encode()).hexdigest()
    assert entry["url_hash"] == expected


def test_summarizer_summary_hashed():
    """summary_hash present, no raw summary stored."""
    clear_state()
    h = make_handler(SAMPLE_BODY)
    h._handle_summarizer_record()
    with ys._SUMMARIZER_LOCK:
        entry = ys._PAGE_SUMMARIES[-1]
    assert "summary_hash" in entry
    assert "summary" not in entry
    expected = hashlib.sha256("The article is about examples.".encode()).hexdigest()
    assert entry["summary_hash"] == expected


def test_summarizer_invalid_model():
    """Unknown model → 400."""
    clear_state()
    body = dict(SAMPLE_BODY, model="gemini-ultra")
    h = make_handler(body)
    h._handle_summarizer_record()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_summarizer_invalid_length_type():
    """Unknown length_type → 400."""
    clear_state()
    body = dict(SAMPLE_BODY, length_type="super_detailed")
    h = make_handler(body)
    h._handle_summarizer_record()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_summarizer_history():
    """GET /history → list returned."""
    clear_state()
    save = make_handler(SAMPLE_BODY)
    save._handle_summarizer_record()
    h = make_handler()
    h._handle_summarizer_history()
    code, data = h._responses[0]
    assert code == 200
    assert "summaries" in data
    assert len(data["summaries"]) >= 1


def test_summarizer_delete():
    """DELETE → removed."""
    clear_state()
    save = make_handler(SAMPLE_BODY)
    save._handle_summarizer_record()
    summary_id = save._responses[0][1]["summary_id"]
    h = make_handler()
    h._handle_summarizer_delete(summary_id)
    code, data = h._responses[0]
    assert code == 200
    assert data["status"] == "deleted"
    with ys._SUMMARIZER_LOCK:
        ids = [s["summary_id"] for s in ys._PAGE_SUMMARIES]
    assert summary_id not in ids


def test_summarizer_delete_not_found():
    """DELETE psum_notexist → 404."""
    clear_state()
    h = make_handler()
    h._handle_summarizer_delete("psum_doesnotexist")
    code, data = h._responses[0]
    assert code == 404
    assert "error" in data


def test_summarizer_stats():
    """GET /stats → by_model present."""
    clear_state()
    save = make_handler(SAMPLE_BODY)
    save._handle_summarizer_record()
    h = make_handler()
    h._handle_summarizer_stats()
    code, data = h._responses[0]
    assert code == 200
    assert "total" in data
    assert "by_model" in data
    assert data["total"] >= 1
    assert "sonnet" in data["by_model"]


def test_no_port_9222_in_summarizer():
    """No port 9222 in AI page summarizer code."""
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found — BANNED"
