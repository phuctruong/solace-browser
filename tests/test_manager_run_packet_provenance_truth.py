import os

def test_hub_app_js_has_packet_provenance_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert JS constraints maps handoff arrays unambiguously natively
    assert "Next-Step Packet Provenance & Handoff Truth:" in content
    assert "Source Assignment ID:" in content
    assert "Target Assignment ID:" in content
    assert "Source Request ID:" in content
    assert "Launched Role:" in content
    assert "Launched Run ID:" in content
    
    # Assert honest exact-vs-fallback provenance states
    assert "Exact launched-workflow handoff tracked" in content
    assert "Fallback handoff tracked" in content
    assert "exact workflow-bound branch (SAC79)" in content
    assert "fallen back away from exact launched-workflow truth (SAC79)" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-packet-provenance-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-packet-provenance-truth.prime-mermaid.md")
