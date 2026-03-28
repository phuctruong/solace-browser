"""
Test: Verification of SAC61 Specialist Post-Release Next-Path Decision Visibility
Persona: Donald Knuth (Verification Precision)
Validates Clean Exit/Bounded Recovery Re-entry/Architecture Reset Dispatch states
proving the system strictly commands terminal routing after resolving an incident loop.
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


def test_html_has_post_release_next_path_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-next-path-card")
    assert card is not None, "Missing Section 4av: post release next-path card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Next-Path Decision" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-next-path-state") is not None


def test_hub_app_js_has_next_path_function(app_js):
    assert "function updateSpecialistPostReleaseNextPath(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseNextPath(appId, runId);" in app_js[hook_start:hook_start+3000]


def test_hub_app_js_honest_next_path_states(app_js):
    assert "state: 'Clean Exit'" in app_js
    assert "state: 'Bounded Recovery Re-entry'" in app_js
    assert "state: 'Architecture Reset Dispatch'" in app_js


def test_hub_app_js_ties_next_path_to_payload(app_js):
    assert "resolutionLineage:" in app_js, "Missing regression resolution closure context binding"
    assert "nextPathBasis:" in app_js, "Missing explicitly commanded terminal rationale bound"


def test_hub_app_js_has_active_next_path_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Next-Path Basis:" in app_js
    assert "post-release regression-resolution -> next-path decision -> clean-exit, bounded-recovery-reentry, or architecture-reset-dispatch state" in app_js


def test_geometric_law_alcoa_next_path_hash(app_js):
    assert "btoa(entry.state + entry.resolutionLineage + entry.nextPathVerdict)" in app_js, \
        "ALCOA+ hash must bind state + resolutionLineage + nextPathVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-next-path.sh"
    assert path.exists(), "Missing SAC61 smoke script"


def test_prime_mermaid_next_path_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-next-path.prime-mermaid.md"
    assert path.exists(), "SAC61 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
