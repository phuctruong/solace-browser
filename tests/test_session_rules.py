"""RED → GREEN proofs for session rules and keep-alive endpoints."""

import json
import pathlib
import shutil
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_PORT = 18888
VALID_TOKEN = "a" * 64
BUILTIN_APPS = [
    "gmail",
    "whatsapp-web",
    "slack-web",
    "telegram-web",
    "linkedin-web",
]


def _copy_session_rule(app_id: str, destination_root: pathlib.Path) -> None:
    source = REPO_ROOT / "data" / "default" / "apps" / app_id / "session-rules.yaml"
    destination = destination_root / app_id / "session-rules.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


@pytest.fixture(scope="module")
def session_rules_env(tmp_path_factory):
    temp_root = tmp_path_factory.mktemp("session-rules")
    apps_root = temp_root / "data" / "default" / "apps"
    evidence_path = temp_root / "evidence.jsonl"

    for app_id in BUILTIN_APPS:
        _copy_session_rule(app_id, apps_root)

    original_apps_dir = ys.SESSION_RULES_APPS_DIR
    original_evidence = ys.EVIDENCE_PATH
    original_rules = list(ys._SESSION_RULES)
    original_status = dict(ys._SESSION_STATUS)

    ys.SESSION_RULES_APPS_DIR = apps_root
    ys.EVIDENCE_PATH = evidence_path
    ys._SESSION_RULES = []
    ys._SESSION_STATUS = {}
    ys.load_session_rules()

    yield {
        "apps_root": apps_root,
        "evidence_path": evidence_path,
    }

    ys.SESSION_RULES_APPS_DIR = original_apps_dir
    ys.EVIDENCE_PATH = original_evidence
    ys._SESSION_RULES = original_rules
    ys._SESSION_STATUS = original_status


def _make_handler(path: str, method: str, auth_header: str | None = None):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    headers: dict[str, str] = {}
    if auth_header is not None:
        headers["Authorization"] = auth_header
    handler.headers = headers
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", TEST_PORT)
    handler.server = type("DummyServer", (), {"session_token_sha256": VALID_TOKEN})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    return handler, captured


def test_load_session_rules_finds_gmail(session_rules_env):
    rules = ys.load_session_rules()
    gmail_rule = next(rule for rule in rules if rule["app"] == "gmail")
    assert gmail_rule["display_name"] == "Gmail"
    assert gmail_rule["check_url"] == "https://mail.google.com/mail/u/0/#inbox"


def test_load_session_rules_finds_all_5(session_rules_env):
    rules = ys.load_session_rules()
    assert len(rules) == 5
    assert {rule["app"] for rule in rules} == set(BUILTIN_APPS)


def test_get_session_rules_requires_auth(session_rules_env):
    handler, captured = _make_handler("/api/v1/session-rules", "GET")
    handler._handle_session_rules_list()
    assert captured["status"] == 401
    assert captured["data"]["error"] == "unauthorized"


def test_get_session_rules_returns_all(session_rules_env):
    handler, captured = _make_handler(
        "/api/v1/session-rules",
        "GET",
        auth_header=f"Bearer {VALID_TOKEN}",
    )
    handler._handle_session_rules_list()
    assert captured["status"] == 200
    assert captured["data"]["total"] == 5
    assert {rule["app"] for rule in captured["data"]["rules"]} == set(BUILTIN_APPS)


def test_check_app_returns_status(session_rules_env):
    handler, captured = _make_handler(
        "/api/v1/session-rules/check/gmail",
        "POST",
        auth_header=f"Bearer {VALID_TOKEN}",
    )
    handler._handle_session_rule_check("gmail")
    assert captured["status"] == 200
    assert captured["data"]["app"] == "gmail"
    assert captured["data"]["status"] == "unknown"
    assert isinstance(captured["data"]["checked_at"], int)


def test_session_status_endpoint(session_rules_env):
    handler, captured = _make_handler(
        "/api/v1/session-rules/status",
        "GET",
        auth_header=f"Bearer {VALID_TOKEN}",
    )
    handler._handle_session_rules_status()
    assert captured["status"] == 200
    assert {entry["app"] for entry in captured["data"]["statuses"]} == set(BUILTIN_APPS)


def test_session_check_records_evidence(session_rules_env):
    evidence_path = ys.EVIDENCE_PATH
    before_lines = evidence_path.read_text().splitlines() if evidence_path.exists() else []
    handler, captured = _make_handler(
        "/api/v1/session-rules/check/gmail",
        "POST",
        auth_header=f"Bearer {VALID_TOKEN}",
    )
    handler._handle_session_rule_check("gmail")
    assert captured["status"] == 200
    after_lines = evidence_path.read_text().splitlines()
    assert len(after_lines) == len(before_lines) + 1
    evidence_record = json.loads(after_lines[-1])
    assert evidence_record["type"] == "session_check"
    assert evidence_record["data"]["app"] == "gmail"
    assert evidence_record["data"]["status"] == captured["data"]["status"]
