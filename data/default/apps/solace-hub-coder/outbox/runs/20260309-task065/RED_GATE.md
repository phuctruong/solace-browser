Command: python -m pytest tests/test_fun_packs.py -q
Exit code: 1

Initial RED run before implementation exposed the missing feature set:

- `FileNotFoundError` for `data/fun-packs/default-en.json`
- `AssertionError` for missing `web/fun-packs.html`
- Route tests could not start a live listener on `18888` in this sandbox: `PermissionError: [Errno 1] Operation not permitted`
- Summary: `4 failed, 8 errors in 1.40s`

Representative excerpt:

```text
FAILED tests/test_fun_packs.py::test_fun_packs_default_en_json_valid - FileNotFoundError
FAILED tests/test_fun_packs.py::test_fun_packs_default_en_has_20_jokes - FileNotFoundError
FAILED tests/test_fun_packs.py::test_fun_packs_html_exists - AssertionError
FAILED tests/test_fun_packs.py::test_fun_packs_html_no_cdn - FileNotFoundError
ERROR tests/test_fun_packs.py::test_fun_packs_list_returns_packs - PermissionError
ERROR tests/test_fun_packs.py::test_fun_packs_requires_auth - PermissionError
ERROR tests/test_fun_packs.py::test_fun_packs_active_returns_full_pack - PermissionError
ERROR tests/test_fun_packs.py::test_fun_packs_random_joke_is_string - PermissionError
ERROR tests/test_fun_packs.py::test_fun_packs_random_fact_is_string - PermissionError
ERROR tests/test_fun_packs.py::test_fun_packs_greeting_morning - PermissionError
ERROR tests/test_fun_packs.py::test_fun_packs_activate_sets_active - PermissionError
ERROR tests/test_fun_packs.py::test_fun_packs_unknown_pack_404 - PermissionError
```
