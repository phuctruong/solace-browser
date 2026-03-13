import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18888
VALID_TOKEN = "b" * 64


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    import yinyang_server as ys

    ys.SETTINGS_PATH = tmp_path / ".solace" / "settings.json"
    ys.EVIDENCE_PATH = tmp_path / ".solace" / "evidence.jsonl"
    ys.PORT_LOCK_PATH = tmp_path / ".solace" / "port.lock"

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{TEST_PORT}"
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1):
                break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {
        "base_url": base_url,
        "headers": {"Authorization": f"Bearer {VALID_TOKEN}"},
        "suggestions_path": tmp_path / ".solace" / "domain_suggestions.jsonl",
    }

    httpd.shutdown()
    thread.join(timeout=2)


def _request(client: dict[str, object], path: str, method: str = "GET", payload: dict | None = None):
    headers = dict(client["headers"])
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{client['base_url']}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def test_domains_page_renders_21_domains(client):
    status, _, body = _request(client, "/domains")

    html = body.decode("utf-8")
    assert status == 200
    assert html.count('class="domain-card"') == 21
    assert "/api/v1/domains/solaceagi.com" in html
    assert "/api/v1/domains/google.com" in html
    assert "/api/v1/domains/linkedin.com" in html


def test_store_page_loads(client):
    status, _, body = _request(client, "/store")

    html = body.decode("utf-8")
    assert status == 200
    assert "<h1>App Store</h1>" in html
    assert '<input type="search" id="store-search" placeholder="Search domains...">' in html
    assert 'class="domain-card"' in html


def test_domain_icon_serves_png_or_svg(client):
    status, headers, body = _request(client, "/api/v1/domains/solaceagi.com/icon")

    assert status == 200
    assert "image/" in headers.get("Content-Type", "") or "svg" in headers.get("Content-Type", "")
    assert body


def test_domain_suggest_appends_jsonl(client):
    status, _, body = _request(
        client,
        "/api/v1/domains/suggest",
        method="POST",
        payload={"domain": "example.com", "message": "Need this in the store"},
    )

    payload = json.loads(body.decode("utf-8"))
    assert status == 200
    assert payload == {"status": "received", "domain": "example.com"}

    lines = client["suggestions_path"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["domain"] == "example.com"
    assert stored["message"] == "Need this in the store"
    assert stored["ts"]
