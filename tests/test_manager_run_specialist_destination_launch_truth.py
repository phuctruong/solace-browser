import os

def test_hub_app_js_has_specialist_destination_launch_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC87 Next-Step Destination Launch Truth" in content
    assert "Next-Step Destination Launch Truth:" in content
    assert "nestedLaunchAction.sourceAssignmentId === lastLaunchAction.targetAssignmentId" in content
    assert "nestedLaunchAction.targetAssignmentId === targetRouteAction.assignmentId" in content
    assert "nestedLaunchAction.targetRole === targetRouteAction.targetRole" in content
    assert "window.__solaceLastWorkflowNestedLaunchAction =" in content
    assert "sourceRole: window.__solaceLastWorkflowLaunchAction.targetRole" in content
    assert "sourceRunId: window.__solaceLastWorkflowLaunchAction.runId" in content
    assert "Nested Source Request ID:" in content
    assert "Nested Source Assignment ID:" in content
    assert "Nested Source Role:" in content
    assert "Nested Source Run ID:" in content
    assert "Nested Target Assignment ID:" in content
    assert "Nested Launched Role:" in content
    assert "Nested Launched Run ID:" in content
    assert "Exact launched-workflow destination launch tracked" in content
    assert "Fallback destination launch tracked" in content
    assert "Awaiting destination launch truth" in content
    assert "Workflow launched the routed destination assignment while request, source assignment, target assignment, role, and run remained aligned in the exact launched-workflow branch (SAC87)" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-destination-launch-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-destination-launch-truth.prime-mermaid.md")
