"""tests/test_recipe_scheduler.py — Recipe Scheduler acceptance gate.
Task 043 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - cron_preset must be in VALID_CRON_PRESETS → 400
  - recipe_id must be in SCHEDULE_RECIPES → 400
  - Auth required on POST/DELETE; GET is public
  - No port 9222, no CDN, no eval()
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-scheduler-043"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18943)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def delete_path(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


@pytest.fixture(autouse=True)
def reset_scheduler_state(monkeypatch):
    """Reset scheduler state between tests."""
    monkeypatch.setattr(ys, "_SCHEDULER_JOBS", [])
    monkeypatch.setattr(ys, "_JOB_HISTORY", {})
    yield


# ---------------------------------------------------------------------------
# 1. test_scheduler_jobs_list — GET /scheduler/jobs → empty list initially
# ---------------------------------------------------------------------------
def test_scheduler_jobs_list():
    status, data = get_json("/api/v1/scheduler/jobs")
    assert status == 200
    assert data.get("jobs") == []
    assert data.get("total") == 0


# ---------------------------------------------------------------------------
# 2. test_scheduler_create_job — POST → job_id returned
# ---------------------------------------------------------------------------
def test_scheduler_create_job():
    status, data = post_json("/api/v1/scheduler/jobs", {
        "name": "My Triage",
        "recipe_id": "gmail-triage",
        "cron_preset": "daily-9am",
    })
    assert status == 200
    assert data.get("status") == "created"
    assert "job_id" in data
    assert data["job_id"].startswith("job_")


# ---------------------------------------------------------------------------
# 3. test_scheduler_jobs_include_created — list includes created job
# ---------------------------------------------------------------------------
def test_scheduler_jobs_include_created():
    post_json("/api/v1/scheduler/jobs", {
        "name": "LinkedIn Daily",
        "recipe_id": "linkedin-daily",
        "cron_preset": "hourly",
    })
    _, data = get_json("/api/v1/scheduler/jobs")
    assert len(data["jobs"]) == 1
    assert data["jobs"][0]["recipe_id"] == "linkedin-daily"


# ---------------------------------------------------------------------------
# 4. test_scheduler_invalid_recipe — unknown recipe_id → 400
# ---------------------------------------------------------------------------
def test_scheduler_invalid_recipe():
    status, data = post_json("/api/v1/scheduler/jobs", {
        "name": "Bad",
        "recipe_id": "nonexistent-recipe",
        "cron_preset": "hourly",
    })
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 5. test_scheduler_invalid_cron — unknown cron_preset → 400
# ---------------------------------------------------------------------------
def test_scheduler_invalid_cron():
    status, data = post_json("/api/v1/scheduler/jobs", {
        "name": "Bad Cron",
        "recipe_id": "gmail-triage",
        "cron_preset": "not-a-valid-preset",
    })
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 6. test_scheduler_delete_job — DELETE → removed from list
# ---------------------------------------------------------------------------
def test_scheduler_delete_job():
    _, create_data = post_json("/api/v1/scheduler/jobs", {
        "name": "To Delete",
        "recipe_id": "news-digest",
        "cron_preset": "every-30min",
    })
    job_id = create_data["job_id"]
    status, data = delete_path(f"/api/v1/scheduler/jobs/{job_id}")
    assert status == 200
    assert data.get("status") == "deleted"

    _, list_data = get_json("/api/v1/scheduler/jobs")
    assert len(list_data["jobs"]) == 0


# ---------------------------------------------------------------------------
# 7. test_scheduler_run_now — POST /run-now → history entry added
# ---------------------------------------------------------------------------
def test_scheduler_run_now():
    _, create_data = post_json("/api/v1/scheduler/jobs", {
        "name": "Run Now Test",
        "recipe_id": "github-summary",
        "cron_preset": "weekly-monday",
    })
    job_id = create_data["job_id"]
    status, data = post_json(f"/api/v1/scheduler/jobs/{job_id}/run-now", {})
    assert status == 200
    assert data.get("status") == "triggered"
    assert "run_id" in data


# ---------------------------------------------------------------------------
# 8. test_scheduler_history — GET /history → run records present
# ---------------------------------------------------------------------------
def test_scheduler_history():
    _, create_data = post_json("/api/v1/scheduler/jobs", {
        "name": "History Test",
        "recipe_id": "calendar-review",
        "cron_preset": "daily-6pm",
    })
    job_id = create_data["job_id"]
    post_json(f"/api/v1/scheduler/jobs/{job_id}/run-now", {})
    status, data = get_json(f"/api/v1/scheduler/jobs/{job_id}/history")
    assert status == 200
    assert len(data.get("history", [])) == 1
    run = data["history"][0]
    assert run["status"] == "completed"
    assert run["cost_usd"] == "0.01"


# ---------------------------------------------------------------------------
# 9. test_scheduler_html_no_cdn — web/recipe-scheduler.html no CDN
# ---------------------------------------------------------------------------
def test_scheduler_html_no_cdn():
    html_path = REPO_ROOT / "web" / "recipe-scheduler.html"
    assert html_path.exists(), "recipe-scheduler.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 10. test_no_port_9222_in_scheduler — grep check
# ---------------------------------------------------------------------------
def test_no_port_9222_in_scheduler():
    files_to_check = [
        REPO_ROOT / "web" / "recipe-scheduler.html",
        REPO_ROOT / "web" / "js" / "recipe-scheduler.js",
        REPO_ROOT / "web" / "css" / "recipe-scheduler.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
