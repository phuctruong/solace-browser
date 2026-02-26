from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from browser.context import BrowserContext
from oauth3.vault import OAuth3Vault


@pytest.mark.asyncio
async def test_browser_context_launch(tmp_path: Path) -> None:
    vault = OAuth3Vault(
        encryption_key=b"3" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "vault.enc.json",
    )
    token = vault.issue_token(["browser.read", "browser.screenshot", "browser.dom"], ttl_seconds=3600)

    ctx = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
        seed=7,
    )
    result = await ctx.launch()

    assert result["status"] == "launched"
    await ctx.close()


@pytest.mark.asyncio
async def test_browser_navigate_checks_scope(tmp_path: Path) -> None:
    vault = OAuth3Vault(
        encryption_key=b"4" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "vault.enc.json",
    )
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)

    ctx = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
    )
    await ctx.launch()

    ok = await ctx.navigate("https://mail.google.com/mail/u/0/#inbox")
    blocked = await ctx.navigate("https://www.linkedin.com/feed/")

    assert ok["status"] == "success"
    assert blocked["status"] == "blocked"
    await ctx.close()


@pytest.mark.asyncio
async def test_browser_revocation_blocks_action(tmp_path: Path) -> None:
    vault = OAuth3Vault(
        encryption_key=b"5" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "vault.enc.json",
    )
    token = vault.issue_token(["gmail.read.inbox"], ttl_seconds=3600)

    ctx = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
    )
    await ctx.launch()

    first = await ctx.navigate("https://mail.google.com/mail/u/0/#inbox")
    vault.revoke_token(token["token_id"])
    second = await ctx.navigate("https://mail.google.com/mail/u/0/#inbox")

    assert first["status"] == "success"
    assert second["status"] == "blocked"
    await ctx.close()


@pytest.mark.asyncio
async def test_browser_actions_enforce_scope_every_time(tmp_path: Path) -> None:
    vault = OAuth3Vault(
        encryption_key=b"6" * 32,
        evidence_log=tmp_path / "oauth3_audit.jsonl",
        storage_path=tmp_path / "vault.enc.json",
    )
    token = vault.issue_token(["browser.read"], ttl_seconds=3600)

    ctx = BrowserContext(
        oauth3_vault=vault,
        token_id=token["token_id"],
        evidence_log=tmp_path / "browser_events.jsonl",
    )
    await ctx.launch()

    # navigate uses browser.read -> allowed
    nav = await ctx.navigate("https://example.com")
    # screenshot requires browser.screenshot -> blocked
    shot = await ctx.screenshot(path=str(tmp_path / "shot.png"))

    assert nav["status"] == "success"
    assert shot["status"] == "blocked"

    with pytest.raises(PermissionError):
        await ctx.evaluate("() => document.title")

    await ctx.close()
