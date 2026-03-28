import os

def test_hub_app_js_has_inbox_packet_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
  
    # Assert launched-run packet logic exists
    assert "payloadExists" in content
    assert "Next-Step Inbox Packet State:" in content
    assert "Packet Role:" in content
    assert "Packet Assignment ID:" in content
    
    # Assert packet view is tied to the launched workflow context
    assert "window.__solaceLastWorkflowLaunchAction" in content
    assert "/artifact/payload.json" in content
    assert "Workflow-bound launched assignment packet via exact launched run artifact (SAC77)" in content
    assert "Workflow-bound launched assignment selected, but payload artifact missing for launched run (SAC77)" in content
    
    # Assert visibility strings are mapped into UI bindings
    assert ">[↗ View Inbox Packet (payload.json)]<" in content
    assert ">[No Inbox Packet]<" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-inbox-packet-binding.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-inbox-packet-workflow.prime-mermaid.md")
