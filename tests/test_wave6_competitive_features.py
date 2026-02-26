from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from competitive_features import (
    load_proxy_config,
    select_proxy,
    solve_captcha,
    webvoyager_score,
)


def test_load_proxy_config_from_json(tmp_path: Path) -> None:
    p = tmp_path / "proxy.json"
    p.write_text(json.dumps({"proxies": [{"country": "us", "url": "http://us-proxy"}]}), encoding="utf-8")
    cfg = load_proxy_config(p)
    assert len(cfg["proxies"]) == 1


def test_load_proxy_config_from_line_format(tmp_path: Path) -> None:
    p = tmp_path / "proxy.txt"
    p.write_text("country=ca,url=http://ca-proxy\n", encoding="utf-8")
    cfg = load_proxy_config(p)
    assert cfg["proxies"][0]["country"] == "ca"


def test_select_proxy_by_country() -> None:
    cfg = {"proxies": [{"country": "us", "url": "http://us"}, {"country": "ca", "url": "http://ca"}]}
    out = select_proxy(cfg, country="ca")
    assert out is not None
    assert out["url"] == "http://ca"


def test_select_proxy_fallback_first() -> None:
    cfg = {"proxies": [{"country": "us", "url": "http://us"}]}
    out = select_proxy(cfg, country="fr")
    assert out is not None
    assert out["url"] == "http://us"


def test_solve_captcha_mock_recaptcha() -> None:
    out = solve_captcha(
        provider="mock",
        captcha_type="recaptcha_v2",
        site_key="abc123",
        page_url="https://example.com",
    )
    assert out["ok"] is True
    assert out["captcha_type"] == "recaptcha_v2"


def test_solve_captcha_mock_hcaptcha() -> None:
    out = solve_captcha(
        provider="mock",
        captcha_type="hcaptcha",
        site_key="xyz987",
        page_url="https://example.com",
    )
    assert out["ok"] is True
    assert out["captcha_type"] == "hcaptcha"


def test_solve_captcha_rejects_unknown_type() -> None:
    out = solve_captcha(
        provider="mock",
        captcha_type="image",
        site_key="x",
        page_url="https://example.com",
    )
    assert out["ok"] is False


def test_webvoyager_score_computation() -> None:
    out = webvoyager_score([{"passed": True}, {"passed": False}, {"passed": True}])
    assert out["total"] == 3
    assert out["passed"] == 2
    assert out["score"] == 66.67


def test_webvoyager_empty_score() -> None:
    out = webvoyager_score([])
    assert out["score"] == 0.0
