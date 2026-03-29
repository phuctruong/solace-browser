import os

def test_hub_app_js_has_specialist_destination_output_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC90 Next-Step Destination Output Truth" in content
    assert "Next-Step Destination Output Truth:" in content
    assert "nestedLaunchMatchesCurrentBranch" in content
    assert "dev-nested-output-fetch-target" in content
    assert "nestedLaunchAction.targetAssignmentId === targetRouteAction.assignmentId" in content
    assert "nestedLaunchAction.targetRole === targetRouteAction.targetRole" in content
    assert "Nested Source Request ID:" in content
    assert "Nested Source Assignment ID:" in content
    assert "Nested Source Role:" in content
    assert "Nested Source Run ID:" in content
    assert "Nested Target Assignment ID:" in content
    assert "Dispatched Nested Specialist:" in content
    assert "Nested Output Run ID:" in content
    assert "fetchArtifactText(nestedLaunchAction.appId, nestedLaunchAction.runId, 'report.html').then(function(res) {" in content
    assert "buildReportPreview(res.text, nestedLaunchAction.appId, nestedLaunchAction.runId);" in content
    assert "var nestedReportExists = nestedActualRun ? nestedActualRun.report_exists : false;" in content
    assert "Exact launched-workflow destination output tracked" in content
    assert "Fallback destination output tracked" in content
    assert "Awaiting destination output truth" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-destination-output-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-destination-output-truth.prime-mermaid.md")
