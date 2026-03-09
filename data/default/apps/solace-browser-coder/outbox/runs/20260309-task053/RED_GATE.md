FFF.F..F                                                                 [100%]
=================================== FAILURES ===================================
___________________ test_by_domain_gmail_returns_gmail_apps ____________________

E       TypeError: _apps_for_domain() takes 2 positional arguments but 4 were given

___________________ test_by_domain_free_user_hides_pro_apps ____________________

E       TypeError: _apps_for_domain() takes 2 positional arguments but 4 were given

_________________ test_by_domain_unknown_domain_returns_empty __________________

E       TypeError: _apps_for_domain() takes 2 positional arguments but 4 were given

____________________ test_wildcard_domain_matches_subdomain ____________________

E       TypeError: _apps_for_domain() takes 2 positional arguments but 4 were given

______________________ test_by_domain_includes_store_apps ______________________

E       TypeError: _apps_for_domain() takes 2 positional arguments but 4 were given

=========================== short test summary info ============================
FAILED tests/test_domain_app_linking.py::test_by_domain_gmail_returns_gmail_apps
FAILED tests/test_domain_app_linking.py::test_by_domain_free_user_hides_pro_apps
FAILED tests/test_domain_app_linking.py::test_by_domain_unknown_domain_returns_empty
FAILED tests/test_domain_app_linking.py::test_wildcard_domain_matches_subdomain
FAILED tests/test_domain_app_linking.py::test_by_domain_includes_store_apps
5 failed, 3 passed in 0.19s
