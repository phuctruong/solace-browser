"""
Test: Verification of SAV38 Specialist Artifact Provenance Visibility
Persona: Donald Knuth (Verification Precision)
Validates Verified/Partial/Invalid integrity states and provenance chain
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


def test_html_has_provenance_card(html_soup):
    card = html_soup.find(id="dev-specialist-artifact-provenance-card")
    assert card is not None, "Missing Section 4y: artifact provenance card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Artifact Provenance" in kicker.text
    assert html_soup.find(id="dev-specialist-artifact-provenance-state") is not None


def test_hub_app_js_has_provenance_function(app_js):
    assert "function updateSpecialistArtifactProvenance(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistArtifactProvenance(appId, runId);" in app_js[hook_start:hook_start+1000]


def test_hub_app_js_honest_integrity_states(app_js):
    assert "integrity: 'Verified'" in app_js
    assert "integrity: 'Partial'" in app_js
    assert "integrity: 'Invalid'" in app_js


def test_hub_app_js_ties_provenance_to_payload(app_js):
    assert "origin:" in app_js, "Missing provenance chain origin"
    assert "checks:" in app_js, "Missing integrity checks array"
    assert "hash-match" in app_js, "Missing hash-match result type"
    assert "hash-mismatch" in app_js, "Missing hash-mismatch result type"
    assert "'missing'" in app_js, "Missing 'missing' result type"


def test_hub_app_js_has_active_provenance_context(app_js):
    assert "Audit Constraints:" in app_js, "Missing provenance constraint header"
    assert "Provenance Basis:" in app_js, "Missing explicit provenance basis"
    assert "Resolution Bound:" in app_js, "Missing provenance resolution bound"


def test_geometric_law_alcoa_provenance_hash(app_js):
    assert "btoa(entry.integrity + entry.bundleId + entry.origin)" in app_js, \
        "ALCOA+ hash must bind integrity + bundleId + origin"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-artifact-provenance.sh"
    assert path.exists(), "Missing SAV38 smoke script"


def test_prime_mermaid_provenance_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-artifact-provenance.prime-mermaid.md"
    assert path.exists(), "SAV38 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
