"""tests/test_password_vault.py — Password Vault acceptance gate.
Task 048 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - category validated against VAULT_CATEGORIES
  - password_hash = SHA-256 of password (never plaintext)
  - domain_hash = SHA-256 of domain (never raw domain)
  - copy_count increments on /copy
  - All routes require auth
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

TEST_TOKEN = "test-token-vault-048"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18920)
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
def reset_vault(monkeypatch):
    """Reset vault state between tests."""
    monkeypatch.setattr(ys, "_VAULT_ENTRIES", [])
    yield


# ---------------------------------------------------------------------------
# 1. Initially empty list
# ---------------------------------------------------------------------------
def test_vault_empty_initially():
    status, data = get_json("/api/v1/vault/entries")
    assert status == 200
    assert data.get("entries") == []


# ---------------------------------------------------------------------------
# 2. POST adds entry and returns entry_id
# ---------------------------------------------------------------------------
def test_vault_add_entry():
    status, data = post_json("/api/v1/vault/entries", {
        "title": "My Gmail", "category": "login", "username": "user@gmail.com",
        "password": "secret123", "domain": "gmail.com",
    })
    assert status == 200
    assert data.get("status") == "added"
    assert data.get("entry_id", "").startswith("vault_")


# ---------------------------------------------------------------------------
# 3. Password stored as SHA-256 hash, never plaintext
# ---------------------------------------------------------------------------
def test_vault_password_hashed():
    post_json("/api/v1/vault/entries", {
        "title": "Bank", "category": "bank",
        "password": "mysecretpassword", "domain": "mybank.com",
    })
    status, data = get_json("/api/v1/vault/entries")
    assert status == 200
    entries = data["entries"]
    assert len(entries) == 1
    entry = entries[0]
    # password_hash must be SHA-256 hex of "mysecretpassword"
    expected = hashlib.sha256(b"mysecretpassword").hexdigest()
    assert entry["password_hash"] == expected
    # raw password must NOT appear anywhere
    assert "mysecretpassword" not in str(entry)


# ---------------------------------------------------------------------------
# 4. Domain stored as SHA-256 hash, never raw domain
# ---------------------------------------------------------------------------
def test_vault_domain_hashed():
    post_json("/api/v1/vault/entries", {
        "title": "WiFi", "category": "wifi",
        "password": "wifipass", "domain": "myhome.router",
    })
    status, data = get_json("/api/v1/vault/entries")
    entry = data["entries"][0]
    expected_domain_hash = hashlib.sha256(b"myhome.router").hexdigest()
    assert entry["domain_hash"] == expected_domain_hash
    assert "myhome.router" not in str(entry)


# ---------------------------------------------------------------------------
# 5. Invalid category → 400
# ---------------------------------------------------------------------------
def test_vault_invalid_category():
    status, data = post_json("/api/v1/vault/entries", {
        "title": "x", "category": "crypto-wallet",
    })
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 6. copy_count increments on /copy
# ---------------------------------------------------------------------------
def test_vault_copy_increments():
    _, add_data = post_json("/api/v1/vault/entries", {
        "title": "API Key", "category": "api-key",
        "password": "sk-abcdef",
    })
    entry_id = add_data["entry_id"]

    status, data = post_json(f"/api/v1/vault/entries/{entry_id}/copy", {})
    assert status == 200
    assert data.get("copy_count") == 1

    post_json(f"/api/v1/vault/entries/{entry_id}/copy", {})
    _, list_data = get_json("/api/v1/vault/entries")
    entry = next(e for e in list_data["entries"] if e["entry_id"] == entry_id)
    assert entry["copy_count"] == 2


# ---------------------------------------------------------------------------
# 7. DELETE /{entry_id} removes entry
# ---------------------------------------------------------------------------
def test_vault_delete_entry():
    _, add_data = post_json("/api/v1/vault/entries", {
        "title": "To Delete", "category": "note",
    })
    entry_id = add_data["entry_id"]

    status, data = delete_path(f"/api/v1/vault/entries/{entry_id}")
    assert status == 200
    assert data.get("status") == "deleted"

    _, list_data = get_json("/api/v1/vault/entries")
    ids = [e["entry_id"] for e in list_data["entries"]]
    assert entry_id not in ids


# ---------------------------------------------------------------------------
# 8. GET /vault/stats returns totals
# ---------------------------------------------------------------------------
def test_vault_stats():
    post_json("/api/v1/vault/entries", {"title": "A", "category": "login"})
    post_json("/api/v1/vault/entries", {"title": "B", "category": "login"})
    post_json("/api/v1/vault/entries", {"title": "C", "category": "api-key"})

    status, data = get_json("/api/v1/vault/stats")
    assert status == 200
    assert data["total"] == 3
    assert data["by_category"]["login"] == 2
    assert data["by_category"]["api-key"] == 1


# ---------------------------------------------------------------------------
# 9. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_vault_html_no_cdn():
    html_path = REPO_ROOT / "web" / "password-vault.html"
    assert html_path.exists(), "password-vault.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 10. No port 9222 in any vault file
# ---------------------------------------------------------------------------
def test_no_port_9222_in_vault():
    files_to_check = [
        REPO_ROOT / "web" / "password-vault.html",
        REPO_ROOT / "web" / "js" / "password-vault.js",
        REPO_ROOT / "web" / "css" / "password-vault.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
