# RED Gate — Task 048

Command:

```bash
pytest -q tests/test_cloud_twin.py
```

Output before implementation:

```text
FFFF.FF                                                                  [100%]
=================================== FAILURES ===================================
____________________ test_cloud_twin_status_not_configured _____________________

E       assert 404 == 200

___________________________ test_cloud_twin_set_url ____________________________

E       assert 404 == 200

______________________ test_cloud_twin_status_configured _______________________

E       assert 404 == 200

_______________________ test_cloud_twin_ping_unreachable _______________________

E       assert 404 == 200

____________________ test_session_new_cloud_target_no_twin _____________________

E       assert 201 == 503

__________________________ test_deploy_script_exists ___________________________

E       AssertionError: assert False

=========================== short test summary info ============================
FAILED tests/test_cloud_twin.py::test_cloud_twin_status_not_configured
FAILED tests/test_cloud_twin.py::test_cloud_twin_set_url
FAILED tests/test_cloud_twin.py::test_cloud_twin_status_configured
FAILED tests/test_cloud_twin.py::test_cloud_twin_ping_unreachable
FAILED tests/test_cloud_twin.py::test_session_new_cloud_target_no_twin
FAILED tests/test_cloud_twin.py::test_deploy_script_exists
6 failed, 1 passed in 0.63s
```
