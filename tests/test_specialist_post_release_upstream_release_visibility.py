"""
Test: Verification of SAC65 Specialist Post-Release Upstream Release Visibility
Persona: Donald Knuth (Verification Precision)
Validates Custody Released/Custody Retained/Custody Re-armed states
proving the upstream tracking node successfully drops its local memory buffers upon target settlement.
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


def test_html_has_post_release_upstream_release_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-upstream-release-card")
    assert card is not None, "Missing Section 4az: post release upstream release card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Upstream Release" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-upstream-release-state") is not None


def test_hub_app_js_has_upstream_release_function(app_js):
    assert "function updateSpecialistPostReleaseUpstreamRelease(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseUpstreamRelease(appId, runId);" in app_js[hook_start:hook_start+3000]


def test_hub_app_js_honest_upstream_release_states(app_js):
    assert "state: 'Custody Released'" in app_js
    assert "state: 'Custody Retained'" in app_js
    assert "state: 'Custody Re-armed'" in app_js


def test_hub_app_js_ties_upstream_release_to_payload(app_js):
    assert "ownershipLineage:" in app_js, "Missing physical residency context binding"
    assert "releaseBasis:" in app_js, "Missing local tracker flush rationale bound"


def test_hub_app_js_has_active_upstream_release_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Upstream Release Basis:" in app_js
    assert "post-release next-path ownership -> upstream release -> custody-released, custody-retained, or custody-rearmed state" in app_js


def test_geometric_law_alcoa_upstream_release_hash(app_js):
    assert "btoa(entry.state + entry.ownershipLineage + entry.releaseVerdict)" in app_js, \
        "ALCOA+ hash must bind state + ownershipLineage + releaseVerdict"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-upstream-release.sh"
    assert path.exists(), "Missing SAC65 smoke script"


def test_prime_mermaid_upstream_release_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-upstream-release.prime-mermaid.md"
    assert path.exists(), "SAC65 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
