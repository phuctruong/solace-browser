import os

def test_hub_app_js_has_specialist_pickup_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC80 Output" in content
    assert "Next-Step Specialist Pickup Truth:" in content
    assert "Dispatched Specialist:" in content
    assert "Pickup Run ID:" in content
    assert "Exact launched-workflow pickup tracked" in content
    assert "Fallback pickup tracked" in content
    assert "Awaiting specialist pickup evidence" in content
    assert "Events exist for the launched next-step run" in content
    assert "request, assignment, role, and run remain aligned" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-pickup-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-pickup-truth.prime-mermaid.md")
