Command:

```bash
pytest -q tests/test_notifications_sse.py
```

Observed RED output before implementation:

```text
FFFFFFFFFFFFF                                                            [100%]
=================================== FAILURES ===================================
_____________________ test_notify_post_queues_notification _____________________
E       assert 404 == 200

__________________________ test_notify_requires_auth ___________________________
E       assert 404 == 401

__________________________ test_notify_requires_type ___________________________
E       assert 404 == 400

_________________________ test_notify_requires_message _________________________
E       assert 404 == 400

_______________________ test_yinyang_status_shows_queue ________________________
E       assert 404 == 200

______________________ test_yinyang_status_requires_auth _______________________
E       assert 404 == 401

_______________________ test_mark_read_updates_read_flag _______________________
E       assert 404 == 200

________________________ test_mark_nonexistent_read_404 ________________________
E       AssertionError: assert 'not found' == 'notification not found'

____________________ test_sse_endpoint_returns_event_stream ____________________
E       assert 404 == 200

________________________ test_sse_requires_token_param _________________________
E       AssertionError: assert 404 == 401

_____________________________ test_js_file_exists ______________________________
E       AssertionError: assert False

_____________________________ test_css_file_exists _____________________________
E       AssertionError: assert False

________________________________ test_js_no_cdn ________________________________
E       FileNotFoundError: [Errno 2] No such file or directory: '/home/phuc/projects/solace-browser/web/js/notifications-sse.js'

=========================== short test summary info ============================
FAILED tests/test_notifications_sse.py::test_notify_post_queues_notification
FAILED tests/test_notifications_sse.py::test_notify_requires_auth
FAILED tests/test_notifications_sse.py::test_notify_requires_type
FAILED tests/test_notifications_sse.py::test_notify_requires_message
FAILED tests/test_notifications_sse.py::test_yinyang_status_shows_queue
FAILED tests/test_notifications_sse.py::test_yinyang_status_requires_auth
FAILED tests/test_notifications_sse.py::test_mark_read_updates_read_flag
FAILED tests/test_notifications_sse.py::test_mark_nonexistent_read_404
FAILED tests/test_notifications_sse.py::test_sse_endpoint_returns_event_stream
FAILED tests/test_notifications_sse.py::test_sse_requires_token_param
FAILED tests/test_notifications_sse.py::test_js_file_exists
FAILED tests/test_notifications_sse.py::test_css_file_exists
FAILED tests/test_notifications_sse.py::test_js_no_cdn
13 failed in 5.52s
```
