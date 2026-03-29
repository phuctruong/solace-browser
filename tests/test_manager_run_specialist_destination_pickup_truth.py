import os

def test_hub_app_js_has_specialist_destination_pickup_truth_logic():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()

    assert "SAC88 Next-Step Destination Pickup Truth" in content
    assert "Next-Step Destination Pickup Truth:" in content
    assert "exactNestedLaunchTruth" in content
    assert "nestedEventsExist && exactNestedLaunchTruth" in content
    assert "Nested Source Request ID:" in content
    assert "Nested Source Assignment ID:" in content
    assert "Nested Source Role:" in content
    assert "Nested Source Run ID:" in content
    assert "Nested Target Assignment ID:" in content
    assert "Dispatched Nested Specialist:" in content
    assert "Nested Pickup Run ID:" in content
    assert "nestedLaunchAction.sourceRole === lastLaunchAction.targetRole" in content
    assert "nestedLaunchAction.sourceRunId === lastLaunchAction.runId" in content
    assert "nestedActualRun = (nestedRunData.runs || []).find" in content
    assert "nestedEventsExist = nestedActualRun ? nestedActualRun.events_exist : false" in content
    assert "Promise.all(runPromises).then(" in content
    assert "Exact launched-workflow destination pickup tracked" in content
    assert "Fallback destination pickup tracked" in content
    assert "Awaiting destination specialist pickup evidence" in content
    assert "request, source assignment, target assignment, role, and run remain aligned in the exact launched-workflow branch (SAC88)" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-manager-run-specialist-destination-pickup-truth.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/manager-run-specialist-destination-pickup-truth.prime-mermaid.md")
