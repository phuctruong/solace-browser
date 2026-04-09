"""
Test: Verification of SAC50 Specialist Convention-Rollout Visibility
Persona: Donald Knuth (Verification Precision)
Validates Live/Staged/Aborted states correctly proving 
whether the Dev Manager's release action converted into physical systemic deployment.
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


def test_html_has_convention_rollout_card(html_soup):
    card = html_soup.find(id="dev-specialist-convention-rollout-card")
    assert card is not None, "Missing Section 4ak: convention rollout card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Convention Rollout / Release Execution" in kicker.text
    assert html_soup.find(id="dev-specialist-convention-rollout-state") is not None


def test_hub_app_js_has_rollout_function(app_js):
    assert "function updateSpecialistConventionRollout(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistConventionRollout(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_rollout_states(app_js):
    assert "'Live'" in app_js
    assert "'Staged'" in app_js
    assert "'Aborted'" in app_js


def test_hub_app_js_ties_rollout_to_payload(app_js):
    assert "actionLineage:" in app_js, "Missing manager signoff action verification"
    assert "executionVerdict:" in app_js, "Missing physical execution verdict description"


def test_hub_app_js_has_active_rollout_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Rollout Basis:" in app_js
    assert "real approval and release records with ready versus shipped separation" in app_js


def test_geometric_law_alcoa_rollout_hash(app_js):
    assert "btoa(entry.state + entry.actionLineage + entry.executionVerdict)" in app_js, \
        "ALCOA+ hash must bind state + actionLineage + executionVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-convention-rollout.sh"
    assert path.exists(), "Missing SAC50 smoke script"


def test_prime_mermaid_rollout_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-convention-rollout.prime-mermaid.md"
    assert path.exists(), "SAC50 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
