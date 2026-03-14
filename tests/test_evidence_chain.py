# Diagram: 05-solace-runtime-architecture
"""tests/test_evidence_chain.py — Task 026: Evidence Chain Viewer (10 tests)."""
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

TEST_PORT = 18926
VALID_TOKEN = "b" * 64


@pytest.fixture(scope="module")
def chain_server():
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


def auth_req(path: str, method: str = "GET", body: dict | None = None, port: int = TEST_PORT):
    url = f"http://localhost:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {VALID_TOKEN}")
    if data:
        req.add_header("Content-Type", "application/json")
    return req


# ---------------------------------------------------------------------------
# Static file checks
# ---------------------------------------------------------------------------

def test_evidence_chain_html_exists():
    """Test 1: evidence-chain.html exists."""
    assert (REPO_ROOT / "web/evidence-chain.html").exists()


def test_evidence_chain_html_no_cdn():
    """Test 2: HTML has no CDN references."""
    content = (REPO_ROOT / "web/evidence-chain.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content


def test_evidence_chain_html_has_verify():
    """Test 3: HTML has a verify button or mention."""
    content = (REPO_ROOT / "web/evidence-chain.html").read_text(encoding="utf-8")
    assert "verify" in content.lower()


def test_evidence_chain_js_no_eval():
    """Test 4: JS has no eval()."""
    content = (REPO_ROOT / "web/js/evidence-chain.js").read_text(encoding="utf-8")
    assert "eval(" not in content


def test_evidence_chain_js_iife():
    """Test 5: JS uses IIFE pattern."""
    content = (REPO_ROOT / "web/js/evidence-chain.js").read_text(encoding="utf-8")
    assert "(function" in content or "})();" in content


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

def test_evidence_chain_list_returns_200(chain_server):
    """Test 6: GET /api/v1/evidence/chain returns 200 with entries list."""
    resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence/chain", timeout=3
    )
    assert resp.status == 200
    data = json.loads(resp.read())
    assert "entries" in data
    assert isinstance(data["entries"], list)
    assert "total" in data


def test_evidence_chain_record_requires_auth(chain_server):
    """Test 7: POST /api/v1/evidence/chain without auth returns 401."""
    req = urllib.request.Request(
        f"http://localhost:{TEST_PORT}/api/v1/evidence/chain",
        data=json.dumps({"type": "test_event", "data": {}}).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=3)
        assert False, "Expected 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401


def test_evidence_chain_record_and_retrieve(chain_server):
    """Test 8: Record entry and verify it appears in chain list."""
    req = auth_req(
        "/api/v1/evidence/chain", "POST",
        {"type": "test_chain_event_026", "description": "Unit test entry", "data": {"source": "test"}},
    )
    resp = urllib.request.urlopen(req, timeout=3)
    assert resp.status == 201
    data = json.loads(resp.read())
    assert "entry" in data
    entry = data["entry"]
    assert "evidence_id" in entry
    assert entry["evidence_id"].startswith("ev_")
    assert "sha256" in entry
    assert len(entry["sha256"]) == 64  # SHA-256 hex is 64 chars

    # Verify in list
    list_resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/evidence/chain", timeout=3
    )
    list_data = json.loads(list_resp.read())
    found = any(e.get("evidence_id") == entry["evidence_id"] for e in list_data.get("entries", []))
    assert found


def test_evidence_chain_hash_chain_links(chain_server):
    """Test 9: Two successive entries — second prev_sha256 matches first sha256."""
    req1 = auth_req("/api/v1/evidence/chain", "POST", {"type": "chain_test_A", "data": {}})
    resp1 = urllib.request.urlopen(req1, timeout=3)
    e1 = json.loads(resp1.read())["entry"]

    req2 = auth_req("/api/v1/evidence/chain", "POST", {"type": "chain_test_B", "data": {}})
    resp2 = urllib.request.urlopen(req2, timeout=3)
    e2 = json.loads(resp2.read())["entry"]

    # The second entry's prev_sha256 should equal the first's sha256
    assert e2["prev_sha256"] == e1["sha256"]


def test_evidence_chain_bad_type_rejected(chain_server):
    """Test 10: Missing type field returns 400."""
    req = auth_req("/api/v1/evidence/chain", "POST", {"data": {}})
    try:
        urllib.request.urlopen(req, timeout=3)
        assert False, "Expected 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
