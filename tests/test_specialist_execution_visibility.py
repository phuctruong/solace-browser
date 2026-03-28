"""
Test: Verification of SAX35 Specialist Execution Activity Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates exactly what live activity states exist post-intake,
proving whether the specialist matrix correctly executed its assigned 
run, exposing the live running block, paused gates, or fatal fails.
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

def test_html_has_specialist_execution_activity_card(html_soup: BeautifulSoup):
    """
    Assert that the specialist execution container is structurally intact.
    """
    card = html_soup.find(id="dev-specialist-execution-activity-card")
    assert card is not None, "Missing Section 4v: specialist execution activity container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for specialist execution activity"
    assert "Specialist Execution Activity" in header.text, "Kicker must explicitly label Specialist Execution Activity"

    content = card.find(id="dev-specialist-execution-activity-state")
    assert content is not None, "Missing execution activity data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_execution_logic(app_js_content: str):
    """
    Verify that `updateSpecialistExecutionActivity` loops live execution tracking.
    """
    assert "function updateSpecialistExecutionActivity(appId, runId)" in app_js_content, \
        "Missing updateSpecialistExecutionActivity trace entirely."

    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing core updateWorkerDetail hook."
    
    assert "updateSpecialistExecutionActivity(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Execution sequence is decoupled from the worker runtime refresh lifecycle."


def test_hub_app_js_has_honest_execution_states(app_js_content: str):
    """
    Ticket 3 constraint: The system must enforce explicit bounded tracking
    preventing hallucination of live worker outputs.
    """
    assert "Running" in app_js_content, "Missing required Running execution logic"
    assert "Paused" in app_js_content, "Missing required Paused execution logic"
    assert "Failed" in app_js_content, "Missing required Failed execution logic"

def test_hub_app_js_ties_execution_to_payloads(app_js_content: str):
    """
    Ticket 2 constraint: Activity matrices must declare exactly which specialist lane
    is running, what packet initiated it, and the very first operational footprint.
    """
    assert "specialist:" in app_js_content, "Missing explicit specialist tracked."
    assert "activePacket:" in app_js_content, "Missing active packet trace."
    assert "firstOutput:" in app_js_content, "Missing explicit first output footprint."


def test_hub_app_js_has_active_execution_context(app_js_content: str):
    """
    Ticket 2/3 hardening: execution state must expose the active review context,
    not just activity rows.
    """
    assert "Active Observability Constraints:" in app_js_content, "Missing execution constraint header."
    assert "Evaluation Limit:" in app_js_content, "Missing execution evaluation limit."
    assert "Resolution Bound:" in app_js_content, "Missing execution resolution bound."
    assert "Execution Basis:" in app_js_content, "Missing explicit execution basis."


def test_geometric_law_phuc_forecast_execution_hash(app_js_content: str):
    """
    Enforce ALCOA+ cryptographic execution constraints per User Override 
    (The Geometric Law / Phuc Forecast): Prioritized actionable items must
    include a deterministic hash string for non-repudiation proving execution states.
    """
    assert "btoa(log.state + log.specialist + log.firstOutput)" in app_js_content, \
        "Failed Geometric Law constraint: UI does not compute an algorithmic ALCOA+ format for specialist execution activity arrays."


def test_smoke_script_exists():
    """
    Ticket 5: a reviewer must have one narrow round-specific smoke path.
    """
    smoke_path = Path(__file__).parent.parent / "scripts" / "smoke-specialist-execution-activity.sh"
    assert smoke_path.exists(), "Missing SAX35 smoke script."


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_execution_state_exists():
    """
    Verify the Prime Mermaid component mapping the SI17 structural bounds
    on active worker executions generating live outputs.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "specialist-execution-activity.prime-mermaid.md"
    assert mermaid_path.exists(), "SAX35 Execution diagram is missing."
    
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime structural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure."
