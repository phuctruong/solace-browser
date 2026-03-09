============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-8.4.1, pluggy-1.6.0 -- /usr/bin/python
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /home/phuc/projects/solace-browser
plugins: cov-7.0.0, playwright-0.7.2, xdist-3.8.0, anyio-4.12.0, timeout-2.4.0, django-4.12.0, base-url-2.1.0, mock-0.11.0, asyncio-1.3.0, typeguard-4.4.4, hypothesis-6.151.6
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 7 items

tests/test_solace_cli.py::test_cli_status_calls_correct_endpoint PASSED  [ 14%]
tests/test_solace_cli.py::test_cli_apps_list PASSED                      [ 28%]
tests/test_solace_cli.py::test_cli_sessions_list PASSED                  [ 42%]
tests/test_solace_cli.py::test_cli_evidence_tail PASSED                  [ 57%]
tests/test_solace_cli.py::test_cli_tunnel_status PASSED                  [ 71%]
tests/test_solace_cli.py::test_cli_no_token_exits_cleanly PASSED         [ 85%]
tests/test_solace_cli.py::test_cli_session_rules_list PASSED             [100%]

============================== 7 passed in 0.11s ===============================
