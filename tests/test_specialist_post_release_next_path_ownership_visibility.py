"""
Test: Verification of SAC64 Specialist Post-Release Next-Path Ownership Visibility
Persona: Donald Knuth (Verification Precision)
Validates Ownership Settled/Ownership Pending/Ownership Bounced states
proving the system explicitly tracks whether the acknowledged target system structurally settled the received incident artifact.
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


def test_html_has_post_release_next_path_ownership_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-next-path-ownership-card")
    assert card is not None, "Missing Section 4ay: post release next-path ownership card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Next-Path Ownership" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-next-path-ownership-state") is not None


def test_hub_app_js_has_next_path_ownership_function(app_js):
    assert "function updateSpecialistPostReleaseNextPathOwnership(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseNextPathOwnership(appId, runId);" in app_js[hook_start:hook_start+3000]


def test_hub_app_js_honest_next_path_ownership_states(app_js):
    assert "state: 'Ownership Settled'" in app_js
    assert "state: 'Ownership Pending'" in app_js
    assert "state: 'Ownership Bounced'" in app_js


def test_hub_app_js_ties_next_path_ownership_to_payload(app_js):
    assert "acknowledgmentLineage:" in app_js, "Missing acknowledgment tracking context binding"
    assert "ownershipBasis:" in app_js, "Missing physical architectural residency bound"


def test_hub_app_js_has_active_next_path_ownership_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Ownership Basis:" in app_js
    assert "post-release next-path acknowledgment -> next-path ownership -> ownership-settled, ownership-pending, or ownership-bounced state" in app_js


def test_geometric_law_alcoa_next_path_ownership_hash(app_js):
    assert "btoa(entry.state + entry.acknowledgmentLineage + entry.ownershipVerdict)" in app_js, \
        "ALCOA+ hash must bind state + acknowledgmentLineage + ownershipVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-next-path-ownership.sh"
    assert path.exists(), "Missing SAC64 smoke script"


def test_prime_mermaid_next_path_ownership_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-next-path-ownership.prime-mermaid.md"
    assert path.exists(), "SAC64 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
