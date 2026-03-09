# RED GATE

- NORTHSTAR: Evidence by Default + User Trust
- Command: `pytest -q tests/test_schedule_viewer.py`
- Result: RED confirmed before validation could reach assertions.
- Sandbox note: this environment blocks local socket creation, so the module fixture failed at `build_server(...)` with `PermissionError: [Errno 1] Operation not permitted`.
- Proof log: `/tmp/solace-hub-coder/20260309-task058/repro_red.log`
