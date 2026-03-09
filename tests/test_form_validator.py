"""Tests for Task 096 — Form Validator."""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.path = ""
        self.headers = {"content-length": "0", "Authorization": f"Bearer {VALID_TOKEN}"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass

    def send_response(self, code):
        self._responses.append((code, {}))

    def end_headers(self):
        pass


def make_handler(body=None, path=""):
    h = FakeHandler()
    h.path = path
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._FORM_VALIDATOR_LOCK:
        ys._FORM_RULE_SETS.clear()


def test_rule_create():
    name_hash = hashlib.sha256(b"login-rules").hexdigest()
    form_hash = hashlib.sha256(b"login-form").hexdigest()
    fields = [
        {"field_name_hash": hashlib.sha256(b"email").hexdigest(), "validation_type": "required", "params_hash": ""},
        {"field_name_hash": hashlib.sha256(b"password").hexdigest(), "validation_type": "min_length", "params_hash": ""},
    ]
    h = make_handler({"name_hash": name_hash, "form_hash": form_hash, "fields": fields})
    h._handle_form_rule_create()
    assert len(h._responses) == 1
    code, data = h._responses[0]
    assert code == 201
    assert data["rule"]["rule_id"].startswith("fvr_")
    assert len(data["rule"]["fields"]) == 2


def test_rule_invalid_validation_type():
    name_hash = hashlib.sha256(b"rules").hexdigest()
    form_hash = hashlib.sha256(b"form").hexdigest()
    fields = [{"field_name_hash": "abc", "validation_type": "fancy_type", "params_hash": ""}]
    h = make_handler({"name_hash": name_hash, "form_hash": form_hash, "fields": fields})
    h._handle_form_rule_create()
    code, data = h._responses[0]
    assert code == 400
    assert "validation_type" in data["error"]


def test_rule_too_many_fields():
    name_hash = hashlib.sha256(b"many-rules").hexdigest()
    form_hash = hashlib.sha256(b"many-form").hexdigest()
    fields = [
        {"field_name_hash": f"field{i}", "validation_type": "required", "params_hash": ""}
        for i in range(51)
    ]
    h = make_handler({"name_hash": name_hash, "form_hash": form_hash, "fields": fields})
    h._handle_form_rule_create()
    code, data = h._responses[0]
    assert code == 400
    assert "50" in data["error"]


def test_rule_list():
    name_hash = hashlib.sha256(b"list-rules").hexdigest()
    form_hash = hashlib.sha256(b"list-form").hexdigest()
    h = make_handler({"name_hash": name_hash, "form_hash": form_hash, "fields": []})
    h._handle_form_rule_create()

    h2 = FakeHandler()
    h2._handle_form_rule_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["rules"], list)
    assert data["total"] >= 1


def test_rule_delete():
    name_hash = hashlib.sha256(b"del-rules").hexdigest()
    form_hash = hashlib.sha256(b"del-form").hexdigest()
    h = make_handler({"name_hash": name_hash, "form_hash": form_hash, "fields": []})
    h._handle_form_rule_create()
    rule_id = h._responses[0][1]["rule"]["rule_id"]

    h2 = make_handler()
    h2._handle_form_rule_delete(rule_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["rule_id"] == rule_id

    with ys._FORM_VALIDATOR_LOCK:
        ids = [r["rule_id"] for r in ys._FORM_RULE_SETS]
    assert rule_id not in ids


def test_rule_not_found():
    h = make_handler()
    h._handle_form_rule_delete("fvr_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_validate():
    name_hash = hashlib.sha256(b"val-rules").hexdigest()
    form_hash = hashlib.sha256(b"val-form").hexdigest()
    fields = [{"field_name_hash": "f1", "validation_type": "required", "params_hash": ""}]
    h = make_handler({"name_hash": name_hash, "form_hash": form_hash, "fields": fields})
    h._handle_form_rule_create()
    rule_id = h._responses[0][1]["rule"]["rule_id"]

    sub_hash = hashlib.sha256(b"form data").hexdigest()
    h2 = make_handler({
        "rule_id": rule_id,
        "submission_hash": sub_hash,
        "field_results": {"f1": True},
    })
    h2._handle_form_validate()
    code, data = h2._responses[0]
    assert code == 200
    assert "valid" in data
    assert "passed_count" in data
    assert "failed_count" in data
    assert "validated_at" in data


def test_validate_invalid_rule():
    sub_hash = hashlib.sha256(b"data").hexdigest()
    h = make_handler({
        "rule_id": "fvr_notexist",
        "submission_hash": sub_hash,
        "field_results": {},
    })
    h._handle_form_validate()
    code, data = h._responses[0]
    assert code == 404


def test_types_list():
    h = FakeHandler()
    h._handle_form_validator_types()
    code, data = h._responses[0]
    assert code == 200
    assert len(data["types"]) == 11
    assert "required" in data["types"]
    assert "email_format" in data["types"]
    assert "enum_values" in data["types"]


def test_no_port_9222_in_validator():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
