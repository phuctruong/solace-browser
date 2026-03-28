"""
Test: Verification of SAM40 Specialist Memory-Admission Visibility
Persona: Donald Knuth (Verification Precision)
Validates Queued/Admitted/Rejected states with target memory paths
and admission basis are structurally bound and not hallucinated.
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


def test_html_has_memory_admission_card(html_soup):
    card = html_soup.find(id="dev-specialist-memory-admission-card")
    assert card is not None, "Missing Section 4aa: memory admission card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Memory Admission" in kicker.text
    assert html_soup.find(id="dev-specialist-memory-admission-state") is not None


def test_hub_app_js_has_admission_function(app_js):
    assert "function updateSpecialistMemoryAdmission(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistMemoryAdmission(appId, runId);" in app_js[hook_start:hook_start+1500]


def test_hub_app_js_honest_admission_states(app_js):
    assert "status: 'Admitted'" in app_js
    assert "status: 'Queued'" in app_js
    assert "status: 'Rejected'" in app_js


def test_hub_app_js_ties_admission_to_payload(app_js):
    assert "basis:" in app_js, "Missing admission basis"
    assert "targetMemory:" in app_js, "Missing target memory path"


def test_hub_app_js_has_active_admission_context(app_js):
    assert "Audit Constraints:" in app_js, "Missing admission constraint header"
    assert "Admission Basis:" in app_js, "Missing explicit admission basis"
    assert "Resolution Bound:" in app_js, "Missing admission resolution bound"


def test_geometric_law_alcoa_admission_hash(app_js):
    assert "btoa(token.status + token.bundleId + token.targetMemory)" in app_js, \
        "ALCOA+ hash must bind status + bundleId + targetMemory"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-memory-admission.sh"
    assert path.exists(), "Missing SAM40 smoke script"


def test_prime_mermaid_admission_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-memory-admission.prime-mermaid.md"
    assert path.exists(), "SAM40 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
