"""
Tests for Task 067 — Voice Notes
Browser: yinyang_server.py routes /api/v1/voice-notes/*
"""
import json
import sys

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


def test_voice_notes_empty():
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler()
    h._handle_voice_notes_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["notes"] == []
    assert data["total"] == 0


def test_voice_note_create():
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler({
        "audio_data": "base64encodedaudiodata",
        "format": "webm",
        "duration_seconds": 30,
        "title": "My first note",
    })
    h._handle_voice_note_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["status"] == "created"
    assert data["note"]["note_id"].startswith("vn_")
    assert data["note"]["status"] == "recorded"
    assert data["note"]["transcript_hash"] is None


def test_voice_note_audio_hashed():
    """audio_hash must be present and no raw audio stored."""
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler({
        "audio_data": "rawaudiopayload12345",
        "format": "ogg",
        "duration_seconds": 60,
        "title": "Hash test",
    })
    h._handle_voice_note_create()
    status, data = h._responses[0]
    assert status == 201
    note = data["note"]
    assert "audio_hash" in note
    assert len(note["audio_hash"]) == 64  # SHA-256 hex
    # raw audio must NOT be stored
    assert "audio_data" not in note


def test_voice_note_invalid_format():
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler({
        "audio_data": "somedata",
        "format": "mp3",  # not in AUDIO_FORMATS
        "duration_seconds": 10,
        "title": "Invalid format",
    })
    h._handle_voice_note_create()
    status, data = h._responses[0]
    assert status == 400
    assert "format" in data["error"]


def test_voice_note_duration_too_long():
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler({
        "audio_data": "somedata",
        "format": "wav",
        "duration_seconds": 9999999,  # way beyond MAX_DURATION_SECONDS
        "title": "Too long",
    })
    h._handle_voice_note_create()
    status, data = h._responses[0]
    assert status == 400
    assert "duration" in data["error"]


def test_voice_note_get():
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler({
        "audio_data": "gettest",
        "format": "mp4",
        "duration_seconds": 45,
        "title": "Get test",
    })
    h._handle_voice_note_create()
    note_id = h._responses[0][1]["note"]["note_id"]

    h2 = _make_handler()
    h2._handle_voice_note_get(note_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["note"]["note_id"] == note_id
    assert data["note"]["title"] == "Get test"


def test_voice_note_delete():
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler({
        "audio_data": "deletetest",
        "format": "webm",
        "duration_seconds": 15,
        "title": "Delete test",
    })
    h._handle_voice_note_create()
    note_id = h._responses[0][1]["note"]["note_id"]

    h2 = _make_handler()
    h2._handle_voice_note_delete(note_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    assert len(ys._VOICE_NOTES) == 0


def test_voice_note_transcribe():
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler({
        "audio_data": "transcribetest",
        "format": "ogg",
        "duration_seconds": 120,
        "title": "Transcribe me",
    })
    h._handle_voice_note_create()
    note_id = h._responses[0][1]["note"]["note_id"]

    import hashlib
    t_hash = hashlib.sha256("This is the transcript".encode()).hexdigest()
    h2 = _make_handler({"transcript_hash": t_hash})
    h2._handle_voice_note_transcribe(note_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "transcribed"
    assert data["note"]["status"] == "transcribed"
    assert data["note"]["transcript_hash"] == t_hash


def test_voice_note_stats():
    import yinyang_server as ys
    ys._VOICE_NOTES.clear()
    h = _make_handler({
        "audio_data": "statstest",
        "format": "wav",
        "duration_seconds": 300,
        "title": "Stats note",
    })
    h._handle_voice_note_create()

    h2 = _make_handler()
    h2._handle_voice_notes_stats()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert "recorded" in data
    assert "transcribed" in data
    assert "archived" in data
    assert data["total_duration_seconds"] >= 300


def test_no_port_9222_in_voice_notes():
    """No port 9222 references in voice notes files."""
    files = [
        "/home/phuc/projects/solace-browser/web/voice-notes.html",
        "/home/phuc/projects/solace-browser/web/js/voice-notes.js",
        "/home/phuc/projects/solace-browser/web/css/voice-notes.css",
    ]
    for path in files:
        with open(path) as f:
            content = f.read()
        assert "9222" not in content, f"Port 9222 found in {path}"
