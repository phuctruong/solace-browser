import os
import re

def test_hub_app_js_has_artifact_binding_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert query exists inside explicit artifact binding block
    assert "get('/api/v1/apps/' + boundRun.appId + '/runs')" in content
    assert ">Run Artifacts:<" in content
    
    # Assert strict endpoint routing variables exist
    assert "/artifact/report.html" in content
    assert "/runs/' + boundRun.runId + '/events" in content
    assert "/artifact/events.jsonl" in content
    
    # Check basis explicitly validates SAC71 states
    assert '(SAC70/71/72)' in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-artifact-binding.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-artifact-workflow.prime-mermaid.md")
