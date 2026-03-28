import os

def test_hub_app_js_has_inbox_packet_preview_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert JS CSS mappings bounds are mapped unconditionally
    assert "SAC78 Inbox Packet Preview Box" in content
    assert "dev-active-workflow-payload-preview" in content
    assert "Packet Preview Basis: exact launched next-step run artifact" in content
    assert "Packet Preview Basis: fallback packet preview; current workflow binding is not exact launched-run truth" in content
    
    # Assert decoupling from SAC72 legacy mutually exclusive strings
    # We guarantee there is a dedicated payload parsing promise natively
    assert "SAC78 Fetch Inbox Packet Preview" in content
    assert "fetchArtifactText(boundRun.appId, boundRun.runId, 'payload.json')" in content
    assert "buildMissingState('payload.json', 'missing for launched next-step run')" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-inbox-packet-preview.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-inbox-packet-preview.prime-mermaid.md")
