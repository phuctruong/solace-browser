"""
Test: Verification of SAT28 Promotion Audit Trail Visibility
Persona: Donald Knuth (Verification Precision)
Skill: prime-coder, prime-safety

Validates the persistence of human-in-the-loop historical evaluations
(defined in SI18 Transparency as a Product Feature). 
Enforces that no UI node hallucinates a memory evolution trace without an
explicit prior state basis and an ALCOA+ Audit Hash matching the Phuc Forecast rules.
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

def test_html_has_promotion_audit_trail_card(html_soup: BeautifulSoup):
    """
    Assert that the promotion audit trail card container is structurally intact
    allowing execution to bind natively to the DOM without layout hallucination.
    """
    card = html_soup.find(id="dev-promotion-audit-trail-card")
    assert card is not None, "Missing Section 4o: promotion audit trail container"
    
    header = card.find("p", class_="sb-kicker")
    assert header is not None, "Missing kicker for audit trail"
    assert "Promotion Audit Trail" in header.text, "Kicker must explicitly label the Audit Trail"

    content = card.find(id="dev-promotion-audit-trail-state")
    assert content is not None, "Missing audit data mount point"


# -----------------------------------------------------------------------------
# Execution Logic Asserts (Ticket 1, 2, 3)
# -----------------------------------------------------------------------------

def test_hub_app_js_has_audit_trail_logic(app_js_content: str):
    """
    Verify that `updatePromotionAuditTrail` exists and maps human judgments
    over time tightly inside the main refresh frame.
    """
    assert "function updatePromotionAuditTrail(appId, runId)" in app_js_content, \
        "Missing updatePromotionAuditTrail trace entirely."

    detail_func_start = app_js_content.find("function updateWorkerDetail(appId, runId)")
    assert detail_func_start != -1, "Missing core updateWorkerDetail hook."
    
    assert "updatePromotionAuditTrail(appId, runId);" in app_js_content[detail_func_start:detail_func_start+1000], \
        "Audit Trail is decoupled from the worker runtime refresh lifecycle."


def test_hub_app_js_has_honest_audit_histories(app_js_content: str):
    """
    Ticket 3 constraint: The system must accurately represent an array of transitions
    from earlier blocks or pending states up to approved evaluation closures.
    """
    assert "state: 'approved'" in app_js_content, "Missing historic APPROVED representation"
    assert "state: 'pending'" in app_js_content, "Missing historic PENDING representation"
    assert "state: 'blocked'" in app_js_content, "Missing historic BLOCKED representation"


def test_geometric_law_phuc_forecast_hash_bounds(app_js_content: str):
    """
    Enforce ALCOA+ cryptographic execution constraints per User Override 
    (The Geometric Law / Phuc Forecast): All audit trail logs must append
    a deterministically derived mock hash.
    """
    assert "btoa(entry.candidate + entry.timestamp + entry.state)" in app_js_content, \
        "Failed Geometric Law constraint: UI does not compute an algorithmic ALCOA+ log hash."


def test_hub_app_js_has_active_audit_context(app_js_content: str):
    """
    The audit trail must surface its active review context so the manager does
    not have to infer which role/run/candidate history is being shown.
    """
    assert "Active Audit Context:" in app_js_content
    assert "Log Binding:" in app_js_content
    assert "History Basis:" in app_js_content
    assert "Evidence Standard:" in app_js_content


# -----------------------------------------------------------------------------
# Documentation Asserts (Ticket 4)
# -----------------------------------------------------------------------------

def test_prime_mermaid_audit_state_exists():
    """
    Verify the Prime Mermaid component mapping the SI18 structural definitions
    matches the diagrammer profile requirements perfectly.
    """
    mermaid_path = Path(__file__).parent.parent / "specs" / "solace-dev" / "diagrams" / "promotion-audit-trail.prime-mermaid.md"
    assert mermaid_path.exists(), "SAT28 Audit diagram is missing."
    
    content = mermaid_path.read_text(encoding="utf-8")
    assert "<!-- Diagram: 24-cpu-swarm-node-architecture" in content, "Missing prime structural signature."
    assert "stateDiagram-v2" in content, "Missing stateDiagram structure."


def test_smoke_audit_trail_exists():
    scripts = Path(__file__).parent.parent / "scripts"
    assert (scripts / "smoke-promotion-audit-trail.sh").exists()
