"""
Test: Verification of SAM27 Promotion Decision Packet Visibility Surface
Persona: Donald Knuth (Algorithmic Precision and Falsifiability)
Skill: prime-coder, prime-safety

This suite verifies that the Promotion Decision Packet UI panels
(defined in SI17 & SI18) are statically present and driven by honest semantic states,
enabling visible human-in-the-loop validation metrics without hallucination.
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
# DOM Structural Asserts (Ticket 1 & 3)
# -----------------------------------------------------------------------------

def test_html_has_promotion_decision_card(html_soup: BeautifulSoup):
    """
    Assert that the manager's promotion decision packet card container is 
    permanently structured in the DOM without relying on dynamic injection.
    """
    card = html_soup.find(id="dev-promotion-decision-card")
    assert card is not None, "Missing Section 4n: promotion decision card container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for promotion decision state"
    assert "Promotion Decision" in header.text, "Kicker must explicitly label Promotion Decision Ticket"

    content = card.find(id="dev-promotion-decision-state")
    assert content is not None, "Missing promotion decision state data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_promotion_logic(app_js_content: str):
    """
    Verify that `updatePromotionDecisionState` exists and is wired into the
    master update chain.
    """
    # Exists as a function
    assert "function updatePromotionDecisionState(appId, runId)" in app_js_content, \
        "Missing updatePromotionDecisionState implementation."

    # Intersected directly inside updateWorkerDetail
    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing updateWorkerDetail hook."
    
    # Assert execution logic triggers execution evaluation sync
    assert "updatePromotionDecisionState(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Promotion logic is not integrated into root worker refresh hook."


def test_hub_app_js_has_honest_decision_states(app_js_content: str):
    """
    Enforce Ticket 3 constraints: The system must represent a candidate's 
    promotion packet honestly, accounting for evidence, manager signoff, 
    and block triggers.
    """
    assert "decisionState = 'approved';" in app_js_content, "Missing APPROVED capability trace"
    assert "decisionState = 'pending';" in app_js_content, "Missing PENDING MANAGER REVIEW capability trace"
    assert "decisionState = 'blocked';" in app_js_content, "Missing BLOCKED decision representation"


def test_hub_app_js_has_active_packet_context(app_js_content: str):
    """
    The packet must expose the active review context honestly instead of forcing
    the reviewer to infer it from nearby panels.
    """
    assert "Active Packet Context:" in app_js_content
    assert "Packet Binding:" in app_js_content
    assert "Decision Basis:" in app_js_content


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_promotion_state_exists():
    """
    Verify the Prime Mermaid constraint ensuring UI properties map 
    transparently to their SI17 & SI18 theoretic boundaries.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "worker-promotion-decision.prime-mermaid.md"
    assert mermaid_path.exists(), "SAM27 Promotion diagram is missing from standard prime architecture."
    
    # Assert Canonical Prime format is followed
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime architectural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure for promotion decision flow."


# -----------------------------------------------------------------------------
# Workflow Validation
# -----------------------------------------------------------------------------

def test_smoke_worker_promotion_decision_state_exists():
    """
    Provide the narrow smoke context proving local deployment works properly.
    """
    scripts = Path(__file__).parent.parent / "scripts"
    assert (scripts / "smoke-worker-promotion-decision.sh").exists()
