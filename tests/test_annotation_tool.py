"""Tests for Task 093 — Annotation Tool."""
import sys
import pathlib
REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import json
import hashlib
import yinyang_server as ys
from io import BytesIO
from unittest.mock import patch

VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method="GET", path="/", body=None, auth=True):
        self.command = method
        self.path = path
        self._body = json.dumps(body).encode() if body else b""
        self._auth = auth
        self._status = None
        self._response = None
        self.headers = {
            "Content-Length": str(len(self._body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.server = type("S", (), {
            "session_token_sha256": VALID_TOKEN,
            "repo_root": str(REPO_ROOT),
        })()
        self.rfile = BytesIO(self._body)
        self.wfile = BytesIO()

    def send_response(self, code):
        self._status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, code=200):
        self._status = code
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def log_message(self, *a):
        pass


def setup_function():
    with ys._ANNOTATION_LOCK:
        ys._ANNOTATIONS.clear()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _make_annotation_body(annotation_type="highlight", color="yellow"):
    return {
        "annotation_type": annotation_type,
        "color": color,
        "page_hash": _sha256("https://example.com/page"),
        "text_hash": _sha256("selected text"),
        "selector_hash": _sha256("#main > p"),
    }


def test_annotation_create_valid():
    """POST /api/v1/annotations creates annotation with ann_ prefix."""
    body = _make_annotation_body("highlight", "yellow")
    h = FakeHandler("POST", "/api/v1/annotations", body=body, auth=True)
    h._handle_annotation_create()
    assert h._status == 201
    assert h._response["annotation"]["annotation_id"].startswith("ann_")
    assert h._response["annotation"]["annotation_type"] == "highlight"
    assert h._response["annotation"]["color"] == "yellow"


def test_annotation_invalid_type():
    """POST rejects unknown annotation_type."""
    body = _make_annotation_body("unknown_type", "yellow")
    h = FakeHandler("POST", "/api/v1/annotations", body=body, auth=True)
    h._handle_annotation_create()
    assert h._status == 400


def test_annotation_invalid_color():
    """POST rejects color not in ANNOTATION_COLORS."""
    body = _make_annotation_body("note", "pink")
    h = FakeHandler("POST", "/api/v1/annotations", body=body, auth=True)
    h._handle_annotation_create()
    assert h._status == 400


def test_annotation_list():
    """GET /api/v1/annotations lists all annotations."""
    FakeHandler("POST", "/", body=_make_annotation_body("note", "blue"), auth=True)._handle_annotation_create()
    h = FakeHandler("GET", "/api/v1/annotations", auth=True)
    h._handle_annotation_list()
    assert h._status == 200
    assert isinstance(h._response["annotations"], list)
    assert h._response["total"] >= 1


def test_annotation_delete():
    """DELETE /api/v1/annotations/{id} removes annotation."""
    FakeHandler("POST", "/", body=_make_annotation_body(), auth=True)._handle_annotation_create()
    with ys._ANNOTATION_LOCK:
        ann_id = ys._ANNOTATIONS[-1]["annotation_id"]

    h = FakeHandler("DELETE", f"/api/v1/annotations/{ann_id}", auth=True)
    h._handle_annotation_delete(ann_id)
    assert h._status == 200
    assert h._response["annotation_id"] == ann_id

    with ys._ANNOTATION_LOCK:
        ids = [a["annotation_id"] for a in ys._ANNOTATIONS]
    assert ann_id not in ids


def test_annotation_delete_not_found():
    """DELETE non-existent annotation returns 404."""
    h = FakeHandler("DELETE", "/api/v1/annotations/ann_notexist", auth=True)
    h._handle_annotation_delete("ann_notexist")
    assert h._status == 404


def test_annotation_by_page():
    """GET /api/v1/annotations/by-page filters by page_hash."""
    page_hash = _sha256("https://specific-page.com")
    body = {
        "annotation_type": "todo",
        "color": "red",
        "page_hash": page_hash,
        "text_hash": _sha256("some text"),
        "selector_hash": _sha256("#div"),
    }
    FakeHandler("POST", "/", body=body, auth=True)._handle_annotation_create()

    # Create annotation on a different page
    FakeHandler("POST", "/", body=_make_annotation_body(), auth=True)._handle_annotation_create()

    class PageHandler(FakeHandler):
        @property
        def path(self):
            return f"/api/v1/annotations/by-page?page_hash={page_hash}"

        @path.setter
        def path(self, v):
            pass

    h = PageHandler("GET", f"/api/v1/annotations/by-page?page_hash={page_hash}", auth=True)
    h._handle_annotation_by_page()
    assert h._status == 200
    assert all(a["page_hash"] == page_hash for a in h._response["annotations"])
    assert h._response["total"] >= 1


def test_annotation_types_public():
    """GET /api/v1/annotations/types is public."""
    h = FakeHandler("GET", "/api/v1/annotations/types", auth=False)
    h._handle_annotation_types()
    assert h._status == 200
    assert "types" in h._response
    assert "highlight" in h._response["types"]
    assert "colors" in h._response
    assert "yellow" in h._response["colors"]


def test_annotation_requires_auth():
    """POST /api/v1/annotations requires auth."""
    body = _make_annotation_body()
    h = FakeHandler("POST", "/api/v1/annotations", body=body, auth=False)
    h._handle_annotation_create()
    assert h._status == 401


def test_annotation_with_note_hash():
    """POST accepts optional note_hash field."""
    body = _make_annotation_body("note", "green")
    body["note_hash"] = _sha256("my note text")
    h = FakeHandler("POST", "/api/v1/annotations", body=body, auth=True)
    h._handle_annotation_create()
    assert h._status == 201
    assert h._response["annotation"]["note_hash"] == _sha256("my note text")
