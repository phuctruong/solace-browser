Validation commands:

```bash
pytest -q tests/test_notifications_sse.py
pytest -q tests/test_yinyang_instructions.py -k 'notifications_list_empty or notifications_unread_count or notifications_mark_all_read_requires_auth or notifications_mark_all_read or notifications_unread_filter or notifications_limit_param or notifications_mark_read'
python -m py_compile yinyang_server.py
```

Observed GREEN output:

```text
.............                                                            [100%]
13 passed in 5.49s

.......                                                                  [100%]
7 passed, 324 deselected in 0.76s

(py_compile exited 0 with no output)
```
