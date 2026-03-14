# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 155 — Network Speed Monitor
Browser: yinyang_server.py routes /api/v1/network-speed/*
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


def test_measurement_create():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    h = _make_handler({
        "connection_type": "wifi",
        "download_mbps": "100.5",
        "upload_mbps": "50.0",
        "latency_ms": 12,
        "jitter_ms": 3,
        "packet_loss_pct": "0.5",
    })
    h._handle_nsm_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["measurement"]["measurement_id"].startswith("nsm_")
    assert data["measurement"]["connection_type"] == "wifi"
    assert data["measurement"]["download_mbps"] == "100.5"


def test_measurement_invalid_connection():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    h = _make_handler({
        "connection_type": "lte",
        "download_mbps": "50",
        "upload_mbps": "20",
        "latency_ms": 10,
        "jitter_ms": 2,
        "packet_loss_pct": "0",
    })
    h._handle_nsm_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_measurement_negative_download():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    h = _make_handler({
        "connection_type": "wifi",
        "download_mbps": "-1",
        "upload_mbps": "10",
        "latency_ms": 5,
        "jitter_ms": 1,
        "packet_loss_pct": "0",
    })
    h._handle_nsm_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_measurement_negative_latency():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    h = _make_handler({
        "connection_type": "ethernet",
        "download_mbps": "100",
        "upload_mbps": "100",
        "latency_ms": -1,
        "jitter_ms": 0,
        "packet_loss_pct": "0",
    })
    h._handle_nsm_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_measurement_invalid_packet_loss():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    h = _make_handler({
        "connection_type": "4g",
        "download_mbps": "30",
        "upload_mbps": "10",
        "latency_ms": 50,
        "jitter_ms": 5,
        "packet_loss_pct": "101",
    })
    h._handle_nsm_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_measurement_list():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    # Create one
    h1 = _make_handler({
        "connection_type": "5g",
        "download_mbps": "500",
        "upload_mbps": "100",
        "latency_ms": 5,
        "jitter_ms": 1,
        "packet_loss_pct": "0",
    })
    h1._handle_nsm_create()
    # List
    h2 = _make_handler()
    h2._handle_nsm_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["measurements"], list)


def test_measurement_delete():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    h1 = _make_handler({
        "connection_type": "wifi",
        "download_mbps": "200",
        "upload_mbps": "80",
        "latency_ms": 10,
        "jitter_ms": 2,
        "packet_loss_pct": "0.1",
    })
    h1._handle_nsm_create()
    measurement_id = h1._responses[0][1]["measurement"]["measurement_id"]
    h2 = _make_handler()
    h2._handle_nsm_delete(measurement_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    # Verify it's gone
    h3 = _make_handler()
    h3._handle_nsm_list()
    _, list_data = h3._responses[0]
    assert list_data["total"] == 0


def test_measurement_not_found():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    h = _make_handler()
    h._handle_nsm_delete("nsm_notexist")
    status, data = h._responses[0]
    assert status == 404
    assert "error" in data


def test_speed_stats():
    import yinyang_server as ys
    ys._SPEED_MEASUREMENTS.clear()
    # Add a couple measurements
    h1 = _make_handler({
        "connection_type": "wifi",
        "download_mbps": "100",
        "upload_mbps": "50",
        "latency_ms": 10,
        "jitter_ms": 2,
        "packet_loss_pct": "0",
    })
    h1._handle_nsm_create()
    h2 = _make_handler({
        "connection_type": "ethernet",
        "download_mbps": "200",
        "upload_mbps": "100",
        "latency_ms": 5,
        "jitter_ms": 1,
        "packet_loss_pct": "0",
    })
    h2._handle_nsm_create()
    h_stats = _make_handler()
    h_stats._handle_nsm_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert data["total_measurements"] == 2
    # avg_download_mbps must be a Decimal string
    avg_dl = data["avg_download_mbps"]
    assert isinstance(avg_dl, str)
    float(avg_dl)
    assert float(avg_dl) == 150.0
    assert "by_connection_type" in data


def test_no_port_9222_in_speed_monitor():
    import re
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0, f"Found port 9222 at positions: {matches}"
