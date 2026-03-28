import os
import re

def test_hub_html_has_manager_routing_ui():
    path = "solace-hub/src/index.html"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
    
    assert 'id="dev-active-workflow-routing"' in content
    assert 'dev-route-role-select' in content
    assert 'Route to Design' in content
    assert 'Route to QA' in content
    assert '__solaceRouteActiveRequest()' in content
    assert 'dev-active-workflow-routes' in content

def test_hub_app_js_has_routing_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    # Request creation no longer triggers assignment POST
    saz_hook = content[content.find('window.__solaceCreateSac67Request'):]
    saz_hook_body = saz_hook[:saz_hook.find('};')]
    assert 'target_role: \'coder\'' not in saz_hook_body, "Request creation should no longer auto-create coder assignment"
        
    assert 'window.__solaceRouteActiveRequest' in content
    assert 'hydrateActiveWorkflowRoutes' in content
    assert 'target_role: targetRole' in content
    assert "method = 'PUT'" in content
    assert "method = 'POST'" in content
    assert "existing = assignments.find" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-assignment-routing.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-routing-workflow.prime-mermaid.md")
