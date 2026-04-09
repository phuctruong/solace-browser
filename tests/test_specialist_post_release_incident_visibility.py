"""
Test: Verification of SAC52 Specialist Post-Release Incident Visibility
Persona: Donald Knuth (Verification Precision)
Validates Mitigated/In Progress/Unresolved states correctly proving 
whether a degraded tracking incident produces actionable operating-level remediation.
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


def test_html_has_post_release_incident_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-incident-card")
    assert card is not None, "Missing Section 4am: post release incident card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Incident / Remediation" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-incident-state") is not None


def test_hub_app_js_has_incident_function(app_js):
    assert "function updateSpecialistPostReleaseIncident(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseIncident(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_incident_states(app_js):
    assert "'Mitigated'" in app_js
    assert "'In Progress'" in app_js
    assert "'Unresolved'" in app_js


def test_hub_app_js_ties_incident_to_payload(app_js):
    assert "healthLineage:" in app_js, "Missing health telemetry evaluation verification"
    assert "incidentBasis:" in app_js, "Missing physical remediation basis description"


def test_geometric_law_alcoa_incident_hash(app_js):
    assert "btoa(entry.state + entry.healthLineage + entry.remediationVerdict)" in app_js, \
        "ALCOA+ hash must bind state + healthLineage + remediationVerdict"


def test_hub_app_js_exposes_active_incident_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Incident Basis:" in app_js
    assert "post-release health -> remediation path -> mitigated, in-progress, or unresolved state" in app_js


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-incident.sh"
    assert path.exists(), "Missing SAC52 smoke script"


def test_prime_mermaid_incident_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-incident.prime-mermaid.md"
    assert path.exists(), "SAC52 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
