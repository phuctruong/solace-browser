# RED Gate

Command: `pytest -q tests/test_marketplace.py`

Captured before the marketplace implementation landed.

```text
FFFFFFF                                                                  [100%]
=================================== FAILURES ===================================
_____________________ test_marketplace_apps_requires_auth ______________________
E       assert 404 == 401

______________________ test_marketplace_apps_returns_list ______________________
E       assert 404 == 200

_____________________ test_marketplace_install_bad_app_id ______________________
E       AssertionError: assert 'not found' == 'app not found'

_______________ test_marketplace_install_downloads_session_rules _______________
E       assert 404 == 200

___________________ test_marketplace_uninstall_removes_file ____________________
E       assert 404 == 200

_________________________ test_marketplace_categories __________________________
E       assert 404 == 200

__________________ test_marketplace_serves_cache_when_offline __________________
E       assert 404 == 200

=========================== short test summary info ============================
FAILED tests/test_marketplace.py::test_marketplace_apps_requires_auth
FAILED tests/test_marketplace.py::test_marketplace_apps_returns_list
FAILED tests/test_marketplace.py::test_marketplace_install_bad_app_id
FAILED tests/test_marketplace.py::test_marketplace_install_downloads_session_rules
FAILED tests/test_marketplace.py::test_marketplace_uninstall_removes_file
FAILED tests/test_marketplace.py::test_marketplace_categories
FAILED tests/test_marketplace.py::test_marketplace_serves_cache_when_offline
7 failed in 3.68s
```
