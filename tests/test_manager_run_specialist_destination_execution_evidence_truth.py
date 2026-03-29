import os

def test_hub_app_js_has_specialist_destination_execution_evidence_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC89 Next-Step Destination Execution Evidence Truth" in content
    assert "Next-Step Destination Execution Evidence Truth:" in content
    assert "nestedLaunchMatchesCurrentBranch" in content
    assert "dev-nested-evidence-fetch-target" in content
    assert "nestedLaunchAction.targetAssignmentId === targetRouteAction.assignmentId" in content
    assert "nestedLaunchAction.targetRole === targetRouteAction.targetRole" in content
    assert "Nested Source Request ID:" in content
    assert "Nested Source Assignment ID:" in content
    assert "Nested Source Role:" in content
    assert "Nested Source Run ID:" in content
    assert "Nested Target Assignment ID:" in content
    assert "Dispatched Nested Specialist:" in content
    assert "Nested Evidence Run ID:" in content
    assert "fetchArtifactText(nestedLaunchAction.appId, nestedLaunchAction.runId, 'events.jsonl').then(function(res) {" in content
    assert "buildEventsPreview(res.text, nestedLaunchAction.appId, nestedLaunchAction.runId);" in content
    assert "Exact launched-workflow destination execution evidence tracked" in content
    assert "Fallback destination execution evidence tracked" in content
    assert "Awaiting destination execution evidence" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-destination-execution-evidence-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-destination-execution-evidence-truth.prime-mermaid.md")
