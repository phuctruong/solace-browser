import os
import re

def test_hub_app_js_has_preview_binding_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert preview container exists
    assert 'id="dev-active-workflow-preview"' in content
    
    # Assert explicit runtime wrapper pulls are invoked
    assert "fetchArtifactText(" in content
    assert "buildReportPreview(" in content
    assert "buildPayloadPreview(" in content
    
    # Check basis explicitly validates SAC72-SAC74 states
    assert '(SAC70/71/72/73/74)' in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-preview-binding.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-preview-workflow.prime-mermaid.md")
