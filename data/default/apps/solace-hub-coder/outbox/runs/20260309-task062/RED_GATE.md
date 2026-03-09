# RED Gate

- NORTHSTAR metric: `USER_ACTIVATION` + `TIME_TO_VALUE`
- Command: `pytest -q tests/test_app_onboarding.py`
- Exit code: `1`

```text
..FFF.F..F..
=================================== FAILURES ===================================
test_activate_requires_all_required_fields
test_activate_returns_activated_state
test_activate_stores_config_encrypted
test_setup_requirements_has_config_fields
test_state_classes_are_4_valid_values

5 failed, 7 passed in 4.61s
```
