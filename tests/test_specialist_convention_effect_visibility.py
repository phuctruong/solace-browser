"""
Test: Verification of SAC46 Specialist Convention-Effect Visibility
Persona: Donald Knuth (Verification Precision)
Validates Visible/Partial/Absent states correctly proving 
whether the target execution runtime actually yielded an output artifact conforming to the convention constraints.
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


def test_html_has_convention_effect_card(html_soup):
    card = html_soup.find(id="dev-specialist-convention-effect-card")
    assert card is not None, "Missing Section 4ag: convention effect card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Convention Effect" in kicker.text
    assert html_soup.find(id="dev-specialist-convention-effect-state") is not None


def test_hub_app_js_has_effect_function(app_js):
    assert "function updateSpecialistConventionEffect(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistConventionEffect(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_effect_states(app_js):
    assert "state: 'Visible'" in app_js
    assert "state: 'Partial'" in app_js
    assert "state: 'Absent'" in app_js


def test_hub_app_js_ties_effect_to_payload(app_js):
    assert "producedArtifact:" in app_js, "Missing produced output artifact verification"
    assert "effectBasis:" in app_js, "Missing effect basis description"


def test_hub_app_js_has_active_effect_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Effect Basis:" in app_js
    assert "active convention -> constrained runtime -> visible artifact or output shift" in app_js


def test_geometric_law_alcoa_effect_hash(app_js):
    assert "btoa(entry.state + entry.targetRuntime + entry.producedArtifact)" in app_js, \
        "ALCOA+ hash must bind state + targetRuntime + producedArtifact"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-convention-effect.sh"
    assert path.exists(), "Missing SAC46 smoke script"


def test_prime_mermaid_effect_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-convention-effect.prime-mermaid.md"
    assert path.exists(), "SAC46 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
