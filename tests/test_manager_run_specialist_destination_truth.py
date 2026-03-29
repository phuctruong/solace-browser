import os

def test_hub_app_js_has_specialist_destination_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC86 Next-Step Destination Truth" in content
    assert "Next-Step Destination Truth:" in content
    assert "Route Next-Step Destination:" in content
    assert "Source Request ID:" in content
    assert "Source Assignment ID:" in content
    assert "Source Role:" in content
    assert "Source Run ID:" in content
    assert "Destination Target Role:" in content
    assert "Destination Mutation Mode:" in content
    assert "targetRouteAction.sourceAssignmentId === lastLaunchAction.targetAssignmentId" in content
    assert "Launch Executable Destination (" in content
    assert "window.__solaceRouteWorkflowNextStep" in content
    assert "Exact launched-workflow destination branch tracked" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-destination-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-destination-truth.prime-mermaid.md")
