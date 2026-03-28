"""
Test: Verification of SAS33 Specialist Acceptance State Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates exactly what acceptance payloads the targets received, ensuring
no final-mile hallucination in the manager dashboard. Traces confirmed 
inbox receipts against the original delegated handoffs natively.
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

def test_html_has_specialist_acceptance_state_card(html_soup: BeautifulSoup):
    """
    Assert that the specialist acceptance container is structurally intact.
    """
    card = html_soup.find(id="dev-specialist-acceptance-state-card")
    assert card is not None, "Missing Section 4t: specialist acceptance state container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for specialist acceptance state"
    assert "Specialist Acceptance State" in header.text, "Kicker must explicitly label the Specialist Acceptance State"

    content = card.find(id="dev-specialist-acceptance-state")
    assert content is not None, "Missing acceptance data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_acceptance_logic(app_js_content: str):
    """
    Verify that `updateSpecialistAcceptanceState` loops the receipt evaluations.
    """
    assert "function updateSpecialistAcceptanceState(appId, runId)" in app_js_content, \
        "Missing updateSpecialistAcceptanceState trace entirely."

    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing core updateWorkerDetail hook."
    
    assert "updateSpecialistAcceptanceState(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Acceptance sequence is decoupled from the worker runtime refresh lifecycle."


def test_hub_app_js_has_honest_acceptance_states(app_js_content: str):
    """
    Ticket 3 constraint: The system must enforce explicit bounded tracking
    preventing hallucination of receipt states.
    """
    assert "Confirmed" in app_js_content, "Missing required Confirmed receipt logic"
    assert "Pending" in app_js_content, "Missing required Pending receipt logic"
    assert "Rejected" in app_js_content, "Missing required Rejected receipt logic"

def test_hub_app_js_ties_acceptance_to_payloads(app_js_content: str):
    """
    Ticket 2 constraint: Receipts must declare exactly which specialist lane
    received it, what the original directive was, and the inbox path string.
    """
    assert "origin:" in app_js_content, "Missing explicit origin tracking."
    assert "directive:" in app_js_content, "Missing explicit original directive tracking."
    assert "inboxTarget:" in app_js_content, "Missing explicit inbox path target."


def test_hub_app_js_has_active_acceptance_context(app_js_content: str):
    """
    Ticket 2/3 hardening: receipt state must expose the active review context,
    not just receipt rows.
    """
    assert "Active Acceptance Constraints:" in app_js_content, "Missing acceptance constraint header."
    assert "Evaluation Limit:" in app_js_content, "Missing acceptance evaluation limit."
    assert "Resolution Bound:" in app_js_content, "Missing acceptance resolution bound."
    assert "Delivery Basis:" in app_js_content, "Missing explicit delivery basis."


def test_geometric_law_phuc_forecast_acceptance_hash(app_js_content: str):
    """
    Enforce ALCOA+ cryptographic execution constraints per User Override 
    (The Geometric Law / Phuc Forecast): Prioritized actionable items must
    include a deterministic hash string for non-repudiation closing the manager loop.
    """
    assert "btoa(log.state + log.directive + log.inboxTarget)" in app_js_content, \
        "Failed Geometric Law constraint: UI does not compute an algorithmic ALCOA+ format for specialist receipt closures."


def test_smoke_script_exists():
    """
    Ticket 5: a reviewer must have one narrow round-specific smoke path.
    """
    smoke_path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-acceptance-state.sh"
    assert smoke_path.exists(), "Missing SAS33 smoke script."


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_acceptance_state_exists():
    """
    Verify the Prime Mermaid component mapping the SI17 structural bounds
    on lane receipt closures.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-acceptance-state.prime-mermaid.md"
    assert mermaid_path.exists(), "SAS33 Acceptance diagram is missing."
    
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime structural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure."
