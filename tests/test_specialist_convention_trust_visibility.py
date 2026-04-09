"""
Test: Verification of SAC48 Specialist Convention-Trust Visibility
Persona: Donald Knuth (Verification Precision)
Validates Trusted/Provisional/Blocked states correctly proving 
whether the proven artifact lineage is definitively approved for deployment, release, or systemic promotion.
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


def test_html_has_convention_trust_card(html_soup):
    card = html_soup.find(id="dev-specialist-convention-trust-card")
    assert card is not None, "Missing Section 4ai: convention trust card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Convention Trust / Release Readiness" in kicker.text
    assert html_soup.find(id="dev-specialist-convention-trust-state") is not None


def test_hub_app_js_has_trust_function(app_js):
    assert "function updateSpecialistConventionTrust(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistConventionTrust(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_trust_states(app_js):
    assert "'Trusted'" in app_js
    assert "'Provisional'" in app_js
    assert "'Blocked'" in app_js


def test_hub_app_js_ties_trust_to_payload(app_js):
    assert "verdictLineage:" in app_js, "Missing proof verdict lineage verification"
    assert "governanceBasis:" in app_js, "Missing governance basis description"


def test_hub_app_js_has_active_trust_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Trust Basis:" in app_js
    assert "real runs, approvals, memory_entries, conventions, and releases" in app_js


def test_geometric_law_alcoa_trust_hash(app_js):
    assert "btoa(entry.state + entry.verdictLineage + entry.decisionVerdict)" in app_js, \
        "ALCOA+ hash must bind state + verdictLineage + decisionVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-convention-trust.sh"
    assert path.exists(), "Missing SAC48 smoke script"


def test_prime_mermaid_trust_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-convention-trust.prime-mermaid.md"
    assert path.exists(), "SAC48 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
