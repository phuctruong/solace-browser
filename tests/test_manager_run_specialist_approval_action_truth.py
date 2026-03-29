import os

def test_hub_app_js_has_specialist_approval_action_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC84 Generate Approval Actions" in content
    assert "Next-Step Approval Action:" in content
    assert "window.__solaceSignoffWorkflow(" in content
    assert "lastLaunchAction.targetAssignmentId" in content
    assert "Action Target Assignment ID:" in content
    assert "Action Target Role:" in content
    assert "Action Target Run ID:" in content
    assert "Approve Target" in content
    assert "Reject Target" in content
    assert "Approval action will " in content
    assert "request, assignment, role, and run remain aligned" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-approval-action-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-approval-action-truth.prime-mermaid.md")
