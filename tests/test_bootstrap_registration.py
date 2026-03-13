import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys


def _count_installed_apps(apps_root: Path) -> int:
    return sum(1 for path in apps_root.glob("*/apps/*") if path.is_dir())


def _make_handler(body: dict | None = None):
    class FakeHandler(ys.YinyangHandler):
        def __init__(self):
            self._responses = []
            self._body = body or {}

        def _read_json_body(self):
            return self._body

        def _send_json(self, data, status=200):
            self._responses.append((status, data))

    return FakeHandler()


def test_bootstrap_default_only_installs_4_domains(tmp_path, monkeypatch):
    monkeypatch.setattr(ys.Path, "home", lambda: tmp_path)

    result = ys._handle_domains_bootstrap(default_only=True)

    apps_root = tmp_path / ".solace" / "apps"
    installed = sorted(path.name for path in apps_root.iterdir() if path.is_dir())
    assert result["bootstrapped_domains"] == 4
    assert result["bootstrapped_apps"] == 7
    assert "solaceagi.com" in installed
    assert _count_installed_apps(apps_root) == 7


def test_bootstrap_skips_login_required_domains(tmp_path, monkeypatch):
    monkeypatch.setattr(ys.Path, "home", lambda: tmp_path)

    ys._handle_domains_bootstrap(default_only=True)

    apps_root = tmp_path / ".solace" / "apps"
    installed = {path.name for path in apps_root.iterdir() if path.is_dir()}
    assert "linkedin.com" not in installed
    assert "github.com" not in installed


def test_registration_triggers_bootstrap(tmp_path, monkeypatch):
    monkeypatch.setattr(ys.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(ys, "ONBOARDING_PATH", tmp_path / ".solace" / "onboarding.json")
    monkeypatch.setattr(ys, "NOTIFICATIONS_PATH", tmp_path / ".solace" / "notifications.json")

    handler = _make_handler({"token": "test"})
    handler._handle_auth_complete()
    status, data = handler._responses[0]

    assert status == 200
    assert data["status"] == "complete"
    assert data.get("bootstrapped_domains", 0) == 4
    assert data.get("bootstrapped_apps", 0) == 7
    assert (tmp_path / ".solace" / "apps" / "google.com" / "manifest.yaml").exists()


def test_bootstrap_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(ys.Path, "home", lambda: tmp_path)

    first = ys._handle_domains_bootstrap(default_only=True)
    second = ys._handle_domains_bootstrap(default_only=True)

    assert first["bootstrapped_domains"] == second["bootstrapped_domains"]
    assert first["bootstrapped_apps"] == second["bootstrapped_apps"]
    assert _count_installed_apps(tmp_path / ".solace" / "apps") == 7
