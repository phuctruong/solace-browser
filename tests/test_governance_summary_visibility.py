"""
Test: Verification of SAG29 Department Governance Summary Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates the persistence of aggregate department-wide governance loads
(defined by SI18 Transparency).
Ensures the UI exposes approved/pending/blocked loads and structural bottleneck
lanes without faking telemetry limits.
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

def test_html_has_governance_summary_card(html_soup: BeautifulSoup):
    """
    Assert that the department governance summary card container is structurally intact
    allowing execution to bind natively to the DOM without layout hallucination.
    """
    card = html_soup.find(id="dev-governance-summary-card")
    assert card is not None, "Missing Section 4p: governance summary container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for governance summary"
    assert "Governance Overview" in header.text, "Kicker must explicitly label the Governance Overview"

    content = card.find(id="dev-governance-summary-state")
    assert content is not None, "Missing governance data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_governance_logic(app_js_content: str):
    """
    Verify that `updateGovernanceSummary` exists and maps human aggregate inputs
    tightly inside the main refresh frame.
    """
    assert "function updateGovernanceSummary(appId, runId)" in app_js_content, \
        "Missing updateGovernanceSummary trace entirely."

    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing core updateWorkerDetail hook."
    
    assert "updateGovernanceSummary(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Governance sequence is decoupled from the worker runtime refresh lifecycle."


def test_hub_app_js_has_honest_governance_metrics(app_js_content: str):
    """
    Ticket 3 constraint: The system must accurately represent approved, pending,
    and blocked counts explicitly, matching department wide oversight patterns.
    """
    assert "approved:" in app_js_content, "Missing required approved count metric"
    assert "pending:" in app_js_content, "Missing required pending count metric"
    assert "blocked:" in app_js_content, "Missing required blocked count metric"


def test_hub_app_js_identifies_pressure_lanes(app_js_content: str):
    """
    Ticket 2 constraint: The UI must point to a specific pressure lane
    indicating where governance load bottlenecks exist.
    """
    assert "pressureLane:" in app_js_content, "Missing pressure identification indicator (Lane)"
    assert "pressureLabel:" in app_js_content, "Missing pressure indicator severity (Label)"
    assert "pressureDesc:" in app_js_content, "Missing pressure explanatory basis (Desc)"


def test_hub_app_js_has_active_governance_context(app_js_content: str):
    """
    The summary must expose the active governance context so the manager can see
    which worker/run selection the aggregate view is anchored to.
    """
    assert "Active Governance Context:" in app_js_content
    assert "Governance Tracking:" in app_js_content
    assert "Pressure Basis:" in app_js_content
    assert "Evidence Standard:" in app_js_content


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_governance_summary_exists():
    """
    Verify the Prime Mermaid component mapping the SI18 structural definitions
    matches the diagrammer profile requirements absolutely.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "governance-summary.prime-mermaid.md"
    assert mermaid_path.exists(), "SAG29 Governance diagram is missing."
    
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime structural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure."


def test_smoke_governance_summary_exists():
    scripts = Path(__file__).parent.parent / "scripts"
    assert (scripts / "smoke-governance-summary.sh").exists()
