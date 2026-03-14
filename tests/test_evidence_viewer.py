# Diagram: 05-solace-runtime-architecture
"""tests/test_evidence_viewer.py — Task 016: Evidence Viewer UI (stats + export + JS/CSS routes)."""
import json
import pathlib
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


# ---------------------------------------------------------------------------
# Static file checks (no server needed)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Task 016 spec tests (10 required)
# ---------------------------------------------------------------------------


def test_evidence_list_endpoint_exists(evidence_server):
    """Test 1: GET /api/v1/evidence returns 200."""
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence", timeout=3
    )
    assert response.status == 200
    assert "application/json" in response.headers.get("Content-Type", "")


def test_evidence_stats_endpoint_exists(evidence_server):
    """Test 2: GET /api/v1/evidence/stats returns 200."""
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence/stats", timeout=3
    )
    assert response.status == 200
    assert "application/json" in response.headers.get("Content-Type", "")


def test_evidence_stats_has_total(evidence_server):
    """Test 3: response has 'total' field (int)."""
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence/stats", timeout=3
    )
    payload = json.loads(response.read().decode("utf-8"))
    assert "total" in payload
    assert isinstance(payload["total"], int)


def test_evidence_export_returns_json(evidence_server):
    """Test 4: GET /api/v1/evidence/export returns JSON."""
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence/export", timeout=3
    )
    assert response.status == 200
    assert "application/json" in response.headers.get("Content-Type", "")
    payload = json.loads(response.read().decode("utf-8"))
    assert isinstance(payload, dict)


def test_evidence_list_pagination(evidence_server):
    """Test 5: GET /api/v1/evidence?limit=5 returns max 5 entries."""
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence?limit=5", timeout=3
    )
    payload = json.loads(response.read().decode("utf-8"))
    entries = payload.get("entries", payload.get("records", []))
    assert isinstance(entries, list)
    assert len(entries) <= 5


def test_evidence_viewer_html_no_cdn():
    """Test 6: web/evidence-viewer.html exists and has no CDN refs (alias)."""
    assert (REPO_ROOT / "web/evidence-viewer.html").exists()
    content = (REPO_ROOT / "web/evidence-viewer.html").read_text(encoding="utf-8")
    assert "cdn." not in content
    assert "unpkg.com" not in content
    assert "jsdelivr" not in content


def test_evidence_viewer_js_no_eval():
    """Test 7: web/js/evidence-viewer.js exists and has no eval()."""
    js_path = REPO_ROOT / "web/js/evidence-viewer.js"
    assert js_path.exists(), "evidence-viewer.js not found"
    content = js_path.read_text(encoding="utf-8")
    assert "eval(" not in content


def test_no_port_9222_in_evidence_files():
    """Test 8: No reference to port 9222 in evidence-related files."""
    files_to_check = [
        REPO_ROOT / "web/evidence-viewer.html",
        REPO_ROOT / "web/js/evidence-viewer.js",
        REPO_ROOT / "web/css/evidence-viewer.css",
    ]
    for fpath in files_to_check:
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            assert "9222" not in content, f"Port 9222 found in {fpath.name}"


def test_evidence_stats_unique_types_is_list(evidence_server):
    """Test 9: unique_types is a list in /api/v1/evidence/stats response."""
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence/stats", timeout=3
    )
    payload = json.loads(response.read().decode("utf-8"))
    assert "unique_types" in payload, "unique_types field missing from stats response"
    assert isinstance(payload["unique_types"], list)


def test_evidence_viewer_js_route(evidence_server):
    """Test 10: GET /web/js/evidence-viewer.js returns JavaScript."""
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/web/js/evidence-viewer.js", timeout=3
    )
    assert response.status == 200
    assert "javascript" in response.headers.get("Content-Type", "")


# ---------------------------------------------------------------------------
# Additional regression tests
# ---------------------------------------------------------------------------


def test_route_serves_html(evidence_server):
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/web/evidence-viewer.html", timeout=3
    )
    assert response.status == 200
    assert "text/html" in response.headers.get("Content-Type", "")


def test_evidence_log_alias_returns_json(evidence_server):
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence/log?limit=1", timeout=3
    )
    payload = json.loads(response.read().decode("utf-8"))
    assert response.status == 200
    assert "application/json" in response.headers.get("Content-Type", "")
    assert "entries" in payload


def test_evidence_viewer_css_route(evidence_server):
    """GET /web/css/evidence-viewer.css returns CSS."""
    response = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/web/css/evidence-viewer.css", timeout=3
    )
    assert response.status == 200
    assert "text/css" in response.headers.get("Content-Type", "")


def test_evidence_viewer_js_uses_esc_html():
    """evidence-viewer.js uses escHtml() for dynamic content."""
    js_path = REPO_ROOT / "web/js/evidence-viewer.js"
    assert js_path.exists()
    content = js_path.read_text(encoding="utf-8")
    assert "escHtml" in content


def test_evidence_viewer_css_uses_hub_tokens():
    """evidence-viewer.css uses var(--hub-*) tokens."""
    css_path = REPO_ROOT / "web/css/evidence-viewer.css"
    assert css_path.exists()
    content = css_path.read_text(encoding="utf-8")
    assert "var(--hub-" in content
