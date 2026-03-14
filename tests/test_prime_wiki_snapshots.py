# Diagram: 05-solace-runtime-architecture
"""Prime Wiki snapshot tests for Yinyang Server."""

import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PZWEB_BIN = pathlib.Path("/home/phuc/projects/pzip/native/pzip_web_cpp/build/pzweb")
PZLOG_BIN = pathlib.Path("/home/phuc/projects/pzip/native/pzip_logs_cpp/build/pzlog")
sys.path.insert(0, str(REPO_ROOT))


def _pzip_decompress_content(content_pzip_b64: str, codec: str) -> str:
    if codec == "pzweb":
        binary_path = PZWEB_BIN
    else:
        assert codec == "pzlog"
        binary_path = PZLOG_BIN
    result = subprocess.run(
        [str(binary_path), "decompress", "-"],
        input=base64.b64decode(content_pzip_b64),
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout.decode()


@pytest.fixture
def prime_wiki_server(tmp_path, monkeypatch):
    import yinyang_server as ys

    repo_root = tmp_path / "repo"
    (repo_root / "data" / "default" / "apps").mkdir(parents=True)

    solace_root = tmp_path / ".solace"
    evidence_path = solace_root / "evidence.jsonl"
    part11_dir = solace_root / "evidence"
    part11_path = part11_dir / "evidence.jsonl"
    chain_path = part11_dir / "chain.lock"
    settings_path = solace_root / "settings.json"
    prime_wiki_root = solace_root / "prime-wiki"
    port_lock_path = solace_root / "port.lock"

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"account": {"tier": "free"}}))

    monkeypatch.setattr(ys, "EVIDENCE_PATH", evidence_path)
    monkeypatch.setattr(ys, "PART11_EVIDENCE_DIR", part11_dir)
    monkeypatch.setattr(ys, "PART11_EVIDENCE_PATH", part11_path)
    monkeypatch.setattr(ys, "PART11_CHAIN_LOCK_PATH", chain_path)
    monkeypatch.setattr(ys, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(ys, "PRIME_WIKI_ROOT", prime_wiki_root)
    monkeypatch.setattr(ys, "PORT_LOCK_PATH", port_lock_path)

    httpd = ys.build_server(0, str(repo_root))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://localhost:{httpd.server_port}"
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1):
                break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {
        "base_url": base_url,
        "settings_path": settings_path,
        "prime_wiki_root": prime_wiki_root,
    }

    httpd.shutdown()
    thread.join(timeout=2)


def _request_json(server: dict, path: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    headers: dict[str, str] = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{server['base_url']}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _snapshot_payload(url: str, html: str, snapshot_type: str = "before_action") -> dict:
    return {
        "url": url,
        "content_html": html,
        "snapshot_type": snapshot_type,
        "app_id": "gmail",
        "action_id": "action-123",
    }


def test_snapshot_compresses_html(prime_wiki_server):
    html = "<html><head><title>Inbox</title></head><body>" + ("<div>Hello world</div>" * 80) + "</body></html>"
    status, created = _request_json(
        prime_wiki_server,
        "/api/v1/prime-wiki/snapshot",
        method="POST",
        payload=_snapshot_payload("https://mail.google.com/mail/u/0/#inbox", html),
    )

    assert status == 201
    assert created["rtc_verified"] is True
    assert created["compression_ratio"] > 1
    assert created["codec"] == "pzweb"

    detail_status, detail = _request_json(
        prime_wiki_server,
        f"/api/v1/prime-wiki/snapshot/{created['snapshot_id']}",
    )
    assert detail_status == 200
    assert "content_pzip_b64" not in detail

    content_status, content = _request_json(
        prime_wiki_server,
        f"/api/v1/prime-wiki/snapshot/{created['snapshot_id']}/content",
    )
    assert content_status == 200
    assert content["rtc_verified"] is True
    assert content["codec"] == "pzweb"
    restored = _pzip_decompress_content(content["content_pzip_b64"], content["codec"])
    assert restored == html


def test_snapshot_sha256_matches_uncompressed(prime_wiki_server):
    html = "<html><head><title>SHA</title></head><body><h1>Digest</h1></body></html>"
    status, created = _request_json(
        prime_wiki_server,
        "/api/v1/prime-wiki/snapshot",
        method="POST",
        payload=_snapshot_payload("https://docs.example.com/page", html),
    )

    assert status == 201
    expected_sha256 = hashlib.sha256(html.encode("utf-8")).hexdigest()
    assert created["sha256"] == expected_sha256

    content_status, content = _request_json(
        prime_wiki_server,
        f"/api/v1/prime-wiki/snapshot/{created['snapshot_id']}/content",
    )
    assert content_status == 200
    assert content["sha256"] == expected_sha256


def test_snapshot_allows_missing_content_html(prime_wiki_server):
    payload = {
        "url": "https://docs.example.com/empty",
        "snapshot_type": "periodic",
        "app_id": "docs",
        "action_id": "action-empty",
    }

    status, created = _request_json(
        prime_wiki_server,
        "/api/v1/prime-wiki/snapshot",
        method="POST",
        payload=payload,
    )

    assert status == 201
    assert created["sha256"] == hashlib.sha256(b"").hexdigest()
    assert created["rtc_verified"] is True
    assert created["codec"] == "pzlog"

    content_status, content = _request_json(
        prime_wiki_server,
        f"/api/v1/prime-wiki/snapshot/{created['snapshot_id']}/content",
    )

    assert content_status == 200
    assert _pzip_decompress_content(content["content_pzip_b64"], content["codec"]) == ""


def test_key_elements_extract_title_and_headings():
    import yinyang_server as ys

    html = """
    <html>
      <head><title>Solace Docs</title></head>
      <body>
        <h1>Prime Wiki</h1>
        <h2>Snapshots</h2>
        <h3>Diffs</h3>
      </body>
    </html>
    """

    extracted = ys.extract_key_elements(html)

    assert extracted["title"] == "Solace Docs"
    assert extracted["headings"] == ["Prime Wiki", "Snapshots", "Diffs"]


def test_cta_extraction_finds_action_buttons():
    import yinyang_server as ys

    html = """
    <html>
      <body>
        <button>Archive</button>
        <button>Reply</button>
        <a href="/messages/send">Send Now</a>
        <a href="/docs/read">Read More</a>
        <input type="submit" value="Publish" />
      </body>
    </html>
    """

    ctas = ys.extract_ctas(html)

    assert "Archive" in ctas
    assert "Reply" in ctas
    assert "Send Now" in ctas
    assert "Publish" in ctas
    assert "Read More" not in ctas


def test_diff_shows_added_and_removed_elements(prime_wiki_server):
    before_html = "<html><head><title>Inbox</title></head><body><h1>Inbox</h1><button>Archive</button></body></html>"
    after_html = "<html><head><title>Inbox Updated</title></head><body><h1>Inbox</h1><h2>Done</h2><button>Reply</button></body></html>"

    _, before = _request_json(
        prime_wiki_server,
        "/api/v1/prime-wiki/snapshot",
        method="POST",
        payload=_snapshot_payload("https://mail.google.com/mail/u/0/#inbox", before_html, "before_action"),
    )
    _, after = _request_json(
        prime_wiki_server,
        "/api/v1/prime-wiki/snapshot",
        method="POST",
        payload=_snapshot_payload("https://mail.google.com/mail/u/0/#inbox", after_html, "after_action"),
    )

    status, diff = _request_json(
        prime_wiki_server,
        f"/api/v1/prime-wiki/diff?before={before['snapshot_id']}&after={after['snapshot_id']}",
    )

    assert status == 200
    assert "heading:Done" in diff["added_elements"]
    assert "cta:Archive" in diff["removed_elements"]
    assert diff["changed_headings"]["added"] == ["Done"]
    assert diff["action_summary"].startswith("Added ")


def test_stats_counts_correctly(prime_wiki_server):
    html = "<html><head><title>Stats</title></head><body><h1>One</h1></body></html>"

    _request_json(
        prime_wiki_server,
        "/api/v1/prime-wiki/snapshot",
        method="POST",
        payload=_snapshot_payload("https://mail.google.com/mail/u/0/#inbox", html, "before_action"),
    )
    _request_json(
        prime_wiki_server,
        "/api/v1/prime-wiki/snapshot",
        method="POST",
        payload=_snapshot_payload("https://docs.example.com/guide", html, "periodic"),
    )

    status, stats = _request_json(prime_wiki_server, "/api/v1/prime-wiki/stats")

    assert status == 200
    assert stats["total_snapshots"] == 2
    assert stats["total_compressed_kb"] > 0
    assert stats["domains_covered"] == 2
    assert stats["last_24h_count"] == 2


def test_cloud_push_async_non_blocking(monkeypatch):
    import yinyang_server as ys

    calls: dict[str, object] = {"started": False}

    class FakeThread:
        def __init__(self, target, args=(), daemon=False):
            calls["target"] = target
            calls["args"] = args
            calls["daemon"] = daemon

        def start(self):
            calls["started"] = True

    monkeypatch.setattr(ys.threading, "Thread", FakeThread)
    monkeypatch.setattr(ys, "_load_account_tier", lambda: "pro")

    snapshot_record = {"snapshot_id": "s1", "url_hash": "a" * 64}
    started = ys._queue_prime_wiki_cloud_push(snapshot_record)

    assert started is True
    assert calls["started"] is True
    assert calls["daemon"] is True
    assert calls["target"] is ys._prime_wiki_cloud_push_worker
    assert calls["args"] == (snapshot_record,)


def test_local_storage_structure_correct(prime_wiki_server):
    html = "<html><head><title>Store</title></head><body><h1>Folder</h1></body></html>"
    status, created = _request_json(
        prime_wiki_server,
        "/api/v1/prime-wiki/snapshot",
        method="POST",
        payload=_snapshot_payload("https://example.com/folder/page", html, "before_action"),
    )

    assert status == 201
    snapshot_dir = prime_wiki_server["prime_wiki_root"] / created["url_hash"]
    files = list(snapshot_dir.glob("before_action_*.json"))

    assert snapshot_dir.is_dir()
    assert len(files) == 1
