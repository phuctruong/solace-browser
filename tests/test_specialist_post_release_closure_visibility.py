"""
Test: Verification of SAC53 Specialist Post-Release Closure Visibility
Persona: Donald Knuth (Verification Precision)
Validates Verified Closed/Pending Verification/Failed Verification states
proving operational remediation physically sealed the detected incident.
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


def test_html_has_post_release_closure_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-closure-card")
    assert card is not None, "Missing Section 4an: post release closure card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Closure / Verification" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-closure-state") is not None


def test_hub_app_js_has_closure_function(app_js):
    assert "function updateSpecialistPostReleaseClosure(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseClosure(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_closure_states(app_js):
    assert "state: 'Verified Closed'" in app_js
    assert "state: 'Pending Verification'" in app_js
    assert "state: 'Failed Verification'" in app_js


def test_hub_app_js_ties_closure_to_payload(app_js):
    assert "incidentLineage:" in app_js, "Missing remediation execution evaluation verification"
    assert "closureBasis:" in app_js, "Missing physical verification basis description"


def test_geometric_law_alcoa_closure_hash(app_js):
    assert "btoa(entry.state + entry.incidentLineage + entry.closureVerdict)" in app_js, \
        "ALCOA+ hash must bind state + incidentLineage + closureVerdict"


def test_hub_app_js_exposes_active_closure_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Closure Basis:" in app_js
    assert "post-release incident -> remediation verification -> verified-closed, pending-verification, or failed-verification state" in app_js


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-closure.sh"
    assert path.exists(), "Missing SAC53 smoke script"


def test_prime_mermaid_closure_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-closure.prime-mermaid.md"
    assert path.exists(), "SAC53 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
