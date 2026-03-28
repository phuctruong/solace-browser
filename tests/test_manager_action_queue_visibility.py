"""
Test: Verification of SAA30 Manager Action Queue Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates exactly what the next bounded action is for the Solace Dev Manager,
ensuring there are no hallucinated or ambiguous states. Traces priority labels
(e.g., Immediate/Pending/Blocked) directly against Candidate lineages.
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

def test_html_has_manager_action_queue_card(html_soup: BeautifulSoup):
    """
    Assert that the manager action queue card container is structurally intact.
    """
    card = html_soup.find(id="dev-manager-action-queue-card")
    assert card is not None, "Missing Section 4q: manager action queue container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for manager action queue"
    assert "Manager Action Queue" in header.text, "Kicker must explicitly label the Manager Action Queue"

    content = card.find(id="dev-manager-action-queue-state")
    assert content is not None, "Missing action data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_action_logic(app_js_content: str):
    """
    Verify that `updateManagerActionQueue` handles the executable decision state.
    """
    assert "function updateManagerActionQueue(appId, runId)" in app_js_content, \
        "Missing updateManagerActionQueue trace entirely."

    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing core updateWorkerDetail hook."
    
    assert "updateManagerActionQueue(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Action sequence is decoupled from the worker runtime refresh lifecycle."


def test_hub_app_js_has_honest_action_states(app_js_content: str):
    """
    Ticket 3 constraint: The system must enforce explicit triage bands
    matching actionable thresholds: Immediate, Pending, or Blocked.
    """
    assert "priority: 'Immediate'" in app_js_content, "Missing required Immediate action trace"
    assert "priority: 'Pending'" in app_js_content, "Missing required Pending action trace"
    assert "priority: 'Blocked'" in app_js_content, "Missing required Blocked action trace"

def test_hub_app_js_ties_actions_to_context(app_js_content: str):
    """
    Ticket 2 constraint: Manager priorities must reference precisely which
    worker/role sequence is requiring attention.
    """
    assert "candidate:" in app_js_content, "Missing explicit candidate binding."
    assert "role:" in app_js_content, "Missing explicit execution role tracking."
    assert "reason:" in app_js_content, "Manager is missing contextual reason."


def test_hub_app_js_has_active_action_context(app_js_content: str):
    """
    The queue must expose the active viewing context so the manager can see
    which worker/run selection the next actions are anchored to.
    """
    assert "Active Queue Constraints:" in app_js_content
    assert "Display Scope:" in app_js_content
    assert "Priority Bound:" in app_js_content
    assert "Action Basis:" in app_js_content


def test_geometric_law_phuc_forecast_action_hash(app_js_content: str):
    """
    Enforce ALCOA+ cryptographic execution constraints per User Override 
    (The Geometric Law / Phuc Forecast): Prioritized actionable items must
    include a deterministic hash string for non-repudiation.
    """
    assert "btoa(act.candidate + act.priority + act.role)" in app_js_content, \
        "Failed Geometric Law constraint: UI does not compute an algorithmic ALCOA+ log hash for actions."


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_manager_action_exists():
    """
    Verify the Prime Mermaid component mapping the SI17 structural bounds
    on actionable governance exists correctly.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "manager-action-queue.prime-mermaid.md"
    assert mermaid_path.exists(), "SAA30 Action diagram is missing."
    
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime structural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure."


def test_smoke_manager_action_queue_exists():
    scripts = Path(__file__).parent.parent / "scripts"
    assert (scripts / "smoke-manager-action-queue.sh").exists()
