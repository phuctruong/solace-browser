$ python -m pytest tests/test_solace_cli.py -v
============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-8.4.1, pluggy-1.6.0 -- /usr/bin/python
cachedir: .pytest_cache
rootdir: /home/phuc/projects/solace-browser
collecting ... collected 7 items

tests/test_solace_cli.py::test_cli_status_calls_correct_endpoint FAILED
tests/test_solace_cli.py::test_cli_apps_list FAILED
tests/test_solace_cli.py::test_cli_sessions_list FAILED
tests/test_solace_cli.py::test_cli_evidence_tail FAILED
tests/test_solace_cli.py::test_cli_tunnel_status FAILED
tests/test_solace_cli.py::test_cli_no_token_exits_cleanly FAILED
tests/test_solace_cli.py::test_cli_session_rules_list FAILED

=================================== FAILURES ===================================
E   ModuleNotFoundError: No module named 'solace_cli'

RED gate verdict: PASS
Reason: the new test file failed before implementation because `solace_cli.py` did not exist yet.
