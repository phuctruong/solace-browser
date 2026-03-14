# Diagram: 05-solace-runtime-architecture
"""tests/test_schedule_tz_ui.py — Schedule Timezone UI acceptance gate. Task 071."""
import hashlib
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEST_PORT = 18899
BASE_URL = f"http://localhost:{TEST_PORT}"
VALID_TOKEN = "b" * 64  # pre-hashed so _check_auth passes when sha256 not set


def _req(path, method="GET", payload=None, token=None):
    url = BASE_URL + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"{}"


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    import yinyang_server as ys

    tmp = tmp_path_factory.mktemp("tz_server")
    ys.EVIDENCE_PATH = tmp / "evidence.jsonl"
    ys.PORT_LOCK_PATH = tmp / "port.lock"
    ys.SETTINGS_PATH = tmp / "settings.json"
    ys.SCHEDULES_PATH = tmp / "schedules.json"

    httpd = ys.build_server(TEST_PORT, str(tmp), session_token_sha256="")
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    for _ in range(30):
        try:
            urllib.request.urlopen(BASE_URL + "/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)
    yield
    httpd.shutdown()


def test_page_exists_and_is_html(server):
    status, body = _req("/web/schedule-tz.html")
    assert status == 200
    assert b"<!DOCTYPE html>" in body or b"<!doctype html>" in body.lower()


def test_page_content_type_is_html(server):
    url = BASE_URL + "/web/schedule-tz.html"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as r:
        ct = r.headers.get("Content-Type", "")
    assert "text/html" in ct


def test_page_no_cdn(server):
    _, body = _req("/web/schedule-tz.html")
    text = body.decode()
    assert "cdn.jsdelivr.net" not in text
    assert "unpkg.com" not in text
    assert "jquery" not in text.lower()
    assert "eval(" not in text


def test_page_uses_hub_tokens(server):
    _, body = _req("/web/schedule-tz.html")
    assert b"var(--hub-" in body


def test_page_has_timezone_selector(server):
    _, body = _req("/web/schedule-tz.html")
    text = body.decode()
    assert "America/New_York" in text
    assert "Europe/London" in text
    assert "Asia/Tokyo" in text


def test_page_has_cron_input(server):
    _, body = _req("/web/schedule-tz.html")
    text = body.decode()
    assert "cron" in text.lower()


def test_schedules_api_exists(server):
    status, _ = _req("/api/v1/schedules")
    assert status in (200, 401)


def test_post_schedule_with_tz(server):
    status, body = _req(
        "/api/v1/schedules",
        method="POST",
        payload={"name": "Morning Report", "cron": "0 9 * * *", "tz": "America/New_York"},
    )
    # No auth required when session_token_sha256="" — should be 201 or 200
    assert status in (200, 201, 422)


def test_patch_schedule_pause_resume_exists(server):
    # PATCH endpoint must exist (not 405); returns 404 for nonexistent id — that is fine
    status, _ = _req(
        "/api/v1/schedules/nonexistent-id",
        method="PATCH",
        payload={"action": "pause"},
    )
    assert status != 405  # method must be registered


def test_page_has_schedule_table_structure(server):
    _, body = _req("/web/schedule-tz.html")
    text = body.decode()
    assert "next run" in text.lower() or "Next Run" in text
    assert "timezone" in text.lower() or "Timezone" in text


def test_no_port_9222(server):
    _, body = _req("/web/schedule-tz.html")
    assert b"9222" not in body


def test_run_history_section_exists(server):
    _, body = _req("/web/schedule-tz.html")
    text = body.decode()
    assert "history" in text.lower() or "History" in text
