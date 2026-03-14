# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 153 — Page Annotation
Browser: yinyang_server.py routes /api/v1/annotations/*
"""
import sys
import json
import re

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


def _valid_body(**overrides):
    base = {
        "annotation_type": "highlight",
        "url": "https://example.com/article",
        "selected_text": "This is the selected text",
        "selected_text_length": 25,
        "color": "yellow",
        "note": "My note",
    }
    base.update(overrides)
    return base


def test_annotation_create():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    h = _make_handler(_valid_body())
    h._handle_ann_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["annotation_id"].startswith("ann_")


def test_annotation_url_hashed():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    h = _make_handler(_valid_body(url="https://secret.example.com/private"))
    h._handle_ann_create()
    _, resp = h._responses[0]
    ann_id = resp["annotation_id"]
    with ys._ANNOTATION_LOCK:
        ann = next(a for a in ys._ANNOTATIONS if a["annotation_id"] == ann_id)
    assert "url_hash" in ann
    assert "url" not in ann


def test_annotation_text_hashed():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    h = _make_handler(_valid_body(selected_text="very private text content"))
    h._handle_ann_create()
    _, resp = h._responses[0]
    ann_id = resp["annotation_id"]
    with ys._ANNOTATION_LOCK:
        ann = next(a for a in ys._ANNOTATIONS if a["annotation_id"] == ann_id)
    assert "selected_text_hash" in ann
    assert "selected_text" not in ann


def test_annotation_invalid_type():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    h = _make_handler(_valid_body(annotation_type="sticky"))
    h._handle_ann_create()
    status, data = h._responses[0]
    assert status == 400


def test_annotation_invalid_color():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    h = _make_handler(_valid_body(color="orange"))
    h._handle_ann_create()
    status, data = h._responses[0]
    assert status == 400


def test_annotation_note_too_long():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    long_note = "x" * 501
    h = _make_handler(_valid_body(note=long_note))
    h._handle_ann_create()
    status, data = h._responses[0]
    assert status == 400


def test_annotation_list():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    h1 = _make_handler(_valid_body(color="blue"))
    h1._handle_ann_create()
    h2 = _make_handler()
    h2._handle_ann_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["annotations"], list)


def test_annotation_delete():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    h1 = _make_handler(_valid_body(color="green"))
    h1._handle_ann_create()
    ann_id = h1._responses[0][1]["annotation_id"]
    h2 = _make_handler()
    h2._handle_ann_delete(ann_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    with ys._ANNOTATION_LOCK:
        assert not any(a["annotation_id"] == ann_id for a in ys._ANNOTATIONS)


def test_annotation_stats():
    import yinyang_server as ys
    ys._ANNOTATIONS.clear()
    for color in ["yellow", "blue", "red"]:
        h = _make_handler(_valid_body(color=color, annotation_type="comment"))
        h._handle_ann_create()
    h_stats = _make_handler()
    h_stats._handle_ann_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert "by_type" in data
    assert "by_color" in data
    assert data["total_annotations"] == 3


def test_no_port_9222_in_annotations():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
