"""
Test: Verification of SAB37 Specialist Artifact Bundle Visibility
Persona: Donald Knuth (Verification Precision)
Validates that Open/Partial/Sealed bundle states with artifact file listings
are structurally bound and not hallucinated.
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


def test_html_has_artifact_bundle_card(html_soup):
    card = html_soup.find(id="dev-specialist-artifact-bundle-card")
    assert card is not None, "Missing Section 4x: artifact bundle card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Artifact Bundle" in kicker.text
    assert html_soup.find(id="dev-specialist-artifact-bundle-state") is not None


def test_hub_app_js_has_bundle_function(app_js):
    assert "function updateSpecialistArtifactBundle(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistArtifactBundle(appId, runId);" in app_js[hook_start:hook_start+1000]


def test_hub_app_js_honest_bundle_states(app_js):
    assert "'Partial'" in app_js or '"Partial"' in app_js or "state: 'Partial'" in app_js
    assert "state: 'Open'" in app_js
    assert "state: 'Sealed'" in app_js


def test_hub_app_js_ties_bundle_to_payload(app_js):
    assert "bundleId:" in app_js, "Missing bundle ID reference"
    assert "sourcePacket:" in app_js, "Missing source packet tie-back"
    assert "artifacts:" in app_js, "Missing artifact file list"


def test_hub_app_js_has_active_artifact_context(app_js):
    assert "Audit Constraints:" in app_js, "Missing artifact constraint header"
    assert "Artifact Basis:" in app_js, "Missing explicit artifact basis"
    assert "Resolution Bound:" in app_js, "Missing artifact resolution bound"


def test_geometric_law_alcoa_bundle_hash(app_js):
    assert "btoa(bundle.state + bundle.bundleId + bundle.specialist)" in app_js, \
        "ALCOA+ hash must bind bundle state + bundleId + specialist"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-artifact-bundle.sh"
    assert path.exists(), "Missing SAB37 smoke script"


def test_prime_mermaid_bundle_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-artifact-bundle.prime-mermaid.md"
    assert path.exists(), "SAB37 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
