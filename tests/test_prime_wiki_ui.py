import pathlib, sys, threading, time, urllib.request
import pytest
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
TEST_PORT = 18897  # UNIQUE — not used by any other test file

@pytest.fixture()
def wiki_server():
    import yinyang_server as ys
    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256='d'*64)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    for _ in range(30):
        try: urllib.request.urlopen(f"http://localhost:{TEST_PORT}/health", timeout=1); break
        except: time.sleep(0.1)
    yield httpd
    httpd.shutdown()

def test_prime_wiki_html_exists():
    assert (REPO_ROOT / "web/prime-wiki.html").exists()

def test_html_no_cdn():
    c = (REPO_ROOT / "web/prime-wiki.html").read_text()
    assert "cdn.jsdelivr.net" not in c and "unpkg.com" not in c

def test_html_no_jquery():
    c = (REPO_ROOT / "web/prime-wiki.html").read_text()
    assert "jQuery" not in c

def test_html_uses_hub_tokens():
    c = (REPO_ROOT / "web/prime-wiki.html").read_text()
    assert "var(--hub-" in c

def test_html_calls_stats_api():
    c = (REPO_ROOT / "web/prime-wiki.html").read_text()
    assert "/api/v1/prime-wiki/stats" in c

def test_html_calls_search_api():
    c = (REPO_ROOT / "web/prime-wiki.html").read_text()
    assert "/api/v1/prime-wiki/search" in c

def test_html_no_eval():
    c = (REPO_ROOT / "web/prime-wiki.html").read_text()
    assert "eval(" not in c

def test_html_has_stat_card():
    c = (REPO_ROOT / "web/prime-wiki.html").read_text()
    assert "stat-snapshots" in c

def test_html_has_search_input():
    c = (REPO_ROOT / "web/prime-wiki.html").read_text()
    assert "search-input" in c

def test_route_serves_html(wiki_server):
    resp = urllib.request.urlopen(f"http://localhost:{TEST_PORT}/web/prime-wiki.html", timeout=3)
    assert resp.status == 200
    assert "text/html" in resp.headers.get("Content-Type", "")
