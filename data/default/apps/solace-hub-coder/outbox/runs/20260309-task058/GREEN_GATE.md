# GREEN GATE

- Syntax: `python -m py_compile yinyang_server.py` → PASS
- Static schedule gate: `pytest -q tests/test_schedule_viewer.py -k 'test_schedule_css_no_hardcoded_hex or test_schedule_html_no_cdn_dependencies or test_no_port_9222_in_schedule_files or test_no_companion_app_in_schedule_files or test_no_bare_except_in_schedule_handlers or test_schedule_js_auto_reject_not_approve_on_timeout or test_schedule_server_routes_registered or test_signoff_sheet_exists_in_html or test_four_views_in_html or test_bulk_approve_class_bc_banned'` → `10 passed`
- Direct backend exercise: no-socket script invoked `plan`, `list`, `queue`, `approve`, `calendar`, and `roi` handlers against a temporary runtime directory → PASS
- Proof logs:
  - `/tmp/solace-hub-coder/20260309-task058/green_static.log`
  - `/tmp/solace-hub-coder/20260309-task058/green_backend_direct.log`
