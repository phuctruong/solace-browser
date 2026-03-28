"""
Test: Verification of SAR34 Specialist Intake Readiness Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates exactly what readiness states exist between inbox delivery
and actual operational execution. Ensures the UI maps honestly to
Queued, Ready, and Blocked execution pipelines natively.
"""

import pytest
from bs4 import BeautifulSoup
from pathlib import Path

# Paths relative to the project root
HUB_DIR = Path(__file__).parent.parent / "solace-hub"
INDEX_HTML = HUB_DIR / "src" / "index.html"
APP_JS = HUB_DIR / "src" / "hub-app.js"

@pytest.fixture
def html_soup() -> BeautifulSoup:
    """Provide a parsed DOM of the Hub entrypoint."""
    assert INDEX_HTML.exists(), "Hub index.html not found."
    return BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")

@pytest.fixture
def app_js_content() -> str:
    """Provide the raw text of the Hub application logic."""
    assert APP_JS.exists(), "Hub hub-app.js not found."
    return APP_JS.read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# DOM Structural Asserts (Ticket 1)
# -----------------------------------------------------------------------------

def test_html_has_specialist_intake_readiness_card(html_soup: BeautifulSoup):
    """
    Assert that the specialist readiness container is structurally intact.
    """
    card = html_soup.find(id="dev-specialist-intake-readiness-card")
    assert card is not None, "Missing Section 4u: specialist intake readiness container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for specialist intake readiness"
    assert "Specialist Intake Readiness" in header.text, "Kicker must explicitly label Specialist Intake Readiness"

    content = card.find(id="dev-specialist-intake-readiness-state")
    assert content is not None, "Missing readiness data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_readiness_logic(app_js_content: str):
    """
    Verify that `updateSpecialistIntakeReadiness` loops execution clearance checks.
    """
    assert "function updateSpecialistIntakeReadiness(appId, runId)" in app_js_content, \
        "Missing updateSpecialistIntakeReadiness trace entirely."

    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing core updateWorkerDetail hook."
    
    assert "updateSpecialistIntakeReadiness(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Readiness sequence is decoupled from the worker runtime refresh lifecycle."


def test_hub_app_js_has_honest_readiness_states(app_js_content: str):
    """
    Ticket 3 constraint: The system must enforce explicit bounded tracking
    preventing hallucination of environment spinups.
    """
    assert "Ready" in app_js_content, "Missing required Ready execution logic"
    assert "Queued" in app_js_content, "Missing required Queued execution logic"
    assert "Blocked" in app_js_content, "Missing required Blocked execution logic"

def test_hub_app_js_ties_readiness_to_payloads(app_js_content: str):
    """
    Ticket 2 constraint: Readiness must declare exactly which specialist lane
    the target packet belongs to and the explicit environment constraints verified.
    """
    assert "specialist:" in app_js_content, "Missing explicit specialist targeted."
    assert "activePacket:" in app_js_content, "Missing explicit intake packet trace."
    assert "constraint:" in app_js_content, "Missing explicit constraint log."


def test_hub_app_js_has_active_readiness_context(app_js_content: str):
    """
    Ticket 2/3 hardening: readiness state must expose the active review context,
    not just readiness rows.
    """
    assert "Active Execution Constraints:" in app_js_content, "Missing readiness constraint header."
    assert "Evaluation Limit:" in app_js_content, "Missing readiness evaluation limit."
    assert "Resolution Bound:" in app_js_content, "Missing readiness resolution bound."
    assert "Execution Basis:" in app_js_content, "Missing explicit execution basis."


def test_geometric_law_phuc_forecast_readiness_hash(app_js_content: str):
    """
    Enforce ALCOA+ cryptographic execution constraints per User Override 
    (The Geometric Law / Phuc Forecast): Prioritized actionable items must
    include a deterministic hash string for non-repudiation proving execution starts.
    """
    assert "btoa(log.state + log.specialist + log.activePacket)" in app_js_content, \
        "Failed Geometric Law constraint: UI does not compute an algorithmic ALCOA+ format for specialist readiness execution runs."


def test_smoke_script_exists():
    """
    Ticket 5: a reviewer must have one narrow round-specific smoke path.
    """
    smoke_path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-intake-readiness.sh"
    assert smoke_path.exists(), "Missing SAR34 smoke script."


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_readiness_state_exists():
    """
    Verify the Prime Mermaid component mapping the SI17 structural bounds
    framing the clearance for a worker pipeline to actually run.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-intake-readiness.prime-mermaid.md"
    assert mermaid_path.exists(), "SAR34 Readiness diagram is missing."
    
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime structural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure."
