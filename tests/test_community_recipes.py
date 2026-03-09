"""tests/test_community_recipes.py — Community Recipe Browsing + Installation UI.

Task 059 — Acceptance gate.
Laws:
  - Port 8888 ONLY. Legacy debug ports are banned.
  - SILENT_INSTALL: BANNED — install response must include scope_required.
  - DIRECT_EXECUTE: BANNED — run always returns requires_approval=True.
  - No Bootstrap/Tailwind/jQuery/CDN in HTML/JS/CSS.
  - No broad fallback exception handling in server code.
"""

from io import BytesIO
import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = "b" * 64


@pytest.fixture
def recipe_env(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    apps_root = repo_root / "data" / "default" / "apps"
    apps_root.mkdir(parents=True)

    gmail_dir = apps_root / "gmail" / "recipes"
    gmail_dir.mkdir(parents=True)
    (gmail_dir / "gmail-daily-digest.json").write_text(json.dumps({
        "recipe_id": "gmail-daily-digest",
        "name": "Gmail Daily Digest",
        "app_id": "gmail",
        "description": "Summarises your inbox each morning",
        "creator": "solace-team",
        "version": "1.0.0",
        "runs_count": 55,
        "hit_rate_pct": 82,
        "avg_cost_usd": "0.001",
        "tags": ["email", "productivity"],
        "steps": [{"action": "navigate", "description": "Open inbox"}],
    }))

    community_recipes_path = tmp_path / ".solace" / "community_recipes.json"
    evidence_path = tmp_path / ".solace" / "evidence.jsonl"
    port_lock_path = tmp_path / ".solace" / "port.lock"
    settings_path = tmp_path / ".solace" / "settings.json"

    monkeypatch.setattr(ys, "COMMUNITY_RECIPES_059_PATH", community_recipes_path, raising=False)
    monkeypatch.setattr(ys, "EVIDENCE_PATH", evidence_path)
    monkeypatch.setattr(ys, "PORT_LOCK_PATH", port_lock_path)
    monkeypatch.setattr(ys, "SETTINGS_PATH", settings_path)

    return {
        "repo_root": repo_root,
        "community_recipes_path": community_recipes_path,
        "install_root": community_recipes_path.parent / "apps",
    }


def _make_handler(env, path, method="GET", payload=None, token=VALID_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured = {"status": None, "data": None, "headers": {}}
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    handler.headers = headers
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18888)
    handler.server = type("DummyServer", (), {
        "session_token_sha256": VALID_TOKEN,
        "repo_root": str(env["repo_root"]),
    })()
    handler.wfile = BytesIO()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    handler.send_response = lambda code: captured.update({"status": code})
    handler.send_header = lambda key, value: captured["headers"].__setitem__(key, value)
    handler.end_headers = lambda: None
    handler.log_message = lambda *args: None
    return handler, captured


def _json_req(env, path, method="GET", payload=None, token=VALID_TOKEN):
    handler, captured = _make_handler(env, path, method=method, payload=payload, token=token)
    if method == "GET":
        handler.do_GET()
    else:
        handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def _asset_req(env, path):
    handler, captured = _make_handler(env, path, method="GET")
    handler.do_GET()
    return int(captured["status"]), dict(captured["headers"]), handler.wfile.getvalue()


def test_recipe_list_returns_installed_flag(recipe_env):
    status, data = _json_req(recipe_env, "/api/v1/recipes/community")
    assert status == 200
    assert "recipes" in data
    assert isinstance(data["recipes"], list)
    assert len(data["recipes"]) > 0
    for recipe in data["recipes"]:
        assert "is_installed" in recipe, f"recipe missing is_installed: {recipe.get('recipe_id')}"


def test_recipe_list_base_route_supports_filters(recipe_env):
    status, data = _json_req(recipe_env, "/api/v1/recipes?category=email&sort=best_hit_rate")
    assert status == 200
    assert data["count"] == len(data["recipes"])
    for recipe in data["recipes"]:
        assert "email" in recipe.get("tags", [])


def test_install_requires_scope_confirmation(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/gmail-inbox-triage-v1/install",
        method="POST",
        payload={},
    )
    assert status == 200
    assert data.get("installed") is True
    assert "scope_required" in data, "install response missing scope_required — SILENT_INSTALL violation"
    scope = data["scope_required"]
    assert "app_id" in scope
    assert "tags" in scope
    assert "description" in scope


def test_install_downloads_to_local_storage(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/gmail-inbox-triage-v1/install",
        method="POST",
        payload={},
    )
    assert status == 200
    recipe_path = recipe_env["install_root"] / "gmail" / "recipes" / "gmail-inbox-triage-v1.json"
    assert recipe_path.exists()
    installed = json.loads(recipe_path.read_text())
    assert installed["recipe_id"] == data["recipe_id"]
    assert installed["is_installed"] is True


def test_install_not_silent(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/github-pr-summary-v1/install",
        method="POST",
        payload={},
    )
    assert status == 200
    assert "scope_required" in data


def test_run_creates_preview_not_direct_execute(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/gmail-daily-digest/run",
        method="POST",
        payload={},
    )
    assert status == 202
    assert data.get("requires_approval") is True
    assert "preview_id" in data
    assert "preview_text" in data
    assert "action_class" in data


def test_fork_creates_local_copy(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/gmail-inbox-triage-v1/fork",
        method="POST",
        payload={"name": "My Custom Triage"},
    )
    assert status == 201
    assert "new_recipe_id" in data
    assert data.get("forked_from") == "gmail-inbox-triage-v1"
    assert data.get("local") is True
    fork_path = recipe_env["install_root"] / "gmail" / "recipes" / f"{data['new_recipe_id']}.json"
    assert fork_path.exists()
    s2, d2 = _json_req(recipe_env, "/api/v1/recipes/my-library")
    assert s2 == 200
    ids = [r["recipe_id"] for r in d2.get("recipes", [])]
    assert data["new_recipe_id"] in ids


def test_my_library_returns_source_field(recipe_env):
    _json_req(recipe_env, "/api/v1/recipes/github-pr-summary-v1/install", method="POST", payload={})
    status, data = _json_req(recipe_env, "/api/v1/recipes/my-library")
    assert status == 200
    assert isinstance(data.get("recipes"), list)
    for recipe in data["recipes"]:
        assert "source" in recipe, f"recipe missing source field: {recipe.get('recipe_id')}"


def test_recipe_hit_rate_uses_decimal(recipe_env):
    status, data = _json_req(recipe_env, "/api/v1/recipes/community")
    assert status == 200
    for recipe in data.get("recipes", []):
        pct = recipe.get("hit_rate_pct", 0)
        assert isinstance(pct, int), f"hit_rate_pct must be int, got {type(pct)} for {recipe.get('recipe_id')}"
        assert 0 <= pct <= 100


def test_recipes_html_no_cdn_dependencies():
    html_path = REPO_ROOT / "web" / "recipes.html"
    assert html_path.exists(), f"recipes.html not found at {html_path}"
    content = html_path.read_text().lower()
    for term in ["bootstrap", "tailwind", "jquery", "cdn."]:
        assert term not in content, f"CDN dependency found in recipes.html: '{term}'"


def test_recipes_css_no_hardcoded_hex():
    css_path = REPO_ROOT / "web" / "css" / "recipes.css"
    assert css_path.exists(), f"recipes.css not found at {css_path}"
    content = css_path.read_text()
    lines = content.splitlines()
    in_root = False
    violations = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(":root"):
            in_root = True
        if in_root and stripped == "}":
            in_root = False
            continue
        if not in_root and "color-mix" not in stripped:
            import re
            if re.search(r"(?<![a-zA-Z0-9-])#[0-9a-fA-F]{3,8}\b", stripped):
                violations.append(f"line {i}: {stripped}")
    assert not violations, "Hardcoded hex outside :root found in recipes.css:\n" + "\n".join(violations)


def test_recipes_html_exists():
    assert (REPO_ROOT / "web" / "recipes.html").exists()


def test_recipes_js_exists():
    assert (REPO_ROOT / "web" / "js" / "recipes.js").exists()


def test_recipes_css_exists():
    assert (REPO_ROOT / "web" / "css" / "recipes.css").exists()


def test_recipes_html_served_via_server(recipe_env):
    status, headers, body = _asset_req(recipe_env, "/web/recipes.html")
    assert status == 200
    assert "text/html" in headers.get("Content-Type", "")
    assert b"Recipe Library" in body


def test_recipes_js_served_via_server(recipe_env):
    status, headers, body = _asset_req(recipe_env, "/web/js/recipes.js")
    assert status == 200
    assert "javascript" in headers.get("Content-Type", "")
    assert b"scope-modal" in body


def test_recipes_css_served_via_server(recipe_env):
    status, headers, body = _asset_req(recipe_env, "/web/css/recipes.css")
    assert status == 200
    assert "text/css" in headers.get("Content-Type", "")
    assert b"--hub-bg" in body


def test_community_recipe_create(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/create",
        method="POST",
        payload={
            "name": "My New Recipe",
            "app_id": "slack",
            "description": "Does something useful",
            "tags": ["messaging"],
            "steps": [{"action": "check", "description": "Verify channel"}],
        },
    )
    assert status == 201
    assert "recipe_id" in data
    assert data.get("local") is True
    recipe_path = recipe_env["install_root"] / "slack" / "recipes" / f"{data['recipe_id']}.json"
    assert recipe_path.exists()


def test_install_requires_auth(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/gmail-inbox-triage-v1/install",
        method="POST",
        payload={},
        token=None,
    )
    assert status == 401
    assert data["error"] == "unauthorized"


def test_run_requires_auth(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/gmail-inbox-triage-v1/run",
        method="POST",
        payload={},
        token=None,
    )
    assert status == 401
    assert data["error"] == "unauthorized"


def test_fork_requires_auth(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/gmail-inbox-triage-v1/fork",
        method="POST",
        payload={"name": "Blocked Fork"},
        token=None,
    )
    assert status == 401
    assert data["error"] == "unauthorized"


def test_fork_missing_name(recipe_env):
    status, data = _json_req(
        recipe_env,
        "/api/v1/recipes/gmail-inbox-triage-v1/fork",
        method="POST",
        payload={},
    )
    assert status == 400
    assert "name" in data.get("error", "").lower()


def test_recipes_js_no_silent_install():
    js_path = REPO_ROOT / "web" / "js" / "recipes.js"
    assert js_path.exists()
    raw = js_path.read_text()
    assert "scope-modal" in raw
    assert "autoInstall" not in raw
    assert "silentInstall" not in raw


def test_community_recipes_filter_by_category(recipe_env):
    status, data = _json_req(recipe_env, "/api/v1/recipes/community?category=email")
    assert status == 200
    for recipe in data.get("recipes", []):
        assert "email" in recipe.get("tags", [])


def test_community_recipes_sort_by_best_hit_rate(recipe_env):
    status, data = _json_req(recipe_env, "/api/v1/recipes/community?sort=best_hit_rate")
    assert status == 200
    recipes = data.get("recipes", [])
    if len(recipes) >= 2:
        for i in range(len(recipes) - 1):
            assert recipes[i]["hit_rate_pct"] >= recipes[i + 1]["hit_rate_pct"]
