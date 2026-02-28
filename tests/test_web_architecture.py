from __future__ import annotations

import hashlib
import http.client
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    REPO_ROOT / "web/home.html",
    REPO_ROOT / "web/download.html",
    REPO_ROOT / "web/machine-dashboard.html",
    REPO_ROOT / "web/tunnel-connect.html",
]


def test_pages_use_shared_assets_and_no_inline_contract_violations() -> None:
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        assert "<style" not in text
        assert "style=" not in text
        assert '<script src="/js/solace.js" defer></script>' in text
        assert '<link rel="stylesheet" href="/css/site.css">' in text


def test_hash_sidecars_match() -> None:
    css_hash = hashlib.sha256((REPO_ROOT / "web/css/site.css").read_bytes()).hexdigest()
    js_hash = hashlib.sha256((REPO_ROOT / "web/js/solace.js").read_bytes()).hexdigest()
    assert (REPO_ROOT / "web/css/site.css.sha256").read_text(encoding="utf-8").strip() == css_hash
    assert (REPO_ROOT / "web/js/solace.js.sha256").read_text(encoding="utf-8").strip() == js_hash


def test_local_server_slug_routes_and_redirects() -> None:
    port = 8797
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["BIND_ADDR"] = "127.0.0.1"
    process = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "web/server.py")],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_server(port)
        status_root, _, root_body = http_get(port, "/")
        status_slug, _, slug_body = http_get(port, "/download")
        status_html, headers_html, _ = http_get(port, "/download.html")

        assert status_root == 200
        assert "Solace Browser" in root_body
        assert status_slug == 200
        assert "Download Solace Browser" in slug_body
        assert status_html == 301
        assert headers_html.get("Location") == "/download"
    finally:
        process.terminate()
        process.wait(timeout=10)


def wait_for_server(port: int) -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            conn.request("GET", "/")
            response = conn.getresponse()
            response.read()
            conn.close()
            return
        except OSError:
            time.sleep(0.2)
    raise AssertionError("server did not start in time")


def http_get(port: int, path: str) -> tuple[int, dict[str, str], str]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    response = conn.getresponse()
    body = response.read().decode("utf-8", errors="ignore")
    headers = {key: value for key, value in response.getheaders()}
    conn.close()
    return response.status, headers, body
