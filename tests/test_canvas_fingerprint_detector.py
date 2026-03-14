# Diagram: 05-solace-runtime-architecture
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yinyang_server as ys


REPO_ROOT = Path(__file__).resolve().parent.parent


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._response_code = None
        self._response_body = None

    def _send_json(self, code, body):
        self._response_code = code
        self._response_body = body

    def _require_auth(self):
        pass


def _reset():
    with ys._FP_DETECTOR_LOCK:
        ys._FP_DETECTIONS.clear()


def _payload(**overrides):
    payload = {
        "technique": "toDataURL",
        "url": "https://example.com",
        "script_url": "https://scripts.example.com/app.js",
        "was_blocked": False,
        "confidence_score": "0.75",
    }
    payload.update(overrides)
    return payload


def test_detection_create():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_create(_payload())
    assert h._response_code == 201
    assert h._response_body["detection_id"].startswith("cfp_")


def test_detection_url_hashed():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_create(_payload())
    assert "url_hash" in h._response_body
    assert "url" not in h._response_body


def test_detection_invalid_technique():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_create(_payload(technique="unknown"))
    assert h._response_code == 400


def test_detection_confidence_out_of_range():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_create(_payload(confidence_score="1.5"))
    assert h._response_code == 400


def test_detection_blocked_flag():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_create(_payload(was_blocked=True))
    assert h._response_code == 201
    assert h._response_body["was_blocked"] is True


def test_detection_list():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_create(_payload())
    h._handle_canvas_fingerprint_detector_list()
    assert h._response_code == 200
    assert len(h._response_body["detections"]) == 1


def test_detection_delete():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_create(_payload())
    detection_id = h._response_body["detection_id"]
    h._handle_canvas_fingerprint_detector_delete(detection_id)
    assert h._response_code == 200
    with ys._FP_DETECTOR_LOCK:
        assert ys._FP_DETECTIONS == []


def test_detection_not_found():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_delete("cfp_notexist")
    assert h._response_code == 404


def test_fp_stats():
    h = FakeHandler()
    _reset()
    h._handle_canvas_fingerprint_detector_create(_payload(was_blocked=True, confidence_score="0.90"))
    h._handle_canvas_fingerprint_detector_create(_payload(technique="measureText", was_blocked=False, confidence_score="0.50"))
    h._handle_canvas_fingerprint_detector_stats()
    assert h._response_code == 200
    assert isinstance(Decimal(h._response_body["block_rate"]), Decimal)


def test_no_port_9222_in_canvas_fp():
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
