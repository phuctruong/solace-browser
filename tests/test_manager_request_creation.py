import os

def test_hub_html_has_manager_creation_ui():
    path = "solace-hub/src/index.html"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
    
    assert 'id="dev-active-workflow-card"' in content
    assert '+ New Dev Request' in content
    assert 'dev-request-select' in content

def test_hub_app_js_has_request_bindings():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
        
    assert 'window.__solaceActiveRequestId' in content
    assert '__solaceCreateSac67Request' in content
    assert '__solaceSelectRequest' in content
    assert 'hydrateActiveWorkflowSelector' in content
    
    assert 'Explicitly selected request (SAC67)' in content
    assert "/api/v1/backoffice/solace-dev-manager/projects" in content
    assert "Self-hosted Solace Dev workspace target project" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-request-creation.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/request-selection-workflow.prime-mermaid.md")
