"""
Test: Verification of SAC58 Specialist Post-Release Sustained-Service Visibility
Persona: Donald Knuth (Verification Precision)
Validates Stable Service/Regression Watch/Relapse Detected states
proving the system strictly measures an extended baseline of survival post-recovery.
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


def test_html_has_post_release_sustained_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-sustained-card")
    assert card is not None, "Missing Section 4as: post release sustained service card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Sustained Service Validation" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-sustained-state") is not None


def test_hub_app_js_has_sustained_function(app_js):
    assert "function updateSpecialistPostReleaseSustained(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseSustained(appId, runId);" in app_js[hook_start:hook_start+3000]


def test_hub_app_js_honest_sustained_states(app_js):
    assert "state: 'Stable Service'" in app_js
    assert "state: 'Regression Watch'" in app_js
    assert "state: 'Relapse Detected'" in app_js


def test_hub_app_js_ties_sustained_to_payload(app_js):
    assert "returnLineage:" in app_js, "Missing return-to-service validation context binding"
    assert "sustainedBasis:" in app_js, "Missing baseline timeframe validation description"


def test_geometric_law_alcoa_sustained_hash(app_js):
    assert "btoa(entry.state + entry.returnLineage + entry.sustainedVerdict)" in app_js, \
        "ALCOA+ hash must bind state + returnLineage + sustainedVerdict"


def test_hub_app_js_exposes_active_sustained_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Sustained Basis:" in app_js
    assert "post-release return -> sustained-service path -> stable-service, regression-watch, or relapse-detected state" in app_js


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-sustained.sh"
    assert path.exists(), "Missing SAC58 smoke script"


def test_prime_mermaid_sustained_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-sustained.prime-mermaid.md"
    assert path.exists(), "SAC58 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
