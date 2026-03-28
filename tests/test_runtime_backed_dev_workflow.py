import os

def test_hub_app_js_hits_runtime_api():
    path = "solace-hub/src/hub-app.js"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
    assert "get('/api/v1/backoffice/solace-dev-manager/assignments')" in content, "Must fetch assignments from runtime"
    assert "get('/api/v1/backoffice/solace-dev-manager/requests')" in content, "Must fetch requests from runtime"

def test_hub_app_js_removed_static_mocks():
    path = "solace-hub/src/hub-app.js"
    with open(path) as f:
        content = f.read()
    
    assert "runtime-backed dynamic API (SAC66)" in content, "Must expose runtime binding explicitly"
    assert "disconnected / fallback mock" in content, "Must gracefully fallback if runtime is offline"

def test_hub_app_js_binds_artifacts_and_approvals():
    path = "solace-hub/src/hub-app.js"
    with open(path) as f:
        content = f.read()
    assert "/api/v1/backoffice/solace-dev-manager/artifacts" in content, "Must fetch assignment-linked artifacts"
    assert "/api/v1/backoffice/solace-dev-manager/approvals" in content, "Must fetch assignment-linked approvals"
    assert "Back Office Approval" in content or "Approval State:" in content, "Must expose approval context in the workflow chain"

def test_seed_script_exists():
    path = "scripts/seed-saz66-runtime-binding.sh"
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
    assert "API_URL=\"http://localhost:8888/api/v1/backoffice/solace-dev-manager\"" in content
    assert "/requests" in content
    assert "/artifacts" in content
    assert "/approvals" in content

def test_smoke_script_exists():
    assert os.path.exists("scripts/smoke-runtime-backed-dev-workflow.sh")

def test_prime_mermaid_diagram_exists():
    assert os.path.exists("specs/solace-dev/diagrams/runtime-backed-dev-workflow.prime-mermaid.md")
