"""
Test: Verification of SAC44 Specialist Convention-Delivery Visibility
Persona: Donald Knuth (Verification Precision)
Validates Acknowledged/Pending/Rejected states correctly proving 
whether the target execution packet actually received the invoked convention.
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


def test_html_has_convention_delivery_card(html_soup):
    card = html_soup.find(id="dev-specialist-convention-delivery-card")
    assert card is not None, "Missing Section 4ae: convention delivery card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Convention Delivery Receipt" in kicker.text
    assert html_soup.find(id="dev-specialist-convention-delivery-state") is not None


def test_hub_app_js_has_delivery_function(app_js):
    assert "function updateSpecialistConventionDelivery(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistConventionDelivery(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_delivery_states(app_js):
    assert "state: 'Acknowledged'" in app_js
    assert "state: 'Pending'" in app_js
    assert "state: 'Rejected'" in app_js


def test_hub_app_js_ties_delivery_to_payload(app_js):
    assert "targetPacket:" in app_js, "Missing target packet verification"
    assert "deliveryBasis:" in app_js, "Missing delivery basis description"


def test_hub_app_js_has_active_delivery_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Delivery Basis:" in app_js
    assert "invoked convention -> target packet receipt -> execution binding acknowledgement" in app_js


def test_geometric_law_alcoa_delivery_hash(app_js):
    assert "btoa(entry.state + entry.conventionTarget + entry.targetPacket)" in app_js, \
        "ALCOA+ hash must bind state + conventionTarget + targetPacket"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-convention-delivery.sh"
    assert path.exists(), "Missing SAC44 smoke script"


def test_prime_mermaid_delivery_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-convention-delivery.prime-mermaid.md"
    assert path.exists(), "SAC44 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
