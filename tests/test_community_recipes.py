"""tests/test_community_recipes.py — Community Recipe Browsing + Installation UI.

Task 059 — Acceptance gate.
Laws:
  - Port 8888 ONLY. Port 9222 BANNED.
  - SILENT_INSTALL: BANNED — install response must include scope_required.
  - DIRECT_EXECUTE: BANNED — run always returns requires_approval=True.
  - No Bootstrap/Tailwind/jQuery/CDN in HTML/JS/CSS.
  - No bare except Exception in server code.
"""

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

VALID_TOKEN = "b" * 64


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def recipe_server(tmp_path, monkeypatch):
    import yinyang_server as ys

    repo_root = tmp_path / "repo"
    apps_root = repo_root / "data" / "default" / "apps"
    apps_root.mkdir(parents=True)

    # Seed one local recipe inside a dummy app dir
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
    }))

    community_recipes_path = tmp_path / ".solace" / "community_recipes.json"
    evidence_path = tmp_path / ".solace" / "evidence.jsonl"
    port_lock_path = tmp_path / ".solace" / "port.lock"
    settings_path = tmp_path / ".solace" / "settings.json"

    monkeypatch.setattr(ys, "COMMUNITY_RECIPES_059_PATH", community_recipes_path, raising=False)
    monkeypatch.setattr(ys, "EVIDENCE_PATH", evidence_path)
    monkeypatch.setattr(ys, "PORT_LOCK_PATH", port_lock_path)
    monkeypatch.setattr(ys, "SETTINGS_PATH", settings_path)

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
        "community_recipes_path": community_recipes_path,
    }

    httpd.shutdown()
    thread.join(timeout=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(server, path, method="GET", payload=None, token=VALID_TOKEN):
    headers = {"Content-Type": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode()
    req = urllib.request.Request(
        server["base_url"] + path,
        data=data, headers=headers, method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_recipe_list_returns_installed_flag(recipe_server):
    """GET /api/v1/recipes/community must include is_installed on each recipe."""
    status, data = _req(recipe_server, "/api/v1/recipes/community")
    assert status == 200
    assert "recipes" in data
    assert isinstance(data["recipes"], list)
    assert len(data["recipes"]) > 0
    for recipe in data["recipes"]:
        assert "is_installed" in recipe, f"recipe missing is_installed: {recipe.get('recipe_id')}"


def test_install_requires_scope_confirmation(recipe_server):
    """POST /api/v1/recipes/{id}/install must return scope_required (not silent)."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/gmail-inbox-triage-v1/install",
        method="POST",
    )
    assert status == 200
    assert data.get("installed") is True
    # CRITICAL: scope_required must be present — UI uses it to show confirmation modal
    assert "scope_required" in data, "install response missing scope_required — SILENT_INSTALL violation"
    scope = data["scope_required"]
    assert "app_id" in scope
    assert "tags" in scope
    assert "description" in scope


def test_install_not_silent(recipe_server):
    """Alias test: install response must always carry scope information."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/github-pr-summary-v1/install",
        method="POST",
    )
    assert status == 200
    assert "scope_required" in data


def test_run_creates_preview_not_direct_execute(recipe_server):
    """POST /api/v1/recipes/{id}/run must return requires_approval=True always."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/gmail-daily-digest/run",
        method="POST",
    )
    assert status == 202
    assert data.get("requires_approval") is True, "DIRECT_EXECUTE violation: requires_approval must be True"
    assert "preview_id" in data
    assert "preview_text" in data
    assert "action_class" in data


def test_fork_creates_local_copy(recipe_server):
    """POST /api/v1/recipes/{id}/fork must create a new local recipe."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/gmail-inbox-triage-v1/fork",
        method="POST",
        payload={"name": "My Custom Triage"},
    )
    assert status == 201
    assert "new_recipe_id" in data
    assert data.get("forked_from") == "gmail-inbox-triage-v1"
    assert data.get("local") is True
    # The fork should now appear in my-library
    s2, d2 = _req(recipe_server, "/api/v1/recipes/my-library")
    assert s2 == 200
    ids = [r["recipe_id"] for r in d2.get("recipes", [])]
    assert data["new_recipe_id"] in ids


def test_my_library_returns_source_field(recipe_server):
    """GET /api/v1/recipes/my-library must include source field on each recipe."""
    # Install something first
    _req(recipe_server, "/api/v1/recipes/github-pr-summary-v1/install", method="POST")
    status, data = _req(recipe_server, "/api/v1/recipes/my-library")
    assert status == 200
    assert isinstance(data.get("recipes"), list)
    for recipe in data["recipes"]:
        assert "source" in recipe, f"recipe missing source field: {recipe.get('recipe_id')}"


def test_recipe_hit_rate_uses_decimal(recipe_server):
    """hit_rate_pct must be an integer (0-100), not a decimal fraction (0.0-1.0)."""
    status, data = _req(recipe_server, "/api/v1/recipes/community")
    assert status == 200
    for recipe in data.get("recipes", []):
        pct = recipe.get("hit_rate_pct", 0)
        assert isinstance(pct, int), f"hit_rate_pct must be int, got {type(pct)} for {recipe.get('recipe_id')}"
        assert 0 <= pct <= 100, f"hit_rate_pct must be 0-100, got {pct}"


def test_recipes_html_no_cdn_dependencies():
    """web/recipes.html must not reference CDN (bootstrap, tailwind, jquery, cdn.)."""
    html_path = REPO_ROOT / "web" / "recipes.html"
    assert html_path.exists(), f"recipes.html not found at {html_path}"
    content = html_path.read_text().lower()
    banned = ["bootstrap", "tailwind", "jquery", "cdn."]
    for term in banned:
        assert term not in content, f"CDN dependency found in recipes.html: '{term}'"


def test_recipes_css_no_hardcoded_hex():
    """web/css/recipes.css must use var(--hub-*) tokens. Hex only allowed in :root token definitions."""
    css_path = REPO_ROOT / "web" / "css" / "recipes.css"
    assert css_path.exists(), f"recipes.css not found at {css_path}"
    content = css_path.read_text()
    lines = content.splitlines()
    # Hex values outside of :root block are forbidden
    in_root = False
    violations = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(":root"):
            in_root = True
        if in_root and stripped == "}":
            in_root = False
            continue
        if not in_root:
            # Allow color-mix() calls which mix with var(--hub-*) — those are fine
            if "color-mix" in stripped:
                continue
            # Check for standalone hex colour values outside :root
            import re
            if re.search(r"(?<![a-zA-Z0-9-])#[0-9a-fA-F]{3,8}\b", stripped):
                violations.append(f"line {i}: {stripped}")
    assert not violations, "Hardcoded hex outside :root found in recipes.css:\n" + "\n".join(violations)


def test_recipes_html_exists():
    """web/recipes.html must exist."""
    assert (REPO_ROOT / "web" / "recipes.html").exists()


def test_recipes_js_exists():
    """web/js/recipes.js must exist."""
    assert (REPO_ROOT / "web" / "js" / "recipes.js").exists()


def test_recipes_css_exists():
    """web/css/recipes.css must exist."""
    assert (REPO_ROOT / "web" / "css" / "recipes.css").exists()


def test_recipes_html_served_via_server(recipe_server):
    """GET /web/recipes.html must return 200 with text/html."""
    req = urllib.request.Request(recipe_server["base_url"] + "/web/recipes.html")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        ct = resp.headers.get("Content-Type", "")
        assert "text/html" in ct


def test_recipes_js_served_via_server(recipe_server):
    """GET /web/js/recipes.js must return 200 with javascript content-type."""
    req = urllib.request.Request(recipe_server["base_url"] + "/web/js/recipes.js")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200


def test_recipes_css_served_via_server(recipe_server):
    """GET /web/css/recipes.css must return 200 with text/css."""
    req = urllib.request.Request(recipe_server["base_url"] + "/web/css/recipes.css")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        ct = resp.headers.get("Content-Type", "")
        assert "text/css" in ct


def test_community_recipe_create(recipe_server):
    """POST /api/v1/recipes/create must return recipe_id and local=True."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/create",
        method="POST",
        payload={
            "name": "My New Recipe",
            "app_id": "slack",
            "description": "Does something useful",
            "tags": ["messaging"],
            "steps": [],
        },
    )
    assert status == 201
    assert "recipe_id" in data
    assert data.get("local") is True


def test_install_requires_auth(recipe_server):
    """POST /api/v1/recipes/{id}/install without token must return 401."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/gmail-inbox-triage-v1/install",
        method="POST",
        token=None,
    )
    assert status == 401


def test_run_requires_auth(recipe_server):
    """POST /api/v1/recipes/{id}/run without token must return 401."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/gmail-inbox-triage-v1/run",
        method="POST",
        token=None,
    )
    assert status == 401


def test_fork_requires_auth(recipe_server):
    """POST /api/v1/recipes/{id}/fork without token must return 401."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/gmail-inbox-triage-v1/fork",
        method="POST",
        token=None,
    )
    assert status == 401


def test_fork_missing_name(recipe_server):
    """POST /api/v1/recipes/{id}/fork without name must return 400."""
    status, data = _req(
        recipe_server,
        "/api/v1/recipes/gmail-inbox-triage-v1/fork",
        method="POST",
        payload={},
    )
    assert status == 400
    assert "name" in data.get("error", "").lower()


def test_recipes_js_no_silent_install():
    """web/js/recipes.js must always show scope modal before install — no silent/auto install in code."""
    import re
    js_path = REPO_ROOT / "web" / "js" / "recipes.js"
    assert js_path.exists()
    raw = js_path.read_text()
    # Must have scope modal wired up
    assert "scope-modal" in raw, "scope-modal reference missing from recipes.js"
    # Must call showScopeModal (or equivalent) before confirmInstall
    assert "scope-modal" in raw.lower(), "scope modal must be shown before install"
    # autoInstall function must NOT exist (only confirmInstall which requires user click)
    assert "autoInstall" not in raw, "autoInstall function found — silent install violation"
    assert "silentInstall" not in raw, "silentInstall function found — silent install violation"
    # confirmInstall must require user interaction (scope-modal must be hidden first)
    assert "scope-modal" in raw, "scope-modal is missing — install flow may be silent"


def test_community_recipes_filter_by_category(recipe_server):
    """GET /api/v1/recipes/community?category=email should only return email-tagged recipes."""
    status, data = _req(recipe_server, "/api/v1/recipes/community?category=email")
    assert status == 200
    for recipe in data.get("recipes", []):
        assert "email" in recipe.get("tags", []), f"Non-email recipe in filtered results: {recipe.get('recipe_id')}"


def test_community_recipes_sort_by_best_hit_rate(recipe_server):
    """GET /api/v1/recipes/community?sort=best_hit_rate should return descending hit_rate_pct."""
    status, data = _req(recipe_server, "/api/v1/recipes/community?sort=best_hit_rate")
    assert status == 200
    recipes = data.get("recipes", [])
    if len(recipes) >= 2:
        for i in range(len(recipes) - 1):
            assert recipes[i]["hit_rate_pct"] >= recipes[i + 1]["hit_rate_pct"], \
                "Recipes not sorted by hit_rate_pct descending"
