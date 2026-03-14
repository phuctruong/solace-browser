# Diagram: 05-solace-runtime-architecture
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18888


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_dockerfile_exists():
    assert (REPO_ROOT / "Dockerfile.cloud-twin").exists()


def test_dockerfile_no_9222():
    assert "9222" not in _read("Dockerfile.cloud-twin")


def test_start_script_uses_xvfb():
    script_path = REPO_ROOT / "scripts" / "start-cloud-twin.sh"
    content = script_path.read_text(encoding="utf-8")
    assert script_path.exists()
    assert "Xvfb" in content
    assert "--headless" not in content
    assert "--cloud-twin" in content


def test_yinyang_server_cloud_twin_flag(monkeypatch):
    import yinyang_server as ys

    calls: list[dict] = []

    def fake_start_server(
        port: int,
        repo_root: str = ".",
        session_token_sha256: str = "",
        cloud_twin: bool = False,
    ) -> None:
        calls.append(
            {
                "port": port,
                "repo_root": repo_root,
                "token_sha256": session_token_sha256,
                "cloud_twin": cloud_twin,
            }
        )

    monkeypatch.setattr(ys, "start_server", fake_start_server)
    exit_code = ys.main(["--cloud-twin", "--port", str(TEST_PORT), str(REPO_ROOT)])
    assert exit_code == 0
    assert calls == [
        {
            "port": TEST_PORT,
            "repo_root": str(REPO_ROOT),
            "token_sha256": "",
            "cloud_twin": True,
        }
    ]
    assert ys._hub_integration_enabled(cloud_twin=True) is False


def test_health_endpoint_returns_mode(monkeypatch):
    import yinyang_server as ys

    monkeypatch.setenv("DISPLAY", ":99")
    payload = ys._health_payload(app_count=0, port=TEST_PORT, cloud_twin_mode=True)
    assert payload["status"] == "ok"
    assert payload["mode"] == "cloud_twin"
    assert payload["display"] == ":99"


def test_cloudbuild_yaml_exists():
    assert (REPO_ROOT / "cloudbuild-twin.yaml").exists()


def test_deploy_script_uses_new_image():
    content = _read("scripts/deploy-cloud-twin.sh")
    assert "solace-browser-twin:latest" in content
    assert "cloudbuild-twin.yaml" in content
