import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_js_file_exists():
    assert (REPO_ROOT / "web/js/yinyang-delight.js").exists()


def test_css_file_exists():
    assert (REPO_ROOT / "web/css/delight.css").exists()


def test_js_no_cdn():
    content = (REPO_ROOT / "web/js/yinyang-delight.js").read_text()
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content
    assert "cdnjs" not in content


def test_js_no_jquery():
    content = (REPO_ROOT / "web/js/yinyang-delight.js").read_text()
    assert "jQuery" not in content
    assert "$(" not in content


def test_js_exports_trigger_delight():
    content = (REPO_ROOT / "web/js/yinyang-delight.js").read_text()
    assert "SolaceDelight" in content
    assert "triggerDelight" in content


def test_js_handles_celebration_type():
    content = (REPO_ROOT / "web/js/yinyang-delight.js").read_text()
    assert "celebration" in content


def test_js_handles_milestone_type():
    content = (REPO_ROOT / "web/js/yinyang-delight.js").read_text()
    assert "milestone_100_runs" in content or "milestone" in content


def test_js_no_eval():
    content = (REPO_ROOT / "web/js/yinyang-delight.js").read_text()
    assert "eval(" not in content


def test_js_uses_canvas_api():
    content = (REPO_ROOT / "web/js/yinyang-delight.js").read_text()
    assert "getContext" in content


def test_js_under_10kb():
    size = (REPO_ROOT / "web/js/yinyang-delight.js").stat().st_size
    assert size < 10240, f"File too large: {size} bytes (limit: 10240)"


def test_css_uses_hub_tokens():
    content = (REPO_ROOT / "web/css/delight.css").read_text()
    assert "var(--hub-" in content


def test_css_hex_only_in_root():
    content = (REPO_ROOT / "web/css/delight.css").read_text()
    lines = content.split("\n")
    in_root = False
    for line in lines:
        if ":root" in line:
            in_root = True
        if in_root and "}" in line and ":root" not in line:
            in_root = False
        if not in_root and re.search(r'#[0-9a-fA-F]{3,6}', line):
            assert False, f"Hardcoded hex outside :root: {line.strip()}"
