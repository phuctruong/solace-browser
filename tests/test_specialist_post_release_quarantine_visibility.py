"""
Test: Verification of SAC55 Specialist Post-Release Quarantine Visibility
Persona: Donald Knuth (Verification Precision)
Validates Quarantined/Manual Override Required/Constrained Continuation states
proving the system exerts physical operational control over severe escalations.
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


def test_html_has_post_release_quarantine_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-quarantine-card")
    assert card is not None, "Missing Section 4ap: post release quarantine card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Quarantine / Override" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-quarantine-state") is not None


def test_hub_app_js_has_quarantine_function(app_js):
    assert "function updateSpecialistPostReleaseQuarantine(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseQuarantine(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_quarantine_states(app_js):
    assert "state: 'Constrained Continuation'" in app_js
    assert "state: 'Manual Override Required'" in app_js
    assert "state: 'Quarantined'" in app_js


def test_hub_app_js_ties_quarantine_to_payload(app_js):
    assert "escalationLineage:" in app_js, "Missing escalation context binding"
    assert "controlBasis:" in app_js, "Missing physical control basis description"


def test_geometric_law_alcoa_quarantine_hash(app_js):
    assert "btoa(entry.state + entry.escalationLineage + entry.controlVerdict)" in app_js, \
        "ALCOA+ hash must bind state + escalationLineage + controlVerdict"


def test_hub_app_js_exposes_active_control_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Control Basis:" in app_js
    assert "post-release escalation -> control path -> quarantined, manual-override-required, or constrained-continuation state" in app_js


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-quarantine.sh"
    assert path.exists(), "Missing SAC55 smoke script"


def test_prime_mermaid_quarantine_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-quarantine.prime-mermaid.md"
    assert path.exists(), "SAC55 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
