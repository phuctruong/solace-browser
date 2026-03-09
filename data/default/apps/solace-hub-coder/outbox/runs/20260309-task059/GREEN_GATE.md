# GREEN_GATE.md — Task 059
# Command: cd /home/phuc/projects/solace-browser && python -m pytest tests/test_community_recipes.py -v

============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-8.4.1
collected 23 items

tests/test_community_recipes.py::test_recipe_list_returns_installed_flag PASSED
tests/test_community_recipes.py::test_install_requires_scope_confirmation PASSED
tests/test_community_recipes.py::test_install_not_silent PASSED
tests/test_community_recipes.py::test_run_creates_preview_not_direct_execute PASSED
tests/test_community_recipes.py::test_fork_creates_local_copy PASSED
tests/test_community_recipes.py::test_my_library_returns_source_field PASSED
tests/test_community_recipes.py::test_recipe_hit_rate_uses_decimal PASSED
tests/test_community_recipes.py::test_recipes_html_no_cdn_dependencies PASSED
tests/test_community_recipes.py::test_recipes_css_no_hardcoded_hex PASSED
tests/test_community_recipes.py::test_recipes_html_exists PASSED
tests/test_community_recipes.py::test_recipes_js_exists PASSED
tests/test_community_recipes.py::test_recipes_css_exists PASSED
tests/test_community_recipes.py::test_recipes_html_served_via_server PASSED
tests/test_community_recipes.py::test_recipes_js_served_via_server PASSED
tests/test_community_recipes.py::test_recipes_css_served_via_server PASSED
tests/test_community_recipes.py::test_community_recipe_create PASSED
tests/test_community_recipes.py::test_install_requires_auth PASSED
tests/test_community_recipes.py::test_run_requires_auth PASSED
tests/test_community_recipes.py::test_fork_requires_auth PASSED
tests/test_community_recipes.py::test_fork_missing_name PASSED
tests/test_community_recipes.py::test_recipes_js_no_silent_install PASSED
tests/test_community_recipes.py::test_community_recipes_filter_by_category PASSED
tests/test_community_recipes.py::test_community_recipes_sort_by_best_hit_rate PASSED

============================== 23 passed in 9.26s ==============================

## Full suite (tests/ --ignore=tests/browser/)
4 failed (PRE-EXISTING before this task), 762 passed, 8 skipped

Pre-existing failures (confirmed by stash check):
  - tests/test_preview_cooldown_signoff.py::test_reject_seals_evidence_with_reason
  - tests/test_preview_cooldown_signoff.py::test_pending_list_shows_cooldown_remaining
  - tests/test_schedule_viewer.py::TestScheduleViewerCancel::test_schedule_cancel_removes_from_queue
  - tests/test_schedule_viewer.py::TestScheduleViewerQueue::test_schedule_queue_returns_pending_only

## Kill Checks — ALL CLEAN
- grep "9222" web/recipes.html web/js/recipes.js → EMPTY
- grep -i "companion app" → EMPTY
- grep "except Exception" yinyang_server.py → EMPTY
- grep -E "bootstrap|tailwind|jquery|cdn\." web/recipes.html → EMPTY
- grep "autoInstall\|silentInstall" web/js/recipes.js → EMPTY
