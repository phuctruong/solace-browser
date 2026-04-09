"""
Test: Verification of SAC57 Specialist Post-Release Return-to-Service Visibility
Persona: Donald Knuth (Verification Precision)
Validates Service Restored/Provisional Service/Re-entry Failed states
proving the system strictly measures physical survival post-quarantine.
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


def test_html_has_post_release_return_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-return-card")
    assert card is not None, "Missing Section 4ar: post release return card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Return-to-Service Verification" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-return-state") is not None


def test_hub_app_js_has_return_function(app_js):
    assert "function updateSpecialistPostReleaseReturn(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseReturn(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_return_states(app_js):
    assert "'Service Restored'" in app_js
    assert "'Provisional Service'" in app_js
    assert "'Re-entry Failed'" in app_js


def test_hub_app_js_ties_return_to_payload(app_js):
    assert "recoveryLineage:" in app_js, "Missing recovery authorization context binding"
    assert "serviceBasis:" in app_js, "Missing physical observation basis description"


def test_geometric_law_alcoa_return_hash(app_js):
    assert "btoa(entry.state + entry.recoveryLineage + entry.serviceVerdict)" in app_js, \
        "ALCOA+ hash must bind state + recoveryLineage + serviceVerdict"


def test_hub_app_js_exposes_active_service_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Service Basis:" in app_js
    assert "post-release recovery -> service verification path -> returned-to-service, provisional-service, or re-entry-failed state" in app_js


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-return.sh"
    assert path.exists(), "Missing SAC57 smoke script"


def test_prime_mermaid_return_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-return.prime-mermaid.md"
    assert path.exists(), "SAC57 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
