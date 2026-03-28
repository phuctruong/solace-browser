"""
Test: Verification of SAC60 Specialist Post-Release Regression Resolution Visibility
Persona: Donald Knuth (Verification Precision)
Validates Resolved After Mitigation/Staged Recovery Reopened/Architecture Reset Required states
proving the system strictly accounts for the closure of physical mitigation loops.
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


def test_html_has_post_release_regression_resolution_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-regression-resolution-card")
    assert card is not None, "Missing Section 4au: post release regression resolution card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Regression Resolution" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-regression-resolution-state") is not None


def test_hub_app_js_has_regression_resolution_function(app_js):
    assert "function updateSpecialistPostReleaseRegressionResolution(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseRegressionResolution(appId, runId);" in app_js[hook_start:hook_start+3000]


def test_hub_app_js_honest_regression_resolution_states(app_js):
    assert "state: 'Resolved After Mitigation'" in app_js
    assert "state: 'Staged Recovery Reopened'" in app_js
    assert "state: 'Architecture Reset Required'" in app_js


def test_hub_app_js_ties_regression_resolution_to_payload(app_js):
    assert "responseLineage:" in app_js, "Missing physical response context binding"
    assert "resolutionBasis:" in app_js, "Missing closure rationale bound"


def test_hub_app_js_has_active_regression_resolution_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Resolution Basis:" in app_js
    assert "post-release regression-response -> regression-resolution path -> resolved-after-mitigation, staged-recovery-reopened, or architecture-reset-required state" in app_js


def test_geometric_law_alcoa_regression_resolution_hash(app_js):
    assert "btoa(entry.state + entry.responseLineage + entry.resolutionVerdict)" in app_js, \
        "ALCOA+ hash must bind state + responseLineage + resolutionVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-regression-resolution.sh"
    assert path.exists(), "Missing SAC60 smoke script"


def test_prime_mermaid_regression_resolution_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-regression-resolution.prime-mermaid.md"
    assert path.exists(), "SAC60 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
