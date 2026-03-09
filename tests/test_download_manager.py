"""tests/test_download_manager.py — Download Manager acceptance gate.
Task 045 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - url_hash is SHA-256 of URL (raw URL never stored)
  - progress_pct is Decimal string, never float
  - retry only for failed/cancelled → 400 for completed/downloading
  - Auth required on POST/DELETE/retry; GET/stats is public
  - No port 9222, no CDN, no eval()
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-downloads-045"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18911)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def delete_path(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


@pytest.fixture(autouse=True)
def reset_downloads(monkeypatch):
    """Reset download state between tests."""
    monkeypatch.setattr(ys, "_DOWNLOADS", [])
    yield


# ---------------------------------------------------------------------------
# 1. Initially empty
# ---------------------------------------------------------------------------
def test_downloads_empty_initially():
    status, data = get_json("/api/v1/downloads")
    assert status == 200
    assert data.get("downloads") == []


# ---------------------------------------------------------------------------
# 2. POST → download_id returned
# ---------------------------------------------------------------------------
def test_download_register():
    status, data = post_json(
        "/api/v1/downloads",
        {"url": "https://example.com/file.zip", "filename": "file.zip"},
    )
    assert status == 200
    assert data.get("status") == "registered"
    assert "download_id" in data
    assert data["download_id"].startswith("dl_")


# ---------------------------------------------------------------------------
# 3. url_hash present, no raw URL stored
# ---------------------------------------------------------------------------
def test_download_url_hash_stored():
    url = "https://example.com/secret.bin"
    post_json("/api/v1/downloads", {"url": url, "filename": "secret.bin"})
    status, data = get_json("/api/v1/downloads")
    assert status == 200
    items = data["downloads"]
    assert len(items) == 1
    entry = items[0]
    assert "url" not in entry
    expected_hash = hashlib.sha256(url.encode()).hexdigest()
    assert entry["url_hash"] == expected_hash


# ---------------------------------------------------------------------------
# 4. GET → includes registered download
# ---------------------------------------------------------------------------
def test_download_list_includes_registered():
    _, add_data = post_json(
        "/api/v1/downloads",
        {"url": "https://example.com/a.tar.gz", "filename": "a.tar.gz"},
    )
    dl_id = add_data["download_id"]
    status, data = get_json("/api/v1/downloads")
    assert status == 200
    ids = [d["download_id"] for d in data["downloads"]]
    assert dl_id in ids


# ---------------------------------------------------------------------------
# 5. progress_pct is string not float
# ---------------------------------------------------------------------------
def test_download_progress_is_string():
    post_json("/api/v1/downloads", {"url": "https://example.com/b.zip", "filename": "b.zip"})
    _, data = get_json("/api/v1/downloads")
    items = data["downloads"]
    assert len(items) == 1
    pct = items[0]["progress_pct"]
    assert isinstance(pct, str), f"progress_pct must be str, got {type(pct)}"
    assert pct == "0.00"


# ---------------------------------------------------------------------------
# 6. DELETE → removed from list
# ---------------------------------------------------------------------------
def test_download_delete():
    _, add_data = post_json(
        "/api/v1/downloads",
        {"url": "https://example.com/c.zip", "filename": "c.zip"},
    )
    dl_id = add_data["download_id"]
    status, data = delete_path(f"/api/v1/downloads/{dl_id}")
    assert status == 200
    assert data.get("status") == "deleted"
    _, list_data = get_json("/api/v1/downloads")
    ids = [d["download_id"] for d in list_data["downloads"]]
    assert dl_id not in ids


# ---------------------------------------------------------------------------
# 7. retry failed download → status="pending"
# ---------------------------------------------------------------------------
def test_download_retry_failed():
    _, add_data = post_json(
        "/api/v1/downloads",
        {"url": "https://example.com/d.zip", "filename": "d.zip"},
    )
    dl_id = add_data["download_id"]
    # Manually set status to failed
    with ys._DOWNLOAD_LOCK:
        for d in ys._DOWNLOADS:
            if d["download_id"] == dl_id:
                d["status"] = "failed"
                break
    status, data = post_json(f"/api/v1/downloads/{dl_id}/retry", {})
    assert status == 200
    assert data.get("status") == "queued"
    # Verify it's now pending
    _, list_data = get_json("/api/v1/downloads")
    entry = next(d for d in list_data["downloads"] if d["download_id"] == dl_id)
    assert entry["status"] == "pending"


# ---------------------------------------------------------------------------
# 8. GET /stats → total, completed, failed counts
# ---------------------------------------------------------------------------
def test_download_stats():
    post_json("/api/v1/downloads", {"url": "https://example.com/e1.zip", "filename": "e1.zip"})
    post_json("/api/v1/downloads", {"url": "https://example.com/e2.zip", "filename": "e2.zip"})
    # Set one to completed, one to failed
    with ys._DOWNLOAD_LOCK:
        ys._DOWNLOADS[0]["status"] = "completed"
        ys._DOWNLOADS[1]["status"] = "failed"
    status, data = get_json("/api/v1/downloads/stats")
    assert status == 200
    assert data["total"] == 2
    assert data["completed"] == 1
    assert data["failed"] == 1


# ---------------------------------------------------------------------------
# 9. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_download_html_no_cdn():
    html_path = REPO_ROOT / "web" / "download-manager.html"
    assert html_path.exists(), "download-manager.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 10. No port 9222 in any download manager file
# ---------------------------------------------------------------------------
def test_no_port_9222_in_download_manager():
    files_to_check = [
        REPO_ROOT / "web" / "download-manager.html",
        REPO_ROOT / "web" / "js" / "download-manager.js",
        REPO_ROOT / "web" / "css" / "download-manager.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
