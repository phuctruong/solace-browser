# RED GATE

## Step 1 — baseline before writing tests

```text
============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-8.4.1, pluggy-1.6.0 -- /usr/bin/python
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /home/phuc/projects/solace-browser
plugins: cov-7.0.0, playwright-0.7.2, xdist-3.8.0, anyio-4.12.0, timeout-2.4.0, django-4.12.0, base-url-2.1.0, mock-0.11.0, asyncio-1.3.0, typeguard-4.4.4, hypothesis-6.151.6
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... ERROR: file or directory not found: tests/test_hub_tunnel_client.py

collected 0 items

============================ no tests ran in 0.07s =============================

```

## Step 2 — tests written first, still RED before implementation

```text
============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-8.4.1, pluggy-1.6.0 -- /usr/bin/python
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /home/phuc/projects/solace-browser
plugins: cov-7.0.0, playwright-0.7.2, xdist-3.8.0, anyio-4.12.0, timeout-2.4.0, django-4.12.0, base-url-2.1.0, mock-0.11.0, asyncio-1.3.0, typeguard-4.4.4, hypothesis-6.151.6
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 7 items

tests/test_hub_tunnel_client.py::test_client_sends_pong_on_ping FAILED   [ 14%]
tests/test_hub_tunnel_client.py::test_client_proxies_get_request FAILED  [ 28%]
tests/test_hub_tunnel_client.py::test_client_proxies_post_request FAILED [ 42%]
tests/test_hub_tunnel_client.py::test_client_handles_disconnect_gracefully FAILED [ 57%]
tests/test_hub_tunnel_client.py::test_start_cloud_no_api_key_returns_400 ERROR [ 71%]
tests/test_hub_tunnel_client.py::test_cloud_status_inactive_by_default ERROR [ 85%]
tests/test_hub_tunnel_client.py::test_start_cloud_sets_active ERROR      [100%]

==================================== ERRORS ====================================
__________ ERROR at setup of test_start_cloud_no_api_key_returns_400 ___________

tmp_path_factory = TempPathFactory(_given_basetemp=None, _trace=<pluggy._tracing.TagTracerSub object at 0x7ecb6f65ea70>, _basetemp=None, _retention_count=3, _retention_policy='all')

    @pytest.fixture(scope="module")
    def auth_server(tmp_path_factory):
>       load_hub_tunnel_client()

tests/test_hub_tunnel_client.py:77: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_hub_tunnel_client.py:23: in load_hub_tunnel_client
    return importlib.import_module("hub_tunnel_client")
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

name = 'hub_tunnel_client', import_ = <function _gcd_import at 0x7ecb70f67400>

>   ???
E   ModuleNotFoundError: No module named 'hub_tunnel_client'

<frozen importlib._bootstrap>:1004: ModuleNotFoundError
___________ ERROR at setup of test_cloud_status_inactive_by_default ____________

tmp_path_factory = TempPathFactory(_given_basetemp=None, _trace=<pluggy._tracing.TagTracerSub object at 0x7ecb6f65ea70>, _basetemp=None, _retention_count=3, _retention_policy='all')

    @pytest.fixture(scope="module")
    def auth_server(tmp_path_factory):
>       load_hub_tunnel_client()

tests/test_hub_tunnel_client.py:77: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_hub_tunnel_client.py:23: in load_hub_tunnel_client
    return importlib.import_module("hub_tunnel_client")
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

name = 'hub_tunnel_client', import_ = <function _gcd_import at 0x7ecb70f67400>

>   ???
E   ModuleNotFoundError: No module named 'hub_tunnel_client'

<frozen importlib._bootstrap>:1004: ModuleNotFoundError
________________ ERROR at setup of test_start_cloud_sets_active ________________

tmp_path_factory = TempPathFactory(_given_basetemp=None, _trace=<pluggy._tracing.TagTracerSub object at 0x7ecb6f65ea70>, _basetemp=None, _retention_count=3, _retention_policy='all')

    @pytest.fixture(scope="module")
    def auth_server(tmp_path_factory):
>       load_hub_tunnel_client()

tests/test_hub_tunnel_client.py:77: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_hub_tunnel_client.py:23: in load_hub_tunnel_client
    return importlib.import_module("hub_tunnel_client")
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

name = 'hub_tunnel_client', import_ = <function _gcd_import at 0x7ecb70f67400>

>   ???
E   ModuleNotFoundError: No module named 'hub_tunnel_client'

<frozen importlib._bootstrap>:1004: ModuleNotFoundError
=================================== FAILURES ===================================
________________________ test_client_sends_pong_on_ping ________________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7ecb6ddd9810>

    @pytest.mark.asyncio
    async def test_client_sends_pong_on_ping(monkeypatch):
>       hub = load_hub_tunnel_client()

tests/test_hub_tunnel_client.py:134: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_hub_tunnel_client.py:23: in load_hub_tunnel_client
    return importlib.import_module("hub_tunnel_client")
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

name = 'hub_tunnel_client', import_ = <function _gcd_import at 0x7ecb70f67400>

>   ???
E   ModuleNotFoundError: No module named 'hub_tunnel_client'

<frozen importlib._bootstrap>:1004: ModuleNotFoundError
_______________________ test_client_proxies_get_request ________________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7ecb6df86ec0>

    @pytest.mark.asyncio
    async def test_client_proxies_get_request(monkeypatch):
>       hub = load_hub_tunnel_client()

tests/test_hub_tunnel_client.py:147: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_hub_tunnel_client.py:23: in load_hub_tunnel_client
    return importlib.import_module("hub_tunnel_client")
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

name = 'hub_tunnel_client', import_ = <function _gcd_import at 0x7ecb70f67400>

>   ???
E   ModuleNotFoundError: No module named 'hub_tunnel_client'

<frozen importlib._bootstrap>:1004: ModuleNotFoundError
_______________________ test_client_proxies_post_request _______________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7ecb6de1f790>

    @pytest.mark.asyncio
    async def test_client_proxies_post_request(monkeypatch):
>       hub = load_hub_tunnel_client()

tests/test_hub_tunnel_client.py:165: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_hub_tunnel_client.py:23: in load_hub_tunnel_client
    return importlib.import_module("hub_tunnel_client")
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

name = 'hub_tunnel_client', import_ = <function _gcd_import at 0x7ecb70f67400>

>   ???
E   ModuleNotFoundError: No module named 'hub_tunnel_client'

<frozen importlib._bootstrap>:1004: ModuleNotFoundError
__________________ test_client_handles_disconnect_gracefully ___________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7ecb6df79d80>

    @pytest.mark.asyncio
    async def test_client_handles_disconnect_gracefully(monkeypatch):
>       hub = load_hub_tunnel_client()

tests/test_hub_tunnel_client.py:186: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_hub_tunnel_client.py:23: in load_hub_tunnel_client
    return importlib.import_module("hub_tunnel_client")
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

name = 'hub_tunnel_client', import_ = <function _gcd_import at 0x7ecb70f67400>

>   ???
E   ModuleNotFoundError: No module named 'hub_tunnel_client'

<frozen importlib._bootstrap>:1004: ModuleNotFoundError
=========================== short test summary info ============================
FAILED tests/test_hub_tunnel_client.py::test_client_sends_pong_on_ping - Modu...
FAILED tests/test_hub_tunnel_client.py::test_client_proxies_get_request - Mod...
FAILED tests/test_hub_tunnel_client.py::test_client_proxies_post_request - Mo...
FAILED tests/test_hub_tunnel_client.py::test_client_handles_disconnect_gracefully
ERROR tests/test_hub_tunnel_client.py::test_start_cloud_no_api_key_returns_400
ERROR tests/test_hub_tunnel_client.py::test_cloud_status_inactive_by_default
ERROR tests/test_hub_tunnel_client.py::test_start_cloud_sets_active - ModuleN...
========================= 4 failed, 3 errors in 0.14s ==========================

```
