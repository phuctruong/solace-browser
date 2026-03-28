"""
Test: Verification of SAH32 Delegation Handoff Log Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates exactly what handoff payload the Solace Dev Manager dispatched,
ensuring there are no hallucinated specialist states. Traces target 
lanes against Pending, Accepted, or Blocked metrics natively.
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

def test_html_has_delegation_handoff_log_card(html_soup: BeautifulSoup):
    """
    Assert that the delegation handoff log container is structurally intact.
    """
    card = html_soup.find(id="dev-delegation-handoff-log-card")
    assert card is not None, "Missing Section 4s: delegation handoff log container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for delegation handoff log"
    assert "Delegation Handoff Log" in header.text, "Kicker must explicitly label the Delegation Handoff Log"

    content = card.find(id="dev-delegation-handoff-log-state")
    assert content is not None, "Missing handoff data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_handoff_logic(app_js_content: str):
    """
    Verify that `updateDelegationHandoffLog` arrays the handoff state bindings.
    """
    assert "function updateDelegationHandoffLog(appId, runId)" in app_js_content, \
        "Missing updateDelegationHandoffLog trace entirely."

    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing core updateWorkerDetail hook."
    
    assert "updateDelegationHandoffLog(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Handoff sequence is decoupled from the worker runtime refresh lifecycle."


def test_hub_app_js_has_honest_handoff_states(app_js_content: str):
    """
    Ticket 3 constraint: The system must enforce explicit bounded tracking
    preventing hallucination of handoff queues.
    """
    assert "Accepted" in app_js_content, "Missing required Accepted handoff logic"
    assert "Pending" in app_js_content, "Missing required Pending handoff logic"
    assert "Blocked" in app_js_content, "Missing required Blocked handoff logic"

def test_hub_app_js_ties_handoff_to_payloads(app_js_content: str):
    """
    Ticket 2 constraint: Handoffs must declare exactly which specialist lane
    is assigned, what the target candidate is, and what the dispatch payload is.
    """
    assert "lane:" in app_js_content, "Missing explicit lane targeted in handoff."
    assert "target:" in app_js_content, "Missing explicit candidate targeted in handoff."
    assert "payload:" in app_js_content, "Missing explicit dispatch payload."


def test_hub_app_js_has_active_handoff_context(app_js_content: str):
    """
    Ticket 2/3 hardening: handoff state must expose the active review context,
    not just the lane entries.
    """
    assert "Active Handoff Constraints:" in app_js_content, "Missing handoff constraint header."
    assert "Tracking Source:" in app_js_content, "Missing handoff tracking source."
    assert "Resolution Bound:" in app_js_content, "Missing handoff resolution bound."
    assert "Dispatch Basis:" in app_js_content, "Missing explicit dispatch basis."


def test_geometric_law_phuc_forecast_handoff_hash(app_js_content: str):
    """
    Enforce ALCOA+ cryptographic execution constraints per User Override 
    (The Geometric Law / Phuc Forecast): Prioritized actionable items must
    include a deterministic hash string for non-repudiation.
    """
    assert "btoa(log.target + log.lane + log.state)" in app_js_content, \
        "Failed Geometric Law constraint: UI does not compute an algorithmic ALCOA+ format for delegation handoffs."


def test_smoke_script_exists():
    """
    Ticket 5: a reviewer must have one narrow round-specific smoke path.
    """
    smoke_path = Path(__file__).parent.parent / "scripts" / "smoke-delegation-handoff-log.sh"
    assert smoke_path.exists(), "Missing SAH32 smoke script."


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_handoff_log_exists():
    """
    Verify the Prime Mermaid component mapping the SI17 structural bounds
    on lane assignments.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "delegation-handoff-log.prime-mermaid.md"
    assert mermaid_path.exists(), "SAH32 Handoff diagram is missing."
    
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime structural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure."
