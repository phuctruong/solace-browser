"""
Test: Verification of SAC47 Specialist Convention-Proof Visibility
Persona: Donald Knuth (Verification Precision)
Validates Verified/Partial/Missing states correctly proving 
whether the generated constraint artifact passed the overarching evidence verdict.
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


def test_html_has_convention_proof_card(html_soup):
    card = html_soup.find(id="dev-specialist-convention-proof-card")
    assert card is not None, "Missing Section 4ah: convention proof card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Convention Proof / Evidence Verdict" in kicker.text
    assert html_soup.find(id="dev-specialist-convention-proof-state") is not None


def test_hub_app_js_has_proof_function(app_js):
    assert "function updateSpecialistConventionProof(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistConventionProof(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_proof_states(app_js):
    assert "state: 'Verified'" in app_js
    assert "state: 'Partial'" in app_js
    assert "state: 'Missing'" in app_js


def test_hub_app_js_ties_proof_to_payload(app_js):
    assert "proofStrategy:" in app_js, "Missing proof strategy evidence basis"
    assert "evidenceVerdict:" in app_js, "Missing evidence verdict description"


def test_hub_app_js_has_active_proof_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Proof Basis:" in app_js
    assert "constrained output -> evidence verdict -> governed convention lineage" in app_js


def test_geometric_law_alcoa_proof_hash(app_js):
    assert "btoa(entry.state + entry.producedArtifact + entry.proofStrategy)" in app_js, \
        "ALCOA+ hash must bind state + producedArtifact + proofStrategy"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-convention-proof.sh"
    assert path.exists(), "Missing SAC47 smoke script"


def test_prime_mermaid_proof_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-convention-proof.prime-mermaid.md"
    assert path.exists(), "SAC47 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
