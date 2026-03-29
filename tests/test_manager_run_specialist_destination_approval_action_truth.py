import os

def test_hub_app_js_has_specialist_destination_approval_action_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC92 Next-Step Destination Approval Action Truth" in content
    assert "Target Assignment Destination Approval Action:" in content
    assert "Nested Source Request ID:" in content
    assert "Nested Source Assignment ID:" in content
    assert "Nested Source Role:" in content
    assert "Nested Source Run ID:" in content
    assert "Nested Target Assignment ID:" in content
    assert "Dispatched Nested Specialist:" in content
    assert "Nested Action Run ID:" in content
    assert "window.__solaceSignoffWorkflow" in content
    assert "nestedLaunchAction.targetAssignmentId" in content
    assert "!nestedTargetApproval || nestedTargetApproval.status === 'pending'" in content
    assert "Approval action will " in content
    assert "nested approval already resolved as " in content
    assert "exact launched-workflow destination approval action truth" in content
    assert "Awaiting destination approval truth" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-destination-approval-action-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-destination-approval-action-truth.prime-mermaid.md")
