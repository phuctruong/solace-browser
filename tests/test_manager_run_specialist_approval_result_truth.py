import os

def test_hub_app_js_has_specialist_approval_result_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC85 Next-Step Approval Result Truth" in content
    assert "Next-Step Approval Mutation Result:" in content
    assert "window.__solaceLastWorkflowSignoffActionResult =" in content
    assert "lastSignoffResult.success" in content
    assert "Target approval successfully written" in content
    assert "Target approval write failed" in content
    assert "Result Target Role:" in content
    assert "Result Target Run ID:" in content
    assert "Exact launched-workflow approval result tracked" in content
    assert "Fallback approval result tracked" in content
    assert "request, assignment, role, and run remain aligned" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-approval-result-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-approval-result-truth.prime-mermaid.md")
