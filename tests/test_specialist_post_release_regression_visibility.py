"""
Test: Verification of SAC59 Specialist Post-Release Regression Response Visibility
Persona: Donald Knuth (Verification Precision)
Validates Rollback Triggered/Live Mitigation/Containment Escalated states
proving the system strictly accounts for physical recovery regressions.
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


def test_html_has_post_release_regression_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-regression-card")
    assert card is not None, "Missing Section 4at: post release regression card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Regression Response" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-regression-state") is not None


def test_hub_app_js_has_regression_function(app_js):
    assert "function updateSpecialistPostReleaseRegression(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseRegression(appId, runId);" in app_js[hook_start:hook_start+3000]


def test_hub_app_js_honest_regression_states(app_js):
    assert "state: 'Rollback Triggered'" in app_js
    assert "state: 'Live Mitigation'" in app_js
    assert "state: 'Containment Escalated'" in app_js


def test_hub_app_js_ties_regression_to_payload(app_js):
    assert "regressionLineage:" in app_js, "Missing regression/relapse tracking context binding"
    assert "responseBasis:" in app_js, "Missing physical response rationale bound"


def test_geometric_law_alcoa_regression_hash(app_js):
    assert "btoa(entry.state + entry.regressionLineage + entry.responseVerdict)" in app_js, \
        "ALCOA+ hash must bind state + regressionLineage + responseVerdict"


def test_hub_app_js_exposes_active_response_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Response Basis:" in app_js
    assert "post-release sustained-service -> regression-response path -> rollback-triggered, live-mitigation, or containment-escalated state" in app_js


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-regression.sh"
    assert path.exists(), "Missing SAC59 smoke script"


def test_prime_mermaid_regression_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-regression.prime-mermaid.md"
    assert path.exists(), "SAC59 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
