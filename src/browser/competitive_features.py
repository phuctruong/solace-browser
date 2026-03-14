# Diagram: 01-triangle-architecture
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_proxy_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"proxies": []}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {"proxies": []}
    if text.startswith("{"):
        data = json.loads(text)
    else:
        # Minimal line-based fallback:
        # country=US,url=http://host:port
        proxies = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = dict(part.split("=", 1) for part in line.split(",") if "=" in part)
            if "url" in parts:
                proxies.append({"country": parts.get("country", "any").lower(), "url": parts["url"]})
        data = {"proxies": proxies}
    if not isinstance(data, dict):
        return {"proxies": []}
    proxies = data.get("proxies", [])
    if not isinstance(proxies, list):
        proxies = []
    return {"proxies": proxies}


def select_proxy(config: dict[str, Any], country: str | None = None) -> dict[str, Any] | None:
    proxies = config.get("proxies", [])
    if not isinstance(proxies, list):
        return None
    if not proxies:
        return None
    if country:
        c = country.strip().lower()
        for proxy in proxies:
            if str(proxy.get("country", "")).lower() == c:
                return proxy
    return proxies[0]


def solve_captcha(
    *,
    provider: str,
    captcha_type: str,
    site_key: str,
    page_url: str,
    mock_token: str | None = None,
) -> dict[str, Any]:
    p = provider.strip().lower()
    ctype = captcha_type.strip().lower()
    if ctype not in {"recaptcha_v2", "hcaptcha"}:
        return {"ok": False, "error": "unsupported_captcha_type"}
    if p == "mock":
        token = mock_token or f"mock_{ctype}_{site_key[:8]}"
        return {"ok": True, "provider": "mock", "captcha_type": ctype, "token": token, "page_url": page_url}
    return {"ok": False, "error": "provider_not_configured"}


def webvoyager_score(cases: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(cases)
    if total == 0:
        return {"ok": True, "total": 0, "passed": 0, "score": 0.0}
    passed = sum(1 for c in cases if bool(c.get("passed")))
    return {
        "ok": True,
        "total": total,
        "passed": passed,
        "score": round((passed / total) * 100.0, 2),
    }
