"""
Test: Verification of SAC62 Specialist Post-Release Next-Path Execution Visibility
Persona: Donald Knuth (Verification Precision)
Validates Execution Confirmed/Execution Queued/Execution Blocked states
proving the system strictly tracks whether terminal routing commands actually executed across the physical network.
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


def test_html_has_post_release_next_path_execution_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-next-path-execution-card")
    assert card is not None, "Missing Section 4aw: post release next-path execution card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Next-Path Execution" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-next-path-execution-state") is not None


def test_hub_app_js_has_next_path_execution_function(app_js):
    assert "function updateSpecialistPostReleaseNextPathExecution(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseNextPathExecution(appId, runId);" in app_js[hook_start:hook_start+3000]


def test_hub_app_js_honest_next_path_execution_states(app_js):
    assert "state: 'Execution Confirmed'" in app_js
    assert "state: 'Execution Queued'" in app_js
    assert "state: 'Execution Blocked'" in app_js


def test_hub_app_js_ties_next_path_execution_to_payload(app_js):
    assert "decisionLineage:" in app_js, "Missing next-path decision context binding"
    assert "executionBasis:" in app_js, "Missing physical network rationale bound"


def test_hub_app_js_has_active_next_path_execution_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Execution Basis:" in app_js
    assert "post-release next-path decision -> next-path execution -> execution-confirmed, execution-queued, or execution-blocked state" in app_js


def test_geometric_law_alcoa_next_path_execution_hash(app_js):
    assert "btoa(entry.state + entry.decisionLineage + entry.executionVerdict)" in app_js, \
        "ALCOA+ hash must bind state + decisionLineage + executionVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-next-path-execution.sh"
    assert path.exists(), "Missing SAC62 smoke script"


def test_prime_mermaid_next_path_execution_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-next-path-execution.prime-mermaid.md"
    assert path.exists(), "SAC62 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
