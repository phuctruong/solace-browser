# Focused Patch Diff

```diff
*** Update File: tests/test_prime_wiki_snapshots.py
@@
-import gzip
+import subprocess
@@
 PZWEB_BIN = pathlib.Path("/home/phuc/projects/pzip/native/pzip_web_cpp/build/pzweb")
+PZLOG_BIN = pathlib.Path("/home/phuc/projects/pzip/native/pzip_logs_cpp/build/pzlog")
@@
-def _pzip_decompress_html(content_pzip_b64: str) -> str:
+def _pzip_decompress_content(content_pzip_b64: str, codec: str) -> str:
+    if codec == "pzweb":
+        binary_path = PZWEB_BIN
+    else:
+        assert codec == "pzlog"
+        binary_path = PZLOG_BIN
@@
-    assert "content_gzip_b64" not in detail
+    assert created["rtc_verified"] is True
+    assert created["codec"] == "pzweb"
+    assert "content_pzip_b64" not in detail
@@
-    restored = gzip.decompress(base64.b64decode(content["content_gzip_b64"])).decode()
+    assert content["rtc_verified"] is True
+    assert content["codec"] == "pzweb"
+    restored = _pzip_decompress_content(content["content_pzip_b64"], content["codec"])
@@
+def test_snapshot_allows_missing_content_html(...):
+    assert created["sha256"] == hashlib.sha256(b"").hexdigest()
+    assert created["codec"] == "pzlog"
+    assert _pzip_decompress_content(content["content_pzip_b64"], content["codec"]) == ""
@@
-    snapshot_dir = prime_wiki_server["prime_wiki_root"] / created["url_hash"][:16]
+    snapshot_dir = prime_wiki_server["prime_wiki_root"] / created["url_hash"]

*** Update File: yinyang_server.py
@@
-  GET  /api/v1/prime-wiki/snapshot/{id}/content → lazy-load gzip content payload
+  GET  /api/v1/prime-wiki/snapshot/{id}/content → lazy-load PZip content payload
@@
-import gzip
@@
-PRIME_WIKI_PZIP_BINARY = Path("/home/phuc/projects/pzip/native/pzip_web_cpp/build/pzweb")
-PRIME_WIKI_PZIP_CODEC = "pzweb"
+PRIME_WIKI_PZIP_WEB_BINARY = Path("/home/phuc/projects/pzip/native/pzip_web_cpp/build/pzweb")
+PRIME_WIKI_PZIP_WEB_CODEC = "pzweb"
+PRIME_WIKI_PZIP_EMPTY_BINARY = Path("/home/phuc/projects/pzip/native/pzip_logs_cpp/build/pzlog")
+PRIME_WIKI_PZIP_EMPTY_CODEC = "pzlog"
@@
+class PZipCompressionError(Exception):
+    ...
+
+class PZipRTCError(PZipCompressionError):
+    ...
@@
-def _prime_wiki_storage_dir(url_hash: str) -> Path:
-    return PRIME_WIKI_ROOT / url_hash[:16]
+def _prime_wiki_storage_dir(url_hash: str) -> Path:
+    return PRIME_WIKI_ROOT / url_hash
@@
-def _run_prime_wiki_pzip(mode: str, payload: bytes) -> bytes:
+def _prime_wiki_pzip_binary_and_codec(raw_bytes: bytes) -> tuple[Path, str]:
+    if raw_bytes:
+        return PRIME_WIKI_PZIP_WEB_BINARY, PRIME_WIKI_PZIP_WEB_CODEC
+    return PRIME_WIKI_PZIP_EMPTY_BINARY, PRIME_WIKI_PZIP_EMPTY_CODEC
+
+def _run_prime_wiki_pzip(binary_path: Path, mode: str, payload: bytes) -> bytes:
@@
-def _compress_prime_wiki_content(content: str) -> tuple[str, str, int, int, float]:
-    compressed_bytes = gzip.compress(raw_bytes)
+def _compress_prime_wiki_content(content: str) -> tuple[str, str, int, int, float, str, bool]:
+    binary_path, codec = _prime_wiki_pzip_binary_and_codec(raw_bytes)
+    compressed_bytes = _run_prime_wiki_pzip(binary_path, "compress", raw_bytes)
+    restored_bytes = _run_prime_wiki_pzip(binary_path, "decompress", compressed_bytes)
+    if restored_bytes != raw_bytes:
+        raise PZipRTCError(...)
@@
-    public_record.pop("content_gzip_b64", None)
+    public_record.pop("content_gzip_b64", None)
+    public_record.pop("content_pzip_b64", None)
@@
-        "content_gzip_b64": compressed_b64,
+        "content_pzip_b64": compressed_b64,
+        "codec": codec,
+        "rtc_verified": rtc_verified,
@@
-        snapshot_record = _prime_wiki_snapshot_record(...)
+        try:
+            snapshot_record = _prime_wiki_snapshot_record(...)
+        except PZipRTCError:
+            self._send_json({"error": "snapshot rtc verification failed"}, 500)
+            return
+        except PZipCompressionError:
+            self._send_json({"error": "failed to compress snapshot"}, 500)
+            return
@@
-                "compression_ratio": snapshot_record["compression_ratio"],
+                "compression_ratio": snapshot_record["compression_ratio"],
+                "codec": snapshot_record["codec"],
+                "rtc_verified": snapshot_record["rtc_verified"],
@@
-                "content_gzip_b64": snapshot_record.get("content_gzip_b64", ""),
+                "content_pzip_b64": snapshot_record.get("content_pzip_b64", ""),
+                "codec": snapshot_record.get("codec", ""),
+                "rtc_verified": snapshot_record.get("rtc_verified", False),
```
