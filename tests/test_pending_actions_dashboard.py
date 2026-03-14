# Diagram: 05-solace-runtime-architecture
"""tests/test_pending_actions_dashboard.py — Task 068: Pending Actions Dashboard."""
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18896
BASE_URL = f"http://localhost:{TEST_PORT}"
VALID_TOKEN = "a" * 64


@pytest.fixture(scope="module")
def yinyang_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("solace_pending_actions_068")
    import yinyang_server as ys

    original_lock = ys.PORT_LOCK_PATH
    ys.PORT_LOCK_PATH = tmp / "port.lock"

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"httpd": httpd, "base_url": BASE_URL}

    httpd.shutdown()
    ys.PORT_LOCK_PATH = original_lock


def test_pending_actions_html_exists():
    assert (REPO_ROOT / "web/pending-actions.html").exists()


def test_html_no_cdn():
    content = (REPO_ROOT / "web/pending-actions.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content


def test_html_no_jquery():
    content = (REPO_ROOT / "web/pending-actions.html").read_text(encoding="utf-8")
    assert "jQuery" not in content and "jquery" not in content


def test_html_uses_hub_tokens():
    content = (REPO_ROOT / "web/pending-actions.html").read_text(encoding="utf-8")
    assert "var(--hub-" in content


def test_html_has_approve_button():
    content = (REPO_ROOT / "web/pending-actions.html").read_text(encoding="utf-8")
    assert "btn-approve" in content or "Approve" in content


def test_html_has_reject_button():
    content = (REPO_ROOT / "web/pending-actions.html").read_text(encoding="utf-8")
    assert "btn-reject" in content or "Reject" in content


def test_html_calls_actions_api():
    content = (REPO_ROOT / "web/pending-actions.html").read_text(encoding="utf-8")
    assert "/api/v1/actions/pending" in content


def test_html_no_eval():
    content = (REPO_ROOT / "web/pending-actions.html").read_text(encoding="utf-8")
    assert "eval(" not in content


def test_html_has_cooldown():
    content = (REPO_ROOT / "web/pending-actions.html").read_text(encoding="utf-8")
    assert "cooldown" in content.lower()


def test_route_serves_html(yinyang_server):
    response = urllib.request.urlopen(f"http://localhost:{TEST_PORT}/web/pending-actions.html", timeout=3)
    assert response.status == 200
    content_type = response.headers.get("Content-Type", "")
    assert "text/html" in content_type
