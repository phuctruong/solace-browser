import os

def test_hub_app_js_has_specialist_evidence_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC81 Fetch Specialist Execution Evidence" in content
    assert "Next-Step Specialist Execution Evidence Truth:" in content
    assert "Source Request ID:" in content
    assert "Target Assignment ID:" in content
    assert "Launched Role:" in content
    assert "Launched Run ID:" in content
    assert "Exact launched-workflow execution evidence tracked" in content
    assert "Fallback execution evidence tracked" in content
    assert "Awaiting specialist execution evidence" in content
    assert "Events exist for the launched next-step run" in content
    assert "request, assignment, role, and run remain aligned" in content
    assert "document.getElementById('dev-evidence-fetch-target')" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-evidence-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-evidence-truth.prime-mermaid.md")
