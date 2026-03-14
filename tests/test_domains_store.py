# Diagram: 05-solace-runtime-architecture
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

VALID_TOKEN = "a" * 64

BUILTIN_DOMAINS = [
    ("solaceagi.com", "Solace AGI", False),
    ("google.com", "Google", False),
    ("news.ycombinator.com", "Hacker News", False),
    ("reddit.com", "Reddit", False),
    ("github.com", "GitHub", True),
    ("linkedin.com", "LinkedIn", True),
    ("slack.com", "Slack", True),
    ("x.com", "X", True),
    ("youtube.com", "YouTube", False),
    ("amazon.com", "Amazon", True),
    ("notion.so", "Notion", True),
    ("figma.com", "Figma", True),
    ("calendar.google.com", "Google Calendar", True),
    ("mail.google.com", "Gmail", True),
    ("docs.google.com", "Google Docs", True),
    ("drive.google.com", "Google Drive", True),
    ("discord.com", "Discord", True),
    ("web.whatsapp.com", "WhatsApp Web", True),
    ("telegram.org", "Telegram", False),
    ("facebook.com", "Facebook", True),
    ("instagram.com", "Instagram", True),
]


def _write_domain(root: Path, domain: str, name: str, requires_login: bool, app_id: str) -> None:
    domain_root = root / domain
    apps_root = domain_root / "apps" / app_id
    apps_root.mkdir(parents=True, exist_ok=True)
    (domain_root / "manifest.yaml").write_text(
        "\n".join(
            [
                f"id: {domain}",
                f"name: {name}",
                f"domain: {domain}",
                f"icon: /branding/{app_id}.png",
                f"requires_login: {'true' if requires_login else 'false'}",
            ]
        ),
        encoding="utf-8",
    )
    (apps_root / "manifest.yaml").write_text(
        "\n".join(
            [
                f"id: {app_id}",
                f"name: {name} Helper",
                f"domain: {domain}",
                'version: "1.0.0"',
                "tier_required: free",
            ]
        ),
        encoding="utf-8",
    )


@pytest.fixture
def domains_store_server(tmp_path, monkeypatch):
    import yinyang_server as ys

    repo_root = tmp_path / "repo"
    default_domains_root = repo_root / "data" / "default" / "domains"
    local_apps_root = tmp_path / ".solace" / "apps"
    suggestions_root = tmp_path / ".solace" / "store-suggestions"
    settings_path = tmp_path / ".solace" / "settings.json"
    evidence_path = tmp_path / ".solace" / "evidence.jsonl"
    port_lock_path = tmp_path / ".solace" / "port.lock"

    for index, (domain, name, requires_login) in enumerate(BUILTIN_DOMAINS, start=1):
        _write_domain(default_domains_root, domain, name, requires_login, f"app-{index:02d}")

    monkeypatch.setattr(ys, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(ys, "EVIDENCE_PATH", evidence_path)
    monkeypatch.setattr(ys, "PORT_LOCK_PATH", port_lock_path)
    monkeypatch.setenv("SOLACE_LOCAL_APPS_ROOT", str(local_apps_root))
    monkeypatch.setenv("SOLACE_STORE_SUGGESTIONS_ROOT", str(suggestions_root))

    httpd = ys.build_server(0, str(repo_root), session_token_sha256=VALID_TOKEN)
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
        "repo_root": repo_root,
        "local_apps_root": local_apps_root,
        "suggestions_root": suggestions_root,
    }

    httpd.shutdown()
    thread.join(timeout=2)


def _request_json(server: dict, path: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {VALID_TOKEN}"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    request = urllib.request.Request(f"{server['base_url']}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode())


class TestDomainsRoutes:
    def test_domains_list_returns_21_domains(self, domains_store_server):
        status, data = _request_json(domains_store_server, "/api/v1/domains")

        assert status == 200
        assert data["count"] == 21
        assert len(data["domains"]) == 21
        assert data["domains"][0]["domain"] == "amazon.com"

    def test_domain_detail_returns_manifest(self, domains_store_server):
        status, data = _request_json(domains_store_server, "/api/v1/domains/solaceagi.com")

        assert status == 200
        assert data["domain"]["domain"] == "solaceagi.com"
        assert data["domain"]["app_count"] == 1
        assert data["domain"]["apps"][0]["id"] == "app-01"

    def test_domain_suggest_stores_locally(self, domains_store_server):
        status, data = _request_json(
            domains_store_server,
            "/api/v1/domains/suggest",
            method="POST",
            payload={
                "domain": "mysite.com",
                "name": "My Site",
                "reason": "Useful customer workflow",
            },
        )

        stored = domains_store_server["suggestions_root"] / "domains" / "mysite.com.json"
        assert status == 201
        assert data["status"] == "stored"
        assert stored.exists()
        payload = json.loads(stored.read_text(encoding="utf-8"))
        assert payload["domain"] == "mysite.com"

    def test_app_suggest_validates_domain_exists(self, domains_store_server):
        status, data = _request_json(
            domains_store_server,
            "/api/v1/apps/suggest",
            method="POST",
            payload={
                "domain": "missing.example",
                "id": "missing-app",
                "name": "Missing App",
            },
        )

        assert status == 404
        assert data["error"] == "domain not found"

    def test_domains_bootstrap_copies_defaults_to_local_root(self, domains_store_server):
        status, data = _request_json(
            domains_store_server,
            "/api/v1/domains/bootstrap",
            method="POST",
            payload={},
        )

        installed_manifest = (
            domains_store_server["local_apps_root"]
            / "solaceagi.com"
            / "app-01"
            / "manifest.yaml"
        )
        assert status == 200
        assert data["status"] == "ok"
        assert data["copied_domains"] == 21
        assert installed_manifest.exists()
