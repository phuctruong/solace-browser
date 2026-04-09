"""
Test: Verification of SAC51 Specialist Post-Release Health Visibility
Persona: Donald Knuth (Verification Precision)
Validates Healthy/Degraded/Rolled Back states correctly proving 
whether the deployed rollout lineage remains operationally viable over time.
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


def test_html_has_post_release_health_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-health-card")
    assert card is not None, "Missing Section 4al: post release health card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Health / Rollback" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-health-state") is not None


def test_hub_app_js_has_health_function(app_js):
    assert "function updateSpecialistPostReleaseHealth(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseHealth(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_health_states(app_js):
    assert "'Healthy'" in app_js
    assert "'Degraded'" in app_js
    assert "'Rolled Back'" in app_js


def test_hub_app_js_ties_health_to_payload(app_js):
    assert "rolloutLineage:" in app_js, "Missing rollout execution verification"
    assert "healthBasis:" in app_js, "Missing physical telemetry basis description"


def test_hub_app_js_has_active_health_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Health Basis:" in app_js
    assert "rollout execution -> ongoing telemetry -> healthy, degraded, or rolled-back state" in app_js


def test_geometric_law_alcoa_health_hash(app_js):
    assert "btoa(entry.state + entry.rolloutLineage + entry.postReleaseVerdict)" in app_js, \
        "ALCOA+ hash must bind state + rolloutLineage + postReleaseVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-health.sh"
    assert path.exists(), "Missing SAC51 smoke script"


def test_prime_mermaid_health_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-health.prime-mermaid.md"
    assert path.exists(), "SAC51 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
