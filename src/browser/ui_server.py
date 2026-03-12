#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
PRIMEWIKI_DIR = ROOT / "data" / "default" / "primewiki"
RECIPES_DIR = ROOT / "data" / "default" / "recipes"
API_BASE = os.getenv("SOLACE_BROWSER_API_BASE", "http://127.0.0.1:8888")

DEFAULT_VENDORS = [
    "linkedin",
    "gmail",
    "reddit",
    "hackernews",
    "notion",
    "substack",
]

app = FastAPI(title="Solace Browser UI Server", version="1.0.0")
app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


def _all_recipe_files() -> list[Path]:
    out = list(RECIPES_DIR.glob("*.recipe.json"))
    out.extend(RECIPES_DIR.glob("*/*.recipe.json"))
    return sorted(p for p in out if p.is_file())


def _count_site_recipes(site: str) -> int:
    key = site.lower()
    count = 0
    for p in _all_recipe_files():
        lower = p.as_posix().lower()
        if f"/{key}/" in lower or f"{key}-" in p.name.lower():
            count += 1
    return count


def _primewiki_counts(site: str) -> tuple[bool, int]:
    site_dir = PRIMEWIKI_DIR / site
    if not site_dir.exists():
        return False, 0
    return True, len(list(site_dir.glob("*.mmd")))


def _session_status() -> str:
    try:
        resp = requests.get(f"{API_BASE}/api/status", timeout=2)
        if not resp.ok:
            return "none"
        data = resp.json()
        session = data.get("session", {})
        if session.get("exists"):
            return "active"
        return "none"
    except (requests.RequestException, ValueError, KeyError, OSError):
        return "none"


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(WEB_DIR / "home.html")


@app.get("/api/ui/vendors")
async def vendors() -> dict[str, Any]:
    session = _session_status()
    rows = []
    # Add known defaults first, then discovered dirs.
    seen = set(DEFAULT_VENDORS)
    for p in PRIMEWIKI_DIR.iterdir():
        if p.is_dir():
            seen.add(p.name.lower())

    for site in sorted(seen):
        has_wiki, snapshots = _primewiki_counts(site)
        rows.append(
            {
                "site": site,
                "primewiki_mapped": has_wiki,
                "snapshot_pages_mapped": snapshots,
                "snapshot_pages_total": snapshots if snapshots > 0 else 0,
                "recipe_count": _count_site_recipes(site),
                "session_status": session,
                "actions": ["run_recipe", "add_snapshot", "map_site", "view_wiki"],
            }
        )
    return {"vendors": rows, "count": len(rows)}


@app.post("/api/ui/add-site")
async def add_site(body: dict[str, Any]) -> dict[str, Any]:
    url = str(body.get("url", "")).strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")
    resp = requests.post(f"{API_BASE}/api/discovery/map-site", json={"url": url}, timeout=15)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.get("/api/ui/replay/{recipe_id}")
async def replay(recipe_id: str) -> dict[str, Any]:
    target = None
    for p in _all_recipe_files():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if data.get("id") == recipe_id:
            target = data
            break
    if target is None:
        raise HTTPException(status_code=404, detail="recipe not found")
    return {
        "ok": True,
        "recipe_id": recipe_id,
        "steps": target.get("steps", []),
        "replay_mode": "step-by-step",
    }


@app.get("/api/ui/live-view/frame")
async def live_view_frame() -> dict[str, Any]:
    screenshot = requests.post(f"{API_BASE}/api/screenshot", json={}, timeout=10)
    if screenshot.status_code >= 400:
        raise HTTPException(status_code=screenshot.status_code, detail=screenshot.text)
    payload = screenshot.json()
    filename = payload.get("filepath")
    if not filename:
        raise HTTPException(status_code=500, detail="screenshot filepath missing")
    shot = Path(filename)
    if not shot.exists():
        raise HTTPException(status_code=404, detail="screenshot not found")
    raw = shot.read_bytes()
    return {
        "ok": True,
        "mime": "image/png",
        "captured_at_ms": int(time.time() * 1000),
        "image_base64": base64.b64encode(raw).decode("ascii"),
    }


@app.websocket("/ws/live-view")
async def ws_live_view(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            try:
                frame = await live_view_frame()
            except (OSError, ValueError, KeyError, requests.RequestException) as exc:
                frame = {"ok": False, "error": str(exc)}
            await ws.send_json(frame)
            await asyncio.sleep(2)
    except (WebSocketDisconnect, ConnectionError, asyncio.CancelledError):
        return


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("SOLACE_UI_HOST", "127.0.0.1")
    port = int(os.getenv("SOLACE_UI_PORT", "9223"))
    uvicorn.run("ui_server:app", host=host, port=port, reload=False)
