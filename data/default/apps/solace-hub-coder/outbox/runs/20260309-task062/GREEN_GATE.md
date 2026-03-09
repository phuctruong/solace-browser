# GREEN Gate

- Focused command: `pytest -q tests/test_app_onboarding.py`
- Focused result: `12 passed in 4.38s`
- Regression command: `pytest -q tests/test_app_onboarding.py tests/test_app_store.py`
- Regression result: `22 passed in 4.44s`
- Syntax gate: `python -m py_compile yinyang_server.py`
- Syntax result: `exit 0`
