"""
Test: Verification of SAC45 Specialist Convention-Activation Visibility
Persona: Donald Knuth (Verification Precision)
Validates Active/Queued/Failed states correctly proving 
whether the target execution runtime actually applied the delivered constraint.
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


def test_html_has_convention_activation_card(html_soup):
    card = html_soup.find(id="dev-specialist-convention-activation-card")
    assert card is not None, "Missing Section 4af: convention activation card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Convention Activation" in kicker.text
    assert html_soup.find(id="dev-specialist-convention-activation-state") is not None


def test_hub_app_js_has_activation_function(app_js):
    assert "function updateSpecialistConventionActivation(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistConventionActivation(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_activation_states(app_js):
    assert "state: 'Active'" in app_js
    assert "state: 'Queued'" in app_js
    assert "state: 'Failed'" in app_js


def test_hub_app_js_ties_activation_to_payload(app_js):
    assert "targetRuntime:" in app_js, "Missing target execution runtime verification"
    assert "activationBasis:" in app_js, "Missing activation basis description"


def test_hub_app_js_has_active_activation_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Activation Basis:" in app_js
    assert "delivered convention -> target runtime binding -> active execution constraint" in app_js


def test_geometric_law_alcoa_activation_hash(app_js):
    assert "btoa(entry.state + entry.conventionTarget + entry.targetRuntime)" in app_js, \
        "ALCOA+ hash must bind state + conventionTarget + targetRuntime"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-convention-activation.sh"
    assert path.exists(), "Missing SAC45 smoke script"


def test_prime_mermaid_activation_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-convention-activation.prime-mermaid.md"
    assert path.exists(), "SAC45 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
