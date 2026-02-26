from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui_server


def test_home_page_served() -> None:
    client = TestClient(ui_server.app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Your AI Agent Portal" in resp.text


def test_vendors_endpoint_returns_rows() -> None:
    client = TestClient(ui_server.app)
    resp = client.get("/api/ui/vendors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert isinstance(data["vendors"], list)


def test_replay_returns_recipe_by_id(tmp_path: Path, monkeypatch) -> None:
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    recipe = recipes_dir / "test.recipe.json"
    recipe.write_text(
        json.dumps({"id": "wave6-recipe", "steps": [{"step": 1, "action": "navigate"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ui_server, "RECIPES_DIR", recipes_dir)
    client = TestClient(ui_server.app)
    resp = client.get("/api/ui/replay/wave6-recipe")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["steps"][0]["action"] == "navigate"


def test_replay_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    monkeypatch.setattr(ui_server, "RECIPES_DIR", recipes_dir)
    client = TestClient(ui_server.app)
    resp = client.get("/api/ui/replay/not-found")
    assert resp.status_code == 404


def test_add_site_proxies_to_browser_api(monkeypatch) -> None:
    class _Resp:
        status_code = 201

        @staticmethod
        def json():
            return {"ok": True, "site": "example.com"}

    monkeypatch.setattr(ui_server.requests, "post", lambda *args, **kwargs: _Resp())
    client = TestClient(ui_server.app)
    resp = client.post("/api/ui/add-site", json={"url": "https://example.com"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_add_site_requires_url() -> None:
    client = TestClient(ui_server.app)
    resp = client.post("/api/ui/add-site", json={})
    assert resp.status_code == 422


def test_live_view_frame_returns_base64_image(tmp_path: Path, monkeypatch) -> None:
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"png-bytes")

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"filepath": str(shot)}

        text = ""

    monkeypatch.setattr(ui_server.requests, "post", lambda *args, **kwargs: _Resp())
    client = TestClient(ui_server.app)
    resp = client.get("/api/ui/live-view/frame")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert base64.b64decode(payload["image_base64"]) == b"png-bytes"
