import os

def test_hub_app_js_has_specialist_destination_approval_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC91 Next-Step Destination Approval Truth" in content
    assert "Next-Step Destination Approval Truth:" in content
    assert "Nested Source Request ID:" in content
    assert "Nested Source Assignment ID:" in content
    assert "Nested Source Role:" in content
    assert "Nested Source Run ID:" in content
    assert "Nested Target Assignment ID:" in content
    assert "Dispatched Nested Specialist:" in content
    assert "Nested Approval Run ID:" in content
    assert "var nestedTargetApproval = approvals.find(function(item) { return item.assignment_id === nestedLaunchAction.targetAssignmentId; }) || null;" in content
    assert "nestedTargetApproval.status === 'approved'" in content
    assert "Exact launched-workflow destination approval tracked" in content
    assert "Fallback destination approval tracked" in content
    assert "Awaiting destination approval truth" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-destination-approval-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-destination-approval-truth.prime-mermaid.md")
