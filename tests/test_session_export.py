"""
Tests for Task 055 — Session Export
Browser: yinyang_server.py routes /api/v1/export/*
"""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")

TOKEN = "test-token-sha256"


def _make_handler(body=None, auth=True):
    import yinyang_server as ys

    class FakeHandler(ys.YinyangHandler):
        def __init__(self):
            self._token = TOKEN
            self._responses = []
            self._body = json.dumps(body).encode() if body else b"{}"

        def _read_json_body(self):
            return json.loads(self._body)

        def _send_json(self, data, status=200):
            self._responses.append((status, data))

        def _check_auth(self):
            if not auth:
                self._send_json({"error": "unauthorized"}, 401)
                return False
            return True

    return FakeHandler()


def test_export_jobs_empty():
    import yinyang_server as ys
    ys._EXPORT_JOBS.clear()
    h = _make_handler()
    h._handle_export_jobs_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["jobs"] == []
    assert data["total"] == 0


def test_export_create_job():
    import yinyang_server as ys
    ys._EXPORT_JOBS.clear()
    h = _make_handler({"format": "json", "scope": "all"})
    h._handle_export_job_create()
    status, data = h._responses[0]
    assert status == 200
    assert data["status"] == "created"
    assert data["job_id"].startswith("exp_")


def test_export_status_completed():
    import yinyang_server as ys
    ys._EXPORT_JOBS.clear()
    h = _make_handler({"format": "csv", "scope": "history"})
    h._handle_export_job_create()
    job_id = h._responses[0][1]["job_id"]

    h2 = _make_handler()
    h2._handle_export_job_get(job_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "completed"


def test_export_file_size_set():
    import yinyang_server as ys
    ys._EXPORT_JOBS.clear()
    h = _make_handler({"format": "html", "scope": "bookmarks"})
    h._handle_export_job_create()
    job_id = h._responses[0][1]["job_id"]

    h2 = _make_handler()
    h2._handle_export_job_get(job_id)
    _, data = h2._responses[0]
    assert data["file_size_bytes"] > 0
    assert data["row_count"] > 0


def test_export_get_by_id():
    import yinyang_server as ys
    ys._EXPORT_JOBS.clear()
    h = _make_handler({"format": "pdf", "scope": "notes"})
    h._handle_export_job_create()
    job_id = h._responses[0][1]["job_id"]

    h2 = _make_handler()
    h2._handle_export_job_get(job_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["job_id"] == job_id
    assert data["format"] == "pdf"
    assert data["scope"] == "notes"


def test_export_delete():
    import yinyang_server as ys
    ys._EXPORT_JOBS.clear()
    h = _make_handler({"format": "json", "scope": "all"})
    h._handle_export_job_create()
    job_id = h._responses[0][1]["job_id"]

    h2 = _make_handler()
    h2._handle_export_job_delete(job_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"


def test_export_invalid_format():
    import yinyang_server as ys
    ys._EXPORT_JOBS.clear()
    h = _make_handler({"format": "xlsx", "scope": "all"})
    h._handle_export_job_create()
    status, data = h._responses[0]
    assert status == 400
    assert "format" in data["error"]


def test_export_invalid_scope():
    import yinyang_server as ys
    ys._EXPORT_JOBS.clear()
    h = _make_handler({"format": "json", "scope": "everything"})
    h._handle_export_job_create()
    status, data = h._responses[0]
    assert status == 400
    assert "scope" in data["error"]


def test_export_formats_list():
    import yinyang_server as ys
    h = _make_handler()
    h._handle_export_formats_list()
    status, data = h._responses[0]
    assert status == 200
    assert "formats" in data
    assert "json" in data["formats"]
    assert "csv" in data["formats"]


def test_no_port_9222_in_export():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    import re
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
