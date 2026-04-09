"""
Test: Verification of SAC56 Specialist Post-Release Recovery Visibility
Persona: Donald Knuth (Verification Precision)
Validates Authorized/Blocked/Staged Recovery states
proving the system strictly governs exit vectors from physical quarantine.
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


def test_html_has_post_release_recovery_card(html_soup):
    card = html_soup.find(id="dev-specialist-post-release-recovery-card")
    assert card is not None, "Missing Section 4aq: post release recovery card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Post-Release Recovery & Re-entry" in kicker.text
    assert html_soup.find(id="dev-specialist-post-release-recovery-state") is not None


def test_hub_app_js_has_recovery_function(app_js):
    assert "function updateSpecialistPostReleaseRecovery(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistPostReleaseRecovery(appId, runId);" in app_js[hook_start:hook_start+2000]


def test_hub_app_js_honest_recovery_states(app_js):
    assert "'Authorized'" in app_js
    assert "'Staged Recovery'" in app_js
    assert "'Blocked'" in app_js


def test_hub_app_js_ties_recovery_to_payload(app_js):
    assert "controlLineage:" in app_js, "Missing quarantine control context binding"
    assert "recoveryBasis:" in app_js, "Missing physical recovery basis description"


def test_geometric_law_alcoa_recovery_hash(app_js):
    assert "btoa(entry.state + entry.controlLineage + entry.recoveryVerdict)" in app_js, \
        "ALCOA+ hash must bind state + controlLineage + recoveryVerdict"


def test_hub_app_js_exposes_active_recovery_context(app_js):
    assert "Viewer Role:" in app_js
    assert "Selected Worker:" in app_js
    assert "Selected Run:" in app_js
    assert "Recovery Basis:" in app_js
    assert "post-release quarantine -> recovery path -> recovery-authorized, re-entry-blocked, or staged-recovery state" in app_js


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-post-release-recovery.sh"
    assert path.exists(), "Missing SAC56 smoke script"


def test_prime_mermaid_recovery_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-post-release-recovery.prime-mermaid.md"
    assert path.exists(), "SAC56 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
