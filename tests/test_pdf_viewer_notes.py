"""Tests for PDF Viewer Notes (Task 124). 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-124").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method, path, body=None, auth=True):
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


def _reset():
    ys._PDF_NOTES.clear()


def test_note_create():
    """POST creates note with pdn_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
        "pdf_url": "https://example.com/doc.pdf",
        "note_type": "text",
        "content": "This is a note",
        "page_number": 1,
        "position": "100,200",
    })
    h._handle_pdf_note_create()
    assert h._status == 201
    note = h._response["note"]
    assert note["note_id"].startswith("pdn_")


def test_note_pdf_hashed():
    """pdf_hash is stored, not raw URL."""
    _reset()
    h = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
        "pdf_url": "https://secret.example.com/private.pdf",
        "note_type": "highlight",
        "content": "highlighted text",
        "page_number": 2,
        "position": "50,100",
    })
    h._handle_pdf_note_create()
    assert h._status == 201
    note = h._response["note"]
    assert "pdf_hash" in note
    assert "https://secret.example.com/private.pdf" not in str(note)
    expected = hashlib.sha256(b"https://secret.example.com/private.pdf").hexdigest()
    assert note["pdf_hash"] == expected


def test_note_content_hashed():
    """content_hash is stored, not raw content."""
    _reset()
    raw_content = "This is my private annotation text"
    h = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
        "pdf_url": "https://example.com/doc.pdf",
        "note_type": "summary",
        "content": raw_content,
        "page_number": 5,
        "position": "10,20",
    })
    h._handle_pdf_note_create()
    assert h._status == 201
    note = h._response["note"]
    assert "content_hash" in note
    assert raw_content not in str(note)
    expected = hashlib.sha256(raw_content.encode()).hexdigest()
    assert note["content_hash"] == expected


def test_note_invalid_type():
    """Unknown note_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
        "pdf_url": "https://example.com/doc.pdf",
        "note_type": "INVALID_TYPE",
        "content": "some text",
        "page_number": 1,
        "position": "0,0",
    })
    h._handle_pdf_note_create()
    assert h._status == 400


def test_note_invalid_page():
    """page_number=0 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
        "pdf_url": "https://example.com/doc.pdf",
        "note_type": "bookmark",
        "content": "test",
        "page_number": 0,
        "position": "0,0",
    })
    h._handle_pdf_note_create()
    assert h._status == 400


def test_note_list():
    """GET returns list of notes."""
    _reset()
    for i in range(3):
        h = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
            "pdf_url": f"https://example.com/doc{i}.pdf",
            "note_type": "text",
            "content": f"Note {i}",
            "page_number": i + 1,
            "position": f"{i*10},{i*10}",
        })
        h._handle_pdf_note_create()
    lh = FakeHandler("GET", "/api/v1/pdf-notes/notes")
    lh._handle_pdf_notes_list()
    assert lh._status == 200
    assert "notes" in lh._response
    assert lh._response["total"] == 3


def test_note_by_pdf():
    """GET /by-pdf?pdf_hash=xxx returns only notes for that PDF."""
    _reset()
    pdf_url = "https://example.com/specific.pdf"
    pdf_hash = hashlib.sha256(pdf_url.encode()).hexdigest()
    # Create note for specific PDF
    h1 = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
        "pdf_url": pdf_url,
        "note_type": "text",
        "content": "Note for specific PDF",
        "page_number": 1,
        "position": "0,0",
    })
    h1._handle_pdf_note_create()
    # Create note for different PDF
    h2 = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
        "pdf_url": "https://example.com/other.pdf",
        "note_type": "text",
        "content": "Note for other PDF",
        "page_number": 1,
        "position": "0,0",
    })
    h2._handle_pdf_note_create()
    # Filter by specific PDF
    fh = FakeHandler("GET", f"/api/v1/pdf-notes/notes/by-pdf?pdf_hash={pdf_hash}")
    fh._handle_pdf_notes_by_pdf()
    assert fh._status == 200
    assert fh._response["total"] == 1
    assert fh._response["notes"][0]["pdf_hash"] == pdf_hash


def test_note_delete():
    """DELETE removes note from list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
        "pdf_url": "https://example.com/doc.pdf",
        "note_type": "question",
        "content": "Delete me",
        "page_number": 3,
        "position": "5,5",
    })
    h._handle_pdf_note_create()
    note_id = h._response["note"]["note_id"]

    dh = FakeHandler("DELETE", f"/api/v1/pdf-notes/notes/{note_id}")
    dh._handle_pdf_note_delete(note_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"

    lh = FakeHandler("GET", "/api/v1/pdf-notes/notes")
    lh._handle_pdf_notes_list()
    assert lh._response["total"] == 0


def test_note_stats():
    """GET /stats returns total_pdfs count."""
    _reset()
    for pdf_url, note_type in [
        ("https://example.com/a.pdf", "text"),
        ("https://example.com/a.pdf", "highlight"),
        ("https://example.com/b.pdf", "bookmark"),
    ]:
        h = FakeHandler("POST", "/api/v1/pdf-notes/notes", {
            "pdf_url": pdf_url,
            "note_type": note_type,
            "content": "content",
            "page_number": 1,
            "position": "0,0",
        })
        h._handle_pdf_note_create()
    sh = FakeHandler("GET", "/api/v1/pdf-notes/stats")
    sh._handle_pdf_notes_stats()
    assert sh._status == 200
    assert sh._response["total_notes"] == 3
    assert sh._response["total_pdfs"] == 2
    assert "by_type" in sh._response


def test_no_banned_port_in_pdf_notes():
    """Grep check: banned debug port must not appear in this file."""
    source = pathlib.Path(__file__)
    banned = "9" + "222"
    assert banned not in source.read_text()
