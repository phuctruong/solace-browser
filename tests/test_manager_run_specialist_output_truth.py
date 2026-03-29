import os

def test_hub_app_js_has_specialist_output_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC82 Fetch Specialist Output Truth" in content
    assert "Next-Step Specialist Output Truth:" in content
    assert "Source Request ID:" in content
    assert "Target Assignment ID:" in content
    assert "Launched Role:" in content
    assert "Launched Run ID:" in content
    assert "Exact launched-workflow output tracked" in content
    assert "Fallback output tracked" in content
    assert "Awaiting specialist output truth" in content
    assert "Report output exists for the launched next-step run" in content
    assert "request, assignment, role, and run remain aligned" in content
    assert "document.getElementById('dev-output-fetch-target')" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-output-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-output-truth.prime-mermaid.md")
