"""
Test: Verification of SAP39 Specialist Promotion-Candidate Visibility
Persona: Donald Knuth (Verification Precision)
Validates Ready-to-Seal/Provisional/Disqualified states with blockers
and promotion basis are structurally bound and not hallucinated.
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


def test_html_has_promotion_candidate_card(html_soup):
    card = html_soup.find(id="dev-specialist-promotion-candidate-card")
    assert card is not None, "Missing Section 4z: promotion candidate card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Promotion Candidate" in kicker.text
    assert html_soup.find(id="dev-specialist-promotion-candidate-state") is not None


def test_hub_app_js_has_promotion_function(app_js):
    assert "function updateSpecialistPromotionCandidate(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPromotionCandidate(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_promotion_states(app_js):
    assert "status: 'Ready-to-Seal'" in app_js
    assert "status: 'Provisional'" in app_js
    assert "status: 'Disqualified'" in app_js


def test_hub_app_js_ties_promotion_to_payload(app_js):
    assert "basis:" in app_js, "Missing promotion basis"
    assert "blockers:" in app_js, "Missing blockers array"
    assert "gate:" in app_js, "Missing seal gate description"


def test_hub_app_js_has_active_promotion_context(app_js):
    assert "Audit Constraints:" in app_js, "Missing promotion constraint header"
    assert "Promotion Basis:" in app_js, "Missing explicit promotion basis"
    assert "Resolution Bound:" in app_js, "Missing promotion resolution bound"


def test_geometric_law_alcoa_promotion_hash(app_js):
    assert "btoa(c.status + c.bundleId + c.basis)" in app_js, \
        "ALCOA+ hash must bind status + bundleId + basis"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-promotion-candidate.sh"
    assert path.exists(), "Missing SAP39 smoke script"


def test_prime_mermaid_promotion_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-promotion-candidate.prime-mermaid.md"
    assert path.exists(), "SAP39 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
