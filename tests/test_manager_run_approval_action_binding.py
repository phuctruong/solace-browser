import os
import re

def test_hub_app_js_has_approval_action_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert JS API POST hook exists
    assert "window.__solaceSignoffWorkflow = function(assignmentId, existingId, status)" in content
    assert "fetch(url" in content
    assert "method = 'PUT'" in content
    assert "approver_role: 'manager'" in content
    
    # Assert buttons are mapped into UI bindings
    assert "onclick=\"window.__solaceSignoffWorkflow(" in content
    assert ">Approve<" in content
    assert ">Reject<" in content
    
    # Check basis explicitly validates SAC74-SAC75 states
    assert '(SAC70/71/72/73/74/75)' in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-approval-action-binding.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-approval-action-workflow.prime-mermaid.md")
