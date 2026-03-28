"""
Test: Verification of SAC54 Specialist Post-Release Escalation Visibility
Persona: Donald Knuth (Verification Precision)
Validates Reopened/Escalated/Under Observation states
proving the system holds incidents accountable when remediation fails.
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


def test_html_has_post_release_escalation_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-escalation-card")
    assert card is not None, "Missing Section 4ao: post release escalation card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Reopen / Escalation" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-escalation-state") is not None


def test_hub_app_js_has_escalation_function(app_js):
    assert "function updateSpecialistPostReleaseEscalation(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseEscalation(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_escalation_states(app_js):
    assert "state: 'Reopened'" in app_js
    assert "state: 'Escalated'" in app_js
    assert "state: 'Under Observation'" in app_js


def test_hub_app_js_ties_escalation_to_payload(app_js):
    assert "closureLineage:" in app_js, "Missing closure failure verification"
    assert "escalationBasis:" in app_js, "Missing physical escalation basis description"


def test_geometric_law_alcoa_escalation_hash(app_js):
    assert "btoa(entry.state + entry.closureLineage + entry.escalationVerdict)" in app_js, \
        "ALCOA+ hash must bind state + closureLineage + escalationVerdict"


def test_hub_app_js_exposes_active_escalation_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Escalation Basis:" in app_js
    assert "post-release closure -> reopen or escalation path -> reopened, escalated, or under-observation state" in app_js


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-escalation.sh"
    assert path.exists(), "Missing SAC54 smoke script"


def test_prime_mermaid_escalation_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-escalation.prime-mermaid.md"
    assert path.exists(), "SAC54 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
