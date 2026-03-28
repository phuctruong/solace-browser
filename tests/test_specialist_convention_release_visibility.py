"""
Test: Verification of SAC49 Specialist Convention-Release Visibility
Persona: Donald Knuth (Verification Precision)
Validates Approved/Pending/Denied states correctly proving 
whether the Dev Manager physically signed off on the verified artifact release.
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


def test_html_has_convention_release_card(html_soup):
    card = html_soup.find(id="dev-specialist-convention-release-card")
    assert card is not None, "Missing Section 4aj: convention release card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Convention Release / Manager Signoff" in kicker.text
    assert html_soup.find(id="dev-specialist-convention-release-state") is not None


def test_hub_app_js_has_release_function(app_js):
    assert "function updateSpecialistConventionRelease(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistConventionRelease(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_release_states(app_js):
    assert "state: 'Approved'" in app_js
    assert "state: 'Pending'" in app_js
    assert "state: 'Denied'" in app_js


def test_hub_app_js_ties_release_to_payload(app_js):
    assert "trustLineage:" in app_js, "Missing trust lineage verification"
    assert "signoffBasis:" in app_js, "Missing human manager signoff description"


def test_hub_app_js_has_active_release_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Action Basis:" in app_js
    assert "trust verdict -> manager signoff -> release or promotion action" in app_js


def test_geometric_law_alcoa_release_hash(app_js):
    assert "btoa(entry.state + entry.trustLineage + entry.actionVerdict)" in app_js, \
        "ALCOA+ hash must bind state + trustLineage + actionVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-convention-release.sh"
    assert path.exists(), "Missing SAC49 smoke script"


def test_prime_mermaid_release_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-convention-release.prime-mermaid.md"
    assert path.exists(), "SAC49 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
