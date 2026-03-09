# GREEN GATE

## Targeted task tests

```text
============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-8.4.1, pluggy-1.6.0 -- /usr/bin/python
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /home/phuc/projects/solace-browser
plugins: cov-7.0.0, playwright-0.7.2, xdist-3.8.0, anyio-4.12.0, timeout-2.4.0, django-4.12.0, base-url-2.1.0, mock-0.11.0, asyncio-1.3.0, typeguard-4.4.4, hypothesis-6.151.6
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 7 items

tests/test_hub_tunnel_client.py::test_client_sends_pong_on_ping PASSED   [ 14%]
tests/test_hub_tunnel_client.py::test_client_proxies_get_request PASSED  [ 28%]
tests/test_hub_tunnel_client.py::test_client_proxies_post_request PASSED [ 42%]
tests/test_hub_tunnel_client.py::test_client_handles_disconnect_gracefully PASSED [ 57%]
tests/test_hub_tunnel_client.py::test_start_cloud_no_api_key_returns_400 PASSED [ 71%]
tests/test_hub_tunnel_client.py::test_cloud_status_inactive_by_default PASSED [ 85%]
tests/test_hub_tunnel_client.py::test_start_cloud_sets_active PASSED     [100%]

============================== 7 passed in 0.09s ===============================

```

## Regression summary

- Command: `python -m pytest tests/ -q --ignore=tests/browser/`
- Result: non-zero in this sandbox
- Cause: existing test fixtures attempt to bind localhost sockets, and the sandbox blocks socket creation with `PermissionError: [Errno 1] Operation not permitted`
- Impact: new task-specific tests are green; broader suite cannot complete in this environment

### First regression error snippet

```text
__________ ERROR at setup of TestHealthEndpoint.test_health_endpoint ___________

tmp_path_factory = TempPathFactory(_given_basetemp=None, _trace=<pluggy._tracing.TagTracerSub object at 0x776a8eb3aad0>, _basetemp=PosixPath('/tmp/pytest-of-phuc/pytest-318'), _retention_count=3, _retention_policy='all')
monkeypatch_module = None

    @pytest.fixture(scope="module")
    def server(tmp_path_factory, monkeypatch_module):
        tmp = tmp_path_factory.mktemp("solace")
        lock_path = tmp / "port.lock"
    
        # Patch the lock path before importing the module.
        import importlib
        import yinyang_server as ys
    
        original_lock = ys.PORT_LOCK_PATH
        ys.PORT_LOCK_PATH = lock_path
    
        token = ys.generate_token()
        t_hash = ys.token_hash(token)
        ys.write_port_lock(TEST_PORT, t_hash, 99999)
    
>       httpd = ys.build_server(TEST_PORT, str(REPO_ROOT))

tests/test_yinyang_instructions.py:49: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
yinyang_server.py:4197: in build_server
    server = http.server.ThreadingHTTPServer(("localhost", port), YinyangHandler)
/usr/lib/python3.10/socketserver.py:448: in __init__
    self.socket = socket.socket(self.address_family,
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <socket.socket fd=-1, family=AddressFamily.AF_UNSPEC, type=0, proto=0>
family = <AddressFamily.AF_INET: 2>, type = <SocketKind.SOCK_STREAM: 1>
proto = 0, fileno = None

    def __init__(self, family=-1, type=-1, proto=-1, fileno=None):
        # For user code address family and type values are IntEnum members, but
        # for the underlying _socket.socket they're just integers. The
        # constructor of _socket.socket converts the given argument to an
        # integer automatically.
```
