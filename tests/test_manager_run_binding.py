import os
import re

def test_hub_html_has_manager_result_binding_ui():
    path = "solace-hub/src/index.html"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
    
    assert 'id="dev-active-workflow-result"' in content
    assert 'Active Launched Execution Context' in content
    assert 'id="dev-active-workflow-result-content"' in content

def test_hub_app_js_has_result_binding_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    assert 'function hydrateActiveWorkflowResult()' in content
    assert "var reqId = window.__solaceActiveRequestId;" in content
    assert 'var launchBinding = loadWorkflowLaunchBinding();' in content
    assert 'var selectedRun = loadSelectedRun();' in content
    assert 'get(\'/api/v1/backoffice/solace-dev-manager/assignments\')' in content
    assert 'Run execution explicitly bound to workflow launch session state (SAC70)' in content
    assert 'Fallback to selected run only; not durable workflow launch proof' in content
    assert 'saveWorkflowLaunchBinding' in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-binding.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-binding-workflow.prime-mermaid.md")
