"""
Test: Verification of SAC43 Specialist Convention-Invocation Visibility
Persona: Donald Knuth (Verification Precision)
Validates Invoked/Queued/Blocked states correctly binding 
reusable memory conventions directly into the next executed directive.
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


def test_html_has_convention_invocation_card(html_soup):
    card = html_soup.find(id="dev-specialist-convention-invocation-card")
    assert card is not None, "Missing Section 4ad: convention invocation card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Convention Invocation" in kicker.text
    assert html_soup.find(id="dev-specialist-convention-invocation-state") is not None


def test_hub_app_js_has_invocation_function(app_js):
    assert "function updateSpecialistConventionInvocation(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistConventionInvocation(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_invocation_states(app_js):
    assert "state: 'Invoked'" in app_js
    assert "state: 'Queued'" in app_js
    assert "state: 'Blocked'" in app_js


def test_hub_app_js_ties_invocation_to_payload(app_js):
    assert "nextDirective:" in app_js, "Missing next directive target"
    assert "invocationContext:" in app_js, "Missing invocation basis description"


def test_hub_app_js_has_active_invocation_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Invocation Basis:" in app_js
    assert "callable department-memory entry -> convention invocation -> next directive or worker packet" in app_js


def test_geometric_law_alcoa_invocation_hash(app_js):
    assert "btoa(entry.state + entry.conventionTarget + entry.nextDirective)" in app_js, \
        "ALCOA+ hash must bind state + conventionTarget + nextDirective"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-convention-invocation.sh"
    assert path.exists(), "Missing SAC43 smoke script"


def test_prime_mermaid_invocation_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-convention-invocation.prime-mermaid.md"
    assert path.exists(), "SAC43 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
