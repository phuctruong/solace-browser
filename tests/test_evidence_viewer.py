"""tests/test_evidence_viewer.py — Task 070: Evidence Viewer Page."""
import pathlib
import json
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18898
VALID_TOKEN = "e" * 64


@pytest.fixture(scope="module")
def evidence_server():
    import yinyang_server as ys

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://localhost:{TEST_PORT}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield httpd

    httpd.shutdown()


def test_evidence_viewer_html_exists():
    assert (REPO_ROOT / "web/evidence-viewer.html").exists()


def test_html_no_cdn():
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content and "unpkg.com" not in content


def test_html_no_jquery():
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "jQuery" not in content


def test_html_uses_hub_tokens():
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "var(--hub-" in content


def test_html_calls_evidence_api():
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "/api/v1/evidence/log" in content


def test_html_has_verify():
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "verify" in content.lower() and "Verify" in content


def test_html_no_eval():
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "eval(" not in content


def test_html_has_hash():
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "hash" in content.lower()


def test_html_has_filter():
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "filter" in content.lower()


def test_route_serves_html(evidence_server):
    response = urllib.request.urlopen(f"http://localhost:{TEST_PORT}/web/evidence-viewer.html", timeout=3)
    assert response.status == 200
    assert "text/html" in response.headers.get("Content-Type", "")


def test_evidence_log_alias_returns_json(evidence_server):
    response = urllib.request.urlopen(f"http://localhost:{TEST_PORT}/api/v1/evidence/log?limit=1", timeout=3)
    payload = json.loads(response.read().decode("utf-8"))
    assert response.status == 200
    assert "application/json" in response.headers.get("Content-Type", "")
    assert "entries" in payload
