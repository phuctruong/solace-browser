# RED Gate

- NORTHSTAR metric advanced: Evidence by Default
- Command: `pytest -q tests/test_prime_wiki_snapshots.py`
- Exit code: `1`

```text
F.......                                                                 [100%]
=================================== FAILURES ===================================
________________________ test_snapshot_compresses_html _________________________

prime_wiki_server = {'base_url': 'http://localhost:43185', 'prime_wiki_root': PosixPath('/tmp/pytest-of-phuc/pytest-742/test_snapshot_comp...i'), 'settings_path': PosixPath('/tmp/pytest-of-phuc/pytest-742/test_snapshot_compresses_html0/.solace/settings.json')}

    def test_snapshot_compresses_html(prime_wiki_server):
        html = "<html><head><title>Inbox</title></head><body>" + ("<div>Hello world</div>" * 80) + "</body></html>"
        status, created = _request_json(
            prime_wiki_server,
            "/api/v1/prime-wiki/snapshot",
            method="POST",
            payload=_snapshot_payload("https://mail.google.com/mail/u/0/#inbox", html),
        )

        assert status == 201
>       assert created["rtc_verified"] is True
E       KeyError: 'rtc_verified'

tests/test_prime_wiki_snapshots.py:116: KeyError
=========================== short test summary info ============================
FAILED tests/test_prime_wiki_snapshots.py::test_snapshot_compresses_html - KeyError: 'rtc_verified'
1 failed, 7 passed in 3.05s
```
