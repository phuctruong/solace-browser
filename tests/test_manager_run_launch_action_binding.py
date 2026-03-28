import os
import re

def test_hub_app_js_has_launch_action_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert JS API parameter logic override exists
    assert "window.__solaceLaunchWorkflowNextStep = function(sourceAssignmentId, targetRole, targetAssignmentId)" in content
    assert "saveWorkflowLaunchBinding(reqId, targetAssignment.id, appId, runId);" in content
    
    # Assert capturing hook is set inside route mapper
    assert "window.__solaceLastWorkflowRouteAction = {" in content
    assert "window.__solaceLastWorkflowLaunchAction = {" in content
    
    # Assert buttons are mapped into UI bindings condition
    assert "Next-Step Route State:<" in content
    assert "window.__solaceLaunchWorkflowNextStep(\\'" in content
    assert "Launch Executable (" in content
    assert "Next-Step Launch State:" in content
    assert "Launch Basis: <code>Workflow-bound routed assignment launch via real runtime run path (SAC76)</code>" in content
    
    # Check basis explicitly validates SAC76 states
    assert '(SAC70/71/72/73/74/75/76)' in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-launch-action-binding.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-launch-action-workflow.prime-mermaid.md")
