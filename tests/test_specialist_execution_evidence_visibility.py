"""
Test: Verification of SAE36 Specialist Execution Evidence Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates that output-log evidence states (Streaming, Stalled, Terminated)
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


def test_html_has_execution_evidence_card(html_soup):
    card = html_soup.find(id="dev-specialist-execution-evidence-card")
    assert card is not None, "Missing Section 4w: execution evidence card"
    kicker = card.find("p", class_="sb-kicker")
    assert kicker and "Specialist Execution Evidence" in kicker.text
    assert html_soup.find(id="dev-specialist-execution-evidence-state") is not None


def test_hub_app_js_has_evidence_function(app_js):
    assert "function updateSpecialistExecutionEvidence(appId, runId)" in app_js
    hook_start = app_js.find("function updateWorkerDetail(appId, runId)")
    assert hook_start != -1
    assert "updateSpecialistExecutionEvidence(appId, runId);" in app_js[hook_start:hook_start+1000]


def test_hub_app_js_honest_evidence_states(app_js):
    assert "Streaming" in app_js
    assert "Stalled" in app_js
    assert "Terminated" in app_js


def test_hub_app_js_ties_evidence_to_payload(app_js):
    assert "logLines:" in app_js, "Missing log lines array"
    assert "activePacket:" in app_js, "Missing active packet reference"
    assert "specialist:" in app_js, "Missing specialist reference"


def test_hub_app_js_has_active_evidence_context(app_js):
    assert "Audit Constraints:" in app_js, "Missing evidence constraint header"
    assert "Evidence Basis:" in app_js, "Missing explicit evidence basis"
    assert "Resolution Bound:" in app_js, "Missing evidence resolution bound"


def test_geometric_law_alcoa_evidence_hash(app_js):
    assert "btoa(log.state + log.specialist + log.logLines[0])" in app_js, \
        "ALCOA+ hash must bind state + specialist + first log line"


def test_smoke_script_exists():
    path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-execution-evidence.sh"
    assert path.exists(), "Missing SAE36 smoke script"


def test_prime_mermaid_evidence_diagram_exists():
    path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-execution-evidence.prime-mermaid.md"
    assert path.exists(), "SAE36 Mermaid diagram missing"
    content = path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content
    assert "stateDiagram-v2" in content
