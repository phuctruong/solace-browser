import os
import re

def test_hub_app_js_has_approval_binding_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert query exists inside explicit artifact binding block
    assert "Promise.all([" in content
    assert "get('/api/v1/backoffice/solace-dev-manager/approvals')" in content
    assert ">Approval State:<" in content
    assert ">pending workflow signoff<" in content
    
    # Check basis explicitly validates SAC73 states
    assert '(SAC70/71/72/73)' in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-approval-binding.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-approval-workflow.prime-mermaid.md")
