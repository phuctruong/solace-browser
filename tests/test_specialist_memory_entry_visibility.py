"""
Test: Verification of SAC41 Specialist Memory-Entry Visibility
Persona: Donald Knuth (Verification Precision)
Validates Draft/Live/Revoked states representing concrete reusable 
department-memory objects and conventions.
"""
import pytest
from bs4 import BeautifulSoup
from pathlib import Path

HUB_DIR = Path(__file__).parent.parent / "solace-hub"
INDEX_HTML = HUB_DIR / "src" / "index.html"
APP_JS = HUB_DIR / "src" / "hub-app.js"

@pytest.fixture
def html_soup():
    assert INDEX_HTML.exists()
    return BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")

@pytest.fixture
def app_js():
    assert APP_JS.exists()
    return APP_JS.read_text(encoding="utf-8")


def test_html_has_memory_entry_card(html_soup):
    card = html_soup.find(id="dev-specialist-memory-entry-card")
    assert card is not None, "Missing Section 4ab: memory entry card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Memory Entry" in kicker.text
    assert html_soup.find(id="dev-specialist-memory-entry-state") is not None


def test_hub_app_js_has_entry_function(app_js):
    assert "function updateSpecialistMemoryEntry(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistMemoryEntry(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_entry_states(app_js):
    assert "state: 'Live'" in app_js
    assert "state: 'Draft'" in app_js
    assert "state: 'Revoked'" in app_js


def test_hub_app_js_ties_entry_to_payload(app_js):
    assert "conventionTarget:" in app_js, "Missing convention target path"
    assert "objectDesc:" in app_js, "Missing memory object description"


def test_hub_app_js_has_active_memory_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Memory Basis:" in app_js
    assert "visible specialist output -> memory admission -> department convention entry" in app_js


def test_geometric_law_alcoa_entry_hash(app_js):
    assert "btoa(entry.state + entry.bundleId + entry.conventionTarget)" in app_js, \
        "ALCOA+ hash must bind state + bundleId + conventionTarget"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-memory-entry.sh"
    assert path.exists(), "Missing SAC41 smoke script"


def test_prime_mermaid_entry_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-memory-entry.prime-mermaid.md"
    assert path.exists(), "SAC41 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
