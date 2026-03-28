import os
import re

def test_hub_app_js_has_route_action_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert JS API parameter logic override exists
    assert "window.__solaceRouteWorkflowNextStep = function(assignmentId, overrideTargetRole)" in content
    assert "var targetRole = overrideTargetRole;" in content
    assert "window.__solaceLastWorkflowRouteAction" in content
    assert "mutation = 'created'" in content
    assert "mutation = 'updated'" in content
    
    # Assert buttons are mapped into UI bindings condition
    assert "Route Workflow Next Step:<" in content
    assert "__solaceRouteWorkflowNextStep(\\'" in content
    assert "\\', \\'design\\')" in content
    assert "\\', \\'coder\\')" in content
    assert "\\', \\'qa\\')" in content
    assert "Next-Step Route State:" in content
    assert "Routing Basis: <code>Workflow-bound assignment " in content
    
    # Check basis explicitly validates SAC75 states
    assert '(SAC70/71/72/73/74/75)' in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-route-action-binding.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-route-action-workflow.prime-mermaid.md")
