import os

def test_hub_app_js_has_specialist_approval_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC83 Next-Step Specialist Approval Truth" in content
    assert "Next-Step Specialist Approval Truth:" in content
    assert "approvals.find(function(item) { return item.assignment_id === lastLaunchAction.targetAssignmentId; })" in content
    assert "Source Request ID:" in content
    assert "Target Assignment ID:" in content
    assert "Launched Role:" in content
    assert "Launched Run ID:" in content
    assert "Exact launched-workflow approval branch tracked" in content
    assert "Fallback approval branch tracked" in content
    assert "pending workflow signoff" in content
    assert "Approval state is read for the launched target assignment" in content
    assert "request, assignment, role, and run remain aligned" in content
    assert "document.getElementById('dev-active-workflow-approval-preview')" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-approval-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-approval-truth.prime-mermaid.md")
