"""
Test: Verification of SAC42 Specialist Memory-Reuse Visibility
Persona: Donald Knuth (Verification Precision)
Validates Callable/Limited/Blocked states correctly binding 
department memory back into actionable next-packet constraints.
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


def test_html_has_memory_reuse_card(html_soup):
    card = html_soup.find(id="dev-specialist-memory-reuse-card")
    assert card is not None, "Missing Section 4ac: memory reuse card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Memory Reuse" in kicker.text
    assert html_soup.find(id="dev-specialist-memory-reuse-state") is not None


def test_hub_app_js_has_reuse_function(app_js):
    assert "function updateSpecialistMemoryReuse(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistMemoryReuse(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_reuse_states(app_js):
    assert "state: 'Callable'" in app_js
    assert "state: 'Limited'" in app_js
    assert "state: 'Blocked'" in app_js


def test_hub_app_js_ties_reuse_to_payload(app_js):
    assert "nextTarget:" in app_js, "Missing next directive target"
    assert "reuseBasis:" in app_js, "Missing reuse basis description"


def test_hub_app_js_has_active_reuse_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Reuse Basis:" in app_js
    assert "visible department-memory entry -> callable convention -> next directive or worker packet" in app_js


def test_geometric_law_alcoa_reuse_hash(app_js):
    assert "btoa(entry.state + entry.memoryId + entry.nextTarget)" in app_js, \
        "ALCOA+ hash must bind state + memoryId + nextTarget"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-memory-reuse.sh"
    assert path.exists(), "Missing SAC42 smoke script"


def test_prime_mermaid_reuse_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-memory-reuse.prime-mermaid.md"
    assert path.exists(), "SAC42 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
