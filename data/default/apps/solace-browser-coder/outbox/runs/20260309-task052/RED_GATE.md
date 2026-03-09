# RED_GATE

Command:
```bash
pytest -q tests/test_cloud_twin_docker.py
```

Result:
```text
FFFFFFF                                                                  [100%]
=================================== FAILURES ===================================
FAILED tests/test_cloud_twin_docker.py::test_dockerfile_exists
FAILED tests/test_cloud_twin_docker.py::test_dockerfile_no_9222
FAILED tests/test_cloud_twin_docker.py::test_start_script_uses_xvfb
FAILED tests/test_cloud_twin_docker.py::test_yinyang_server_cloud_twin_flag
FAILED tests/test_cloud_twin_docker.py::test_health_endpoint_returns_mode
FAILED tests/test_cloud_twin_docker.py::test_cloudbuild_yaml_exists
FAILED tests/test_cloud_twin_docker.py::test_deploy_script_uses_new_image
7 failed in 0.14s
```

Key failing assertions:
- `Dockerfile.cloud-twin` missing
- `scripts/start-cloud-twin.sh` missing
- `cloudbuild-twin.yaml` missing
- `yinyang_server.main(...)` missing
- `build_server(..., cloud_twin=True)` unsupported
- deploy script still pointed at the old image
