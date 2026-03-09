# Red Gate

- Metric advanced: Safe Autonomy + Evidence by Default.
- Command: `python -m pytest tests/test_preview_cooldown_signoff.py -q`
- Result before patch: FAIL.
- Failure witness: the original route proof depended on opening a local listener in this sandbox and failed during fixture setup with a socket permission error, so the suite never reached the workflow assertions.
- Red evidence file: `/tmp/solace-hub-coder/20260309-task057/repro_red.log`
