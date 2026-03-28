import os
import re

def test_hub_html_has_manager_launch_ui():
    path = "solace-hub/src/index.html"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
    
    assert 'id="dev-active-workflow-launch"' in content
    assert '__solaceLaunchRoutedFlow()' in content
    assert '▶ Launch Routed Flow' in content
    assert 'dev-active-workflow-launch-output' in content

def test_hub_app_js_has_launch_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    assert 'window.__solaceLaunchRoutedFlow' in content
    assert "fetch(API + '/api/v1/apps/run/' + appId" in content
    assert 'Resolving active assignment for request ID' in content
    assert 'Requested launch role:' in content
    assert 'Executing mapped application: [' in content
    assert 'Runtime Route: POST /api/v1/apps/run/' in content
    assert "chosen = active.find" in content
    assert 'DEV_ROLES.find' in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-launch.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-launch-workflow.prime-mermaid.md")
