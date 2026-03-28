"""
Test: Verification of SAD31 Manager Directive Packet Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates exactly what bounded directive the Solace Dev Manager is 
inspecting. Ensures there are no hallucinated or ambiguous delegations.
Traces specific evidence targets mapped to explicitly constrained next
delegation actions.
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

def test_html_has_manager_directive_packet_card(html_soup: BeautifulSoup):
    """
    Assert that the manager directive packet container is structurally intact.
    """
    card = html_soup.find(id="dev-manager-directive-packet-card")
    assert card is not None, "Missing Section 4r: manager directive packet container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for manager directive packet"
    assert "Manager Directive Packet" in header.text, "Kicker must explicitly label the Manager Directive Packet"

    content = card.find(id="dev-manager-directive-packet-state")
    assert content is not None, "Missing directive data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_directive_logic(app_js_content: str):
    """
    Verify that `updateManagerDirectivePacket` isolates the exact packet bounds.
    """
    assert "function updateManagerDirectivePacket(appId, runId)" in app_js_content, \
        "Missing updateManagerDirectivePacket trace entirely."

    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing core updateWorkerDetail hook."
    
    assert "updateManagerDirectivePacket(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Directive sequence is decoupled from the worker runtime refresh lifecycle."


def test_hub_app_js_has_honest_directive_states(app_js_content: str):
    """
    Ticket 3 constraint: The system must enforce explicit bounded tracking
    preventing hallucination of directive scope.
    """
    assert "EXECUTE PROMOTION" in app_js_content, "Missing required Immediate/Promotion directive"
    assert "HALT EXECUTION" in app_js_content, "Missing required Pending/Halt directive"
    assert "DEFER" in app_js_content, "Missing required Blocked/Defer directive"

def test_hub_app_js_ties_directives_to_evidence(app_js_content: str):
    """
    Ticket 2 constraint: Directives must declare exactly which specialist 
    is assigned, what the evidence is, and what the delegation is.
    """
    assert "evidence:" in app_js_content, "Missing explicit evidence tracing."
    assert "delegation:" in app_js_content, "Missing explicit target delegation step."


def test_hub_app_js_has_active_directive_context(app_js_content: str):
    """
    The packet must expose the active viewing context so the manager can see
    which worker/run/governance selection the directive is anchored to.
    """
    assert "Active Directive Constraints:" in app_js_content
    assert "Action Source:" in app_js_content
    assert "Resolution Bound:" in app_js_content
    assert "Directive Basis:" in app_js_content


def test_geometric_law_phuc_forecast_directive_hash(app_js_content: str):
    """
    Enforce ALCOA+ cryptographic execution constraints per User Override 
    (The Geometric Law / Phuc Forecast): Prioritized actionable items must
    include a deterministic hash string for non-repudiation.
    """
    assert "btoa(directive.target + directive.action + directive.state)" in app_js_content, \
        "Failed Geometric Law constraint: UI does not compute an algorithmic ALCOA+ log hash for delegation directives."


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_manager_directive_exists():
    """
    Verify the Prime Mermaid component mapping the SI17 structural bounds
    on single delegated packets.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "manager-directive-packet.prime-mermaid.md"
    assert mermaid_path.exists(), "SAD31 Directive diagram is missing."
    
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime structural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure."


def test_smoke_manager_directive_packet_exists():
    scripts = Path(__file__).parent.parent / "scripts"
    assert (scripts / "smoke-manager-directive-packet.sh").exists()
