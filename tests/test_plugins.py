"""
Plugin Architecture Test Suite — OAuth3-governed plugin system.

Test classes:
  TestPluginManifest (8 tests)   — creation, validation, SHA256, required fields
  TestPluginRegistry (15 tests)  — register, unregister, query, SHA256 verify, scope gate
  TestPluginLifecycle (10 tests) — state transitions, forbidden transitions, evidence trail
  TestPluginSandbox (10 tests)   — scope isolation, resource limits, kill switch
  TestPluginSecurity (10 tests)  — rung enforcement, no scope escalation, no downgrade
  TestOAuth3Integration (7 tests)— token required, scope matching, revocation cascades

Total: 60+ tests
Rung: 641 (local correctness)

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_plugins.py -v -p no:httpbin
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from plugins.registry import (
    PluginManifest,
    PluginRegistry,
    PluginState,
    PluginLifecycleEvent,
    PluginRegistryError,
    ScopeGateError,
    RungEnforcementError,
    VersionDowngradeError,
    SHA256VerificationError,
    _parse_semver,
    _is_downgrade,
    _now_iso8601,
)
from plugins.sandbox import (
    PluginSandbox,
    SandboxViolationError,
    SandboxResourceLimitError,
    SandboxTerminatedError,
    compute_plugin_hash,
    DEFAULT_MAX_MEMORY_BYTES,
    DEFAULT_MAX_CPU_SECONDS,
    DEFAULT_MAX_OUTPUT_BYTES,
)

# OAuth3 components for integration tests
from oauth3.token import AgencyToken
from oauth3.enforcement import ScopeGate


# ===========================================================================
# Test helpers
# ===========================================================================

def make_content(text: str = "plugin body") -> bytes:
    """Create deterministic plugin content bytes."""
    return text.encode("utf-8")


def make_hash(content: bytes) -> str:
    """Compute 'sha256:<hex>' for given bytes."""
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def make_manifest(
    name: str = "test-plugin",
    version: str = "1.0.0",
    author: str = "test@example.com",
    description: str = "A test plugin.",
    required_scopes: tuple = ("gmail.read.inbox",),
    entry_point: str = "test_plugin.main:run",
    content: bytes = b"plugin body",
    rung: int = 641,
    belt: str = "white",
) -> PluginManifest:
    """Create a PluginManifest with sane defaults."""
    return PluginManifest(
        name=name,
        version=version,
        author=author,
        description=description,
        required_scopes=required_scopes,
        entry_point=entry_point,
        sha256_hash=make_hash(content),
        rung=rung,
        belt=belt,
    )


CONTENT = make_content()
MANIFEST = make_manifest(content=CONTENT)

LOW_SCOPE = "gmail.read.inbox"
HIGH_SCOPE = "gmail.send.email"
MULTI_SCOPES = ("gmail.read.inbox", "gmail.label.apply")


# ===========================================================================
# TestPluginManifest — 8 tests
# ===========================================================================

class TestPluginManifest:
    """Tests for PluginManifest creation and validation."""

    def test_create_valid_manifest(self):
        """A well-formed manifest is created without error."""
        m = make_manifest()
        assert m.name == "test-plugin"
        assert m.version == "1.0.0"
        assert m.author == "test@example.com"
        assert m.rung == 641
        assert m.belt == "white"

    def test_required_scopes_stored_as_tuple(self):
        """required_scopes is stored as a tuple (immutable)."""
        m = make_manifest(required_scopes=("gmail.read.inbox", "gmail.label.apply"))
        assert isinstance(m.required_scopes, tuple)
        assert len(m.required_scopes) == 2

    def test_sha256_hash_format_valid(self):
        """SHA256 hash must be 'sha256:<64 lowercase hex chars>'."""
        content = b"hello world"
        h = make_hash(content)
        m = make_manifest(content=content)
        assert m.sha256_hash.startswith("sha256:")
        assert len(m.sha256_hash) == 7 + 64  # 'sha256:' + 64 hex chars

    def test_invalid_sha256_no_prefix_raises(self):
        """sha256_hash without 'sha256:' prefix raises ValueError."""
        with pytest.raises(ValueError, match="sha256:"):
            PluginManifest(
                name="bad-hash",
                version="1.0.0",
                author="a@b.com",
                description="desc",
                required_scopes=("gmail.read.inbox",),
                entry_point="m:r",
                sha256_hash="badhash",
                rung=641,
                belt="white",
            )

    def test_invalid_semver_raises(self):
        """Non-SemVer version string raises ValueError."""
        with pytest.raises(ValueError, match="SemVer"):
            make_manifest(version="not-a-version")

    def test_invalid_belt_raises(self):
        """Unknown belt string raises ValueError."""
        with pytest.raises(ValueError, match="belt"):
            make_manifest(belt="purple")

    def test_manifest_hash_is_deterministic(self):
        """manifest_hash() returns same value for same manifest."""
        m1 = make_manifest()
        m2 = make_manifest()
        assert m1.manifest_hash() == m2.manifest_hash()
        assert m1.manifest_hash().startswith("sha256:")

    def test_from_dict_roundtrip(self):
        """to_dict() → from_dict() produces an identical manifest."""
        m = make_manifest(required_scopes=("gmail.read.inbox", "gmail.label.apply"))
        d = m.to_dict()
        m2 = PluginManifest.from_dict(d)
        assert m.name == m2.name
        assert m.version == m2.version
        assert m.sha256_hash == m2.sha256_hash
        assert m.required_scopes == m2.required_scopes

    def test_empty_name_raises(self):
        """Empty plugin name raises ValueError."""
        with pytest.raises(ValueError, match="name"):
            make_manifest(name="")

    def test_invalid_name_uppercase_raises(self):
        """Plugin name with uppercase raises ValueError."""
        with pytest.raises(ValueError, match="name"):
            make_manifest(name="MyPlugin")

    def test_empty_author_raises(self):
        """Empty author raises ValueError."""
        with pytest.raises(ValueError, match="author"):
            make_manifest(author="")

    def test_empty_description_raises(self):
        """Empty description raises ValueError."""
        with pytest.raises(ValueError, match="description"):
            make_manifest(description="")

    def test_rung_must_be_positive_int(self):
        """Non-positive rung raises ValueError."""
        with pytest.raises(ValueError, match="rung"):
            make_manifest(rung=0)
        with pytest.raises(ValueError, match="rung"):
            make_manifest(rung=-1)

    def test_from_dict_null_required_scopes_raises(self):
        """from_dict with null required_scopes raises ValueError (null != zero)."""
        d = make_manifest().to_dict()
        d["required_scopes"] = None
        with pytest.raises(ValueError, match="null"):
            PluginManifest.from_dict(d)


# ===========================================================================
# TestPluginRegistry — 15 tests
# ===========================================================================

class TestPluginRegistry:
    """Tests for PluginRegistry core operations."""

    @pytest.fixture
    def registry(self):
        return PluginRegistry(min_rung=641)

    @pytest.fixture
    def manifest(self):
        return make_manifest()

    @pytest.fixture
    def content(self):
        return CONTENT

    def test_register_discovers_and_verifies(self, registry, manifest, content):
        """Registering a plugin sets state to VERIFIED."""
        registry.register(manifest, content)
        assert registry.get_state(manifest.name) == PluginState.VERIFIED

    def test_registered_manifest_retrievable(self, registry, manifest, content):
        """Registered manifest can be retrieved by name."""
        registry.register(manifest, content)
        assert registry.get_manifest(manifest.name) == manifest

    def test_unregistered_plugin_returns_none_state(self, registry):
        """get_state returns None for unknown plugin."""
        assert registry.get_state("nonexistent") is None

    def test_unregistered_plugin_returns_none_manifest(self, registry):
        """get_manifest returns None for unknown plugin."""
        assert registry.get_manifest("nonexistent") is None

    def test_sha256_mismatch_raises(self, registry, manifest):
        """SHA256 mismatch raises SHA256VerificationError."""
        wrong_content = b"this is NOT the plugin content"
        with pytest.raises(SHA256VerificationError) as exc_info:
            registry.register(manifest, wrong_content)
        assert exc_info.value.plugin_name == manifest.name

    def test_scope_gate_blocks_activation_without_scopes(self, registry, manifest, content):
        """Plugin cannot activate without required scopes."""
        registry.register(manifest, content)
        registry.install(manifest.name)
        with pytest.raises(ScopeGateError) as exc_info:
            registry.activate(manifest.name, granted_scopes=[])
        assert "gmail.read.inbox" in exc_info.value.missing_scopes

    def test_scope_gate_allows_activation_with_scopes(self, registry, manifest, content):
        """Plugin activates when required scopes are granted."""
        registry.register(manifest, content)
        registry.install(manifest.name)
        event = registry.activate(manifest.name, granted_scopes=["gmail.read.inbox"])
        assert registry.get_state(manifest.name) == PluginState.ACTIVE

    def test_query_by_scope_returns_matching_plugins(self, registry):
        """query_by_scope finds plugins that require the scope."""
        c1 = b"plugin-a"
        c2 = b"plugin-b"
        m1 = make_manifest(name="plugin-a", required_scopes=("gmail.read.inbox",), content=c1)
        m2 = make_manifest(name="plugin-b", required_scopes=("gmail.send.email",), content=c2)
        registry.register(m1, c1)
        registry.register(m2, c2)
        results = registry.query_by_scope("gmail.read.inbox")
        names = [m.name for m in results]
        assert "plugin-a" in names
        assert "plugin-b" not in names

    def test_query_by_belt_returns_matching_plugins(self, registry):
        """query_by_belt finds plugins with the given belt."""
        c1 = b"orange-plugin"
        m1 = make_manifest(name="orange-plugin", belt="orange", content=c1)
        registry.register(m1, c1)
        results = registry.query_by_belt("orange")
        assert any(m.name == "orange-plugin" for m in results)
        results_white = registry.query_by_belt("white")
        assert all(m.name != "orange-plugin" for m in results_white)

    def test_query_by_rung_returns_matching_plugins(self, registry):
        """query_by_rung filters plugins by minimum rung."""
        c_low = b"low-rung-plugin"
        c_high = b"high-rung-plugin"
        m_low = make_manifest(name="low-rung-plugin", rung=641, content=c_low)
        m_high = make_manifest(name="high-rung-plugin", rung=274177, content=c_high)
        registry.register(m_low, c_low)
        registry.register(m_high, c_high)
        # Only high-rung plugin meets rung 274177
        high_results = registry.query_by_rung(274177)
        names = [m.name for m in high_results]
        assert "high-rung-plugin" in names
        assert "low-rung-plugin" not in names
        # Both meet rung 641
        all_results = registry.query_by_rung(641)
        all_names = [m.name for m in all_results]
        assert "low-rung-plugin" in all_names
        assert "high-rung-plugin" in all_names

    def test_list_all_returns_all_registered(self, registry):
        """list_all() returns all registered plugins."""
        c1, c2 = b"alpha", b"beta"
        registry.register(make_manifest(name="alpha", content=c1), c1)
        registry.register(make_manifest(name="beta", content=c2), c2)
        names = [m.name for m in registry.list_all()]
        assert "alpha" in names
        assert "beta" in names

    def test_list_active_returns_only_active_plugins(self, registry):
        """list_active() returns only ACTIVE plugins."""
        c = b"active-plugin"
        m = make_manifest(name="active-plugin", content=c)
        registry.register(m, c)
        assert not any(p.name == "active-plugin" for p in registry.list_active())
        registry.install(m.name)
        registry.activate(m.name, granted_scopes=["gmail.read.inbox"])
        assert any(p.name == "active-plugin" for p in registry.list_active())

    def test_uninstall_removes_plugin_from_registry(self, registry, manifest, content):
        """uninstall() removes plugin from registry."""
        registry.register(manifest, content)
        registry.uninstall(manifest.name)
        assert registry.get_manifest(manifest.name) is None
        assert registry.get_state(manifest.name) is None

    def test_verify_content_returns_true_for_matching_content(self, registry, manifest, content):
        """verify_content() returns True when content matches registered hash."""
        registry.register(manifest, content)
        assert registry.verify_content(manifest.name, content) is True

    def test_verify_content_raises_for_tampered_content(self, registry, manifest, content):
        """verify_content() raises SHA256VerificationError for tampered content."""
        registry.register(manifest, content)
        with pytest.raises(SHA256VerificationError):
            registry.verify_content(manifest.name, b"tampered content")

    def test_verify_content_returns_false_for_unregistered(self, registry):
        """verify_content() returns False for an unregistered plugin."""
        assert registry.verify_content("nonexistent", b"whatever") is False


# ===========================================================================
# TestPluginLifecycle — 10 tests
# ===========================================================================

class TestPluginLifecycle:
    """Tests for plugin lifecycle state machine and evidence trail."""

    @pytest.fixture
    def registry(self):
        return PluginRegistry(min_rung=641)

    @pytest.fixture
    def manifest_and_content(self):
        content = b"lifecycle-plugin"
        manifest = make_manifest(name="lifecycle-plugin", content=content)
        return manifest, content

    def test_full_lifecycle_sequence(self, registry, manifest_and_content):
        """DISCOVERED → VERIFIED → INSTALLED → ACTIVE → SUSPENDED → ACTIVE → UNINSTALLED."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        assert registry.get_state(manifest.name) == PluginState.VERIFIED
        registry.install(manifest.name)
        assert registry.get_state(manifest.name) == PluginState.INSTALLED
        registry.activate(manifest.name, granted_scopes=["gmail.read.inbox"])
        assert registry.get_state(manifest.name) == PluginState.ACTIVE
        registry.suspend(manifest.name, reason="maintenance")
        assert registry.get_state(manifest.name) == PluginState.SUSPENDED
        registry.resume(manifest.name, granted_scopes=["gmail.read.inbox"])
        assert registry.get_state(manifest.name) == PluginState.ACTIVE
        registry.uninstall(manifest.name)
        assert registry.get_state(manifest.name) is None  # removed

    def test_cannot_activate_from_verified_state(self, registry, manifest_and_content):
        """VERIFIED → ACTIVE is a forbidden transition (must go through INSTALLED)."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        # State is VERIFIED; ACTIVE is not allowed directly
        with pytest.raises(PluginRegistryError, match="not allowed"):
            registry.activate(manifest.name, granted_scopes=["gmail.read.inbox"])

    def test_cannot_install_from_active_state(self, registry, manifest_and_content):
        """ACTIVE → INSTALLED is a forbidden transition."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        registry.install(manifest.name)
        registry.activate(manifest.name, granted_scopes=["gmail.read.inbox"])
        with pytest.raises(PluginRegistryError, match="not allowed"):
            registry.install(manifest.name)

    def test_cannot_suspend_installed_plugin(self, registry, manifest_and_content):
        """INSTALLED → SUSPENDED is a forbidden transition."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        registry.install(manifest.name)
        with pytest.raises(PluginRegistryError, match="not allowed"):
            registry.suspend(manifest.name)

    def test_uninstall_from_any_active_state(self, registry, manifest_and_content):
        """Uninstall is allowed from ACTIVE state."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        registry.install(manifest.name)
        registry.activate(manifest.name, granted_scopes=["gmail.read.inbox"])
        registry.uninstall(manifest.name)
        assert registry.get_state(manifest.name) is None

    def test_uninstall_from_suspended_state(self, registry, manifest_and_content):
        """Uninstall is allowed from SUSPENDED state."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        registry.install(manifest.name)
        registry.activate(manifest.name, granted_scopes=["gmail.read.inbox"])
        registry.suspend(manifest.name)
        registry.uninstall(manifest.name)
        assert registry.get_state(manifest.name) is None

    def test_evidence_trail_records_all_events(self, registry, manifest_and_content):
        """Every lifecycle transition is recorded in the evidence trail."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        registry.install(manifest.name)
        registry.activate(manifest.name, granted_scopes=["gmail.read.inbox"])
        trail = registry.evidence_trail()
        to_states = [e.to_state for e in trail]
        assert PluginState.DISCOVERED in to_states
        assert PluginState.VERIFIED in to_states
        assert PluginState.INSTALLED in to_states
        assert PluginState.ACTIVE in to_states

    def test_evidence_trail_timestamps_are_iso8601(self, registry, manifest_and_content):
        """All evidence trail timestamps are ISO8601 UTC strings."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        trail = registry.evidence_trail()
        for event in trail:
            # Must parse without error
            ts = event.timestamp
            # ISO8601: contains 'T' and timezone info
            assert "T" in ts
            # Must be parseable
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            assert parsed.tzinfo is not None

    def test_evidence_trail_contains_manifest_hash(self, registry, manifest_and_content):
        """Evidence trail events include manifest SHA256 hash."""
        manifest, content = manifest_and_content
        registry.register(manifest, content)
        trail = registry.evidence_trail()
        for event in trail:
            assert event.manifest_hash.startswith("sha256:")

    def test_evidence_for_plugin_filters_correctly(self, registry, manifest_and_content):
        """evidence_for_plugin returns only events for that plugin."""
        manifest, content = manifest_and_content
        other_content = b"other-plugin"
        other_manifest = make_manifest(name="other-plugin", content=other_content)
        registry.register(manifest, content)
        registry.register(other_manifest, other_content)
        trail = registry.evidence_for_plugin(manifest.name)
        assert all(e.plugin_name == manifest.name for e in trail)


# ===========================================================================
# TestPluginSandbox — 10 tests
# ===========================================================================

class TestPluginSandbox:
    """Tests for PluginSandbox isolation and resource limits."""

    def test_allowed_api_call_succeeds(self):
        """call_api with a granted scope returns allowed result."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=["gmail.read.inbox"],
        )
        result = sandbox.call_api("gmail.read.inbox", {"limit": 5})
        assert result["status"] == "allowed"
        assert result["scope"] == "gmail.read.inbox"

    def test_denied_api_call_raises_violation(self):
        """call_api with an ungranted scope raises SandboxViolationError."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=["gmail.read.inbox"],
        )
        with pytest.raises(SandboxViolationError) as exc_info:
            sandbox.call_api("gmail.send.email")
        assert exc_info.value.plugin_name == "test"

    def test_denied_call_is_logged(self):
        """Denied API calls appear in the call log with allowed=False."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=[],
        )
        try:
            sandbox.call_api("gmail.read.inbox")
        except SandboxViolationError:
            pass
        denied = sandbox.denied_calls()
        assert len(denied) == 1
        assert denied[0].allowed is False

    def test_kill_switch_blocks_all_subsequent_calls(self):
        """After terminate(), all API calls raise SandboxTerminatedError."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=["gmail.read.inbox"],
        )
        sandbox.terminate()
        assert sandbox.is_terminated() is True
        with pytest.raises(SandboxTerminatedError):
            sandbox.call_api("gmail.read.inbox")

    def test_network_blocked_without_network_scope(self):
        """request_network raises SandboxViolationError for non-network scopes."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=["gmail.read.inbox"],
        )
        with pytest.raises(SandboxViolationError, match="network"):
            sandbox.request_network("https://example.com", "gmail.read.inbox")

    def test_output_limit_enforced(self):
        """write_output raises SandboxResourceLimitError when output limit exceeded."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=[],
            max_output_bytes=10,
        )
        # 10 bytes fits
        sandbox.write_output(b"0123456789")
        # 1 more byte exceeds limit
        with pytest.raises(SandboxResourceLimitError) as exc_info:
            sandbox.write_output(b"X")
        assert exc_info.value.resource == "output_bytes"

    def test_filesystem_blocked_without_data_dir(self):
        """read_file raises SandboxViolationError when data_dir is None."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=[],
            data_dir=None,
        )
        with pytest.raises(SandboxViolationError, match="data_dir"):
            sandbox.read_file("config.json")

    def test_path_traversal_blocked(self, tmp_path):
        """read_file blocks path traversal attacks (e.g. '../../../etc/passwd')."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=[],
            data_dir=tmp_path,
        )
        with pytest.raises(SandboxViolationError):
            sandbox.read_file("../../../etc/passwd")

    def test_call_log_records_allowed_calls(self):
        """Allowed API calls appear in call_log with allowed=True."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=["gmail.read.inbox", "gmail.label.apply"],
        )
        sandbox.call_api("gmail.read.inbox")
        sandbox.call_api("gmail.label.apply")
        allowed = sandbox.allowed_calls()
        assert len(allowed) == 2
        assert all(c.allowed for c in allowed)

    def test_context_manager_usage(self):
        """Sandbox can be used as context manager without error."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=["gmail.read.inbox"],
        )
        with sandbox:
            result = sandbox.call_api("gmail.read.inbox")
        assert result["status"] == "allowed"


# ===========================================================================
# TestPluginSecurity — 10 tests
# ===========================================================================

class TestPluginSecurity:
    """Tests for rung enforcement, scope escalation prevention, downgrade prevention."""

    @pytest.fixture
    def registry(self):
        return PluginRegistry(min_rung=641)

    def test_plugin_below_min_rung_rejected_at_registration(self, registry):
        """Plugin with rung < registry min_rung is rejected at register()."""
        content = b"low-rung"
        manifest = make_manifest(name="low-rung", rung=100, content=content)
        with pytest.raises(RungEnforcementError) as exc_info:
            registry.register(manifest, content)
        assert exc_info.value.plugin_rung == 100
        assert exc_info.value.required_rung == 641

    def test_plugin_at_min_rung_accepted(self, registry):
        """Plugin with rung == registry min_rung is accepted."""
        content = b"min-rung"
        manifest = make_manifest(name="min-rung", rung=641, content=content)
        registry.register(manifest, content)
        assert registry.get_state("min-rung") == PluginState.VERIFIED

    def test_activate_with_required_rung_gate(self, registry):
        """activate() with required_rung=274177 blocks plugin with rung=641."""
        content = b"low-rung-plugin"
        manifest = make_manifest(name="low-rung-plugin", rung=641, content=content)
        registry.register(manifest, content)
        registry.install(manifest.name)
        with pytest.raises(RungEnforcementError) as exc_info:
            registry.activate(
                manifest.name,
                granted_scopes=["gmail.read.inbox"],
                required_rung=274177,
            )
        assert exc_info.value.required_rung == 274177

    def test_high_rung_plugin_passes_required_rung_gate(self, registry):
        """Plugin with rung=274177 passes required_rung=274177 gate."""
        content = b"high-rung-plugin"
        manifest = make_manifest(name="high-rung-plugin", rung=274177, content=content)
        registry.register(manifest, content)
        registry.install(manifest.name)
        # Should not raise
        registry.activate(
            manifest.name,
            granted_scopes=["gmail.read.inbox"],
            required_rung=274177,
        )
        assert registry.get_state(manifest.name) == PluginState.ACTIVE

    def test_no_scope_escalation(self):
        """Plugin cannot escalate scopes beyond what's declared in its manifest."""
        content = b"escalator"
        manifest = make_manifest(
            name="escalator",
            required_scopes=("gmail.read.inbox",),
            content=content,
        )
        sandbox = PluginSandbox(
            plugin_name="escalator",
            granted_scopes=["gmail.read.inbox"],  # only read scope
        )
        # Cannot call send (not granted)
        with pytest.raises(SandboxViolationError):
            sandbox.call_api("gmail.send.email")

    def test_version_downgrade_blocked_by_default(self, registry):
        """Installing an older version is blocked without explicit approval."""
        content_v2 = b"plugin-v2.0.0"
        content_v1 = b"plugin-v1.0.0"
        m_v2 = make_manifest(name="versioned", version="2.0.0", content=content_v2)
        m_v1 = make_manifest(name="versioned", version="1.0.0", content=content_v1)
        registry.register(m_v2, content_v2)
        with pytest.raises(VersionDowngradeError) as exc_info:
            registry.register(m_v1, content_v1)
        assert exc_info.value.installed_version == "2.0.0"
        assert exc_info.value.attempted_version == "1.0.0"

    def test_version_upgrade_allowed(self, registry):
        """Installing a newer version replaces the old one."""
        content_v1 = b"plugin-v1.0.0-old"
        content_v2 = b"plugin-v2.0.0-new"
        m_v1 = make_manifest(name="upgradeable", version="1.0.0", content=content_v1)
        m_v2 = make_manifest(name="upgradeable", version="2.0.0", content=content_v2)
        registry.register(m_v1, content_v1)
        registry.register(m_v2, content_v2)
        assert registry.get_manifest("upgradeable").version == "2.0.0"

    def test_sha256_hash_must_be_provided_in_manifest(self):
        """PluginManifest validates sha256_hash format on construction."""
        with pytest.raises(ValueError, match="sha256"):
            PluginManifest(
                name="bad-hash",
                version="1.0.0",
                author="a@b.com",
                description="desc",
                required_scopes=("gmail.read.inbox",),
                entry_point="m:r",
                sha256_hash="INVALID",   # no 'sha256:' prefix
                rung=641,
                belt="white",
            )

    def test_plugin_with_wrong_content_cannot_be_registered(self, registry):
        """register() with content that doesn't match hash raises SHA256VerificationError."""
        content = b"real content"
        wrong_content = b"fake content"
        manifest = make_manifest(name="integrity-test", content=content)
        with pytest.raises(SHA256VerificationError):
            registry.register(manifest, wrong_content)

    def test_semver_validation_blocks_invalid_version(self):
        """PluginManifest rejects non-SemVer version strings."""
        for bad_version in ["1", "1.0", "v1.0.0", "latest", "1.0.0.0"]:
            with pytest.raises(ValueError, match="SemVer"):
                make_manifest(version=bad_version)


# ===========================================================================
# TestOAuth3Integration — 7 tests
# ===========================================================================

class TestOAuth3Integration:
    """Tests integrating plugin registry with OAuth3 token enforcement."""

    @pytest.fixture
    def registry(self):
        return PluginRegistry(min_rung=641)

    def _make_token(self, scopes: List[str], expired: bool = False, revoked: bool = False):
        """Create an AgencyToken for testing."""
        ttl = -1 if expired else 3600
        token = AgencyToken.create(
            issuer="https://www.solaceagi.com",
            subject="user:test@example.com",
            scopes=scopes,
            intent="plugin integration test",
            ttl_seconds=ttl,
        )
        if revoked:
            token = token.revoke()
        return token

    def test_plugin_activation_requires_token_scopes(self, registry):
        """Plugin cannot activate if token does not grant required scopes."""
        content = b"oauth3-plugin"
        manifest = make_manifest(
            name="oauth3-plugin",
            required_scopes=("gmail.read.inbox", "gmail.label.apply"),
            content=content,
        )
        registry.register(manifest, content)
        registry.install(manifest.name)

        # Token with only partial scopes
        token = self._make_token(["gmail.read.inbox"])
        granted = list(token.scopes)

        with pytest.raises(ScopeGateError) as exc_info:
            registry.activate(manifest.name, granted_scopes=granted)
        assert "gmail.label.apply" in exc_info.value.missing_scopes

    def test_plugin_activates_with_full_token_scopes(self, registry):
        """Plugin activates when token grants all required scopes."""
        content = b"full-scope-plugin"
        manifest = make_manifest(
            name="full-scope-plugin",
            required_scopes=("gmail.read.inbox", "gmail.label.apply"),
            content=content,
        )
        registry.register(manifest, content)
        registry.install(manifest.name)

        token = self._make_token(["gmail.read.inbox", "gmail.label.apply"])
        granted = list(token.scopes)
        registry.activate(manifest.name, granted_scopes=granted, actor=token.subject)
        assert registry.get_state(manifest.name) == PluginState.ACTIVE

    def test_revoked_token_scopes_suspend_plugin(self, registry):
        """When token is revoked, plugin should be suspended (caller responsibility)."""
        content = b"revoke-test"
        manifest = make_manifest(
            name="revoke-test",
            required_scopes=("gmail.read.inbox",),
            content=content,
        )
        registry.register(manifest, content)
        registry.install(manifest.name)

        token = self._make_token(["gmail.read.inbox"])
        registry.activate(manifest.name, granted_scopes=list(token.scopes))
        assert registry.get_state(manifest.name) == PluginState.ACTIVE

        # Revoke token → caller suspends plugin
        revoked_token = token.revoke()
        # G4: revocation gate
        gate = ScopeGate(revoked_token, ["gmail.read.inbox"])
        result = gate.check_all()
        assert not result.allowed
        assert result.error_code == "OAUTH3_TOKEN_REVOKED"

        # Caller should suspend the plugin
        registry.suspend(manifest.name, reason="Token revoked.")
        assert registry.get_state(manifest.name) == PluginState.SUSPENDED

    def test_expired_token_blocks_resume(self, registry):
        """Expired token should block plugin resume (validated via ScopeGate)."""
        content = b"expiry-test"
        manifest = make_manifest(
            name="expiry-test",
            required_scopes=("gmail.read.inbox",),
            content=content,
        )
        registry.register(manifest, content)
        registry.install(manifest.name)
        registry.activate(manifest.name, granted_scopes=["gmail.read.inbox"])
        registry.suspend(manifest.name)

        # Create expired token
        expired_token = self._make_token(["gmail.read.inbox"], expired=True)
        gate = ScopeGate(expired_token, ["gmail.read.inbox"])
        result = gate.check_all()
        assert not result.allowed
        assert result.error_code == "OAUTH3_TOKEN_EXPIRED"

    def test_scope_gate_four_gates_all_pass_for_valid_token(self):
        """ScopeGate.check_all() passes all four gates for a valid token."""
        token = self._make_token(["gmail.read.inbox"])
        gate = ScopeGate(token, ["gmail.read.inbox"])
        result = gate.check_all()
        assert result.allowed
        assert result.blocking_gate is None
        assert len(result.gate_results) == 4

    def test_plugin_sandbox_respects_token_scopes(self):
        """Sandbox only permits API calls matching token's granted scopes."""
        token = self._make_token(["gmail.read.inbox"])
        # Sandbox created with token's scopes
        sandbox = PluginSandbox(
            plugin_name="scope-test",
            granted_scopes=list(token.scopes),
        )
        # Allowed: scope in token
        result = sandbox.call_api("gmail.read.inbox")
        assert result["status"] == "allowed"
        # Blocked: scope NOT in token
        with pytest.raises(SandboxViolationError):
            sandbox.call_api("gmail.send.email")

    def test_revocation_cascades_to_sandbox(self):
        """After token revocation, sandbox should raise on new calls (kill switch)."""
        token = self._make_token(["gmail.read.inbox"])
        sandbox = PluginSandbox(
            plugin_name="revoke-cascade",
            granted_scopes=list(token.scopes),
        )
        # Pre-revocation: allowed
        sandbox.call_api("gmail.read.inbox")

        # Revoke token → system terminates sandbox
        revoked = token.revoke()
        gate = ScopeGate(revoked, ["gmail.read.inbox"])
        result = gate.check_all()
        assert not result.allowed
        # System kills sandbox
        sandbox.terminate()

        with pytest.raises(SandboxTerminatedError):
            sandbox.call_api("gmail.read.inbox")


# ===========================================================================
# Additional edge case tests
# ===========================================================================

class TestSemVer:
    """SemVer parsing and downgrade detection tests."""

    def test_parse_valid_semver(self):
        assert _parse_semver("1.2.3") == (1, 2, 3)
        assert _parse_semver("0.0.1") == (0, 0, 1)
        assert _parse_semver("10.20.30") == (10, 20, 30)

    def test_parse_semver_with_prerelease(self):
        assert _parse_semver("1.0.0-alpha") == (1, 0, 0)
        assert _parse_semver("2.1.0-beta.1") == (2, 1, 0)

    def test_parse_invalid_semver_raises(self):
        for bad in ["1", "1.0", "v1.0.0", "latest", "1.0.0.0"]:
            with pytest.raises(ValueError):
                _parse_semver(bad)

    def test_is_downgrade_detects_older_version(self):
        assert _is_downgrade("2.0.0", "1.9.9") is True
        assert _is_downgrade("1.1.0", "1.0.9") is True
        assert _is_downgrade("1.0.1", "1.0.0") is True

    def test_is_downgrade_allows_upgrade(self):
        assert _is_downgrade("1.0.0", "2.0.0") is False
        assert _is_downgrade("1.0.0", "1.0.1") is False
        assert _is_downgrade("1.0.0", "1.1.0") is False

    def test_is_downgrade_same_version_is_not_downgrade(self):
        assert _is_downgrade("1.0.0", "1.0.0") is False


class TestPluginSandboxWrite:
    """Tests for sandbox write operations and resource tracking."""

    def test_write_output_tracks_bytes(self):
        """write_output returns the total output buffer size."""
        sandbox = PluginSandbox(plugin_name="test", granted_scopes=[])
        total = sandbox.write_output(b"hello")
        assert total == 5
        total2 = sandbox.write_output(b" world")
        assert total2 == 11

    def test_get_output_returns_buffer_contents(self):
        """get_output() returns accumulated output."""
        sandbox = PluginSandbox(plugin_name="test", granted_scopes=[])
        sandbox.write_output(b"chunk1")
        sandbox.write_output(b"chunk2")
        assert sandbox.get_output() == b"chunk1chunk2"

    def test_write_file_and_read_file(self, tmp_path):
        """write_file() then read_file() round-trip succeeds."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=[],
            data_dir=tmp_path,
        )
        payload = json.dumps({"key": "value"}).encode("utf-8")
        bytes_written = sandbox.write_file("data.json", payload)
        assert bytes_written == len(payload)
        read_back = sandbox.read_file("data.json")
        assert read_back == payload

    def test_memory_limit_enforced_on_write_file(self, tmp_path):
        """write_file raises SandboxResourceLimitError when memory limit exceeded."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=[],
            data_dir=tmp_path,
            max_memory_bytes=10,
        )
        with pytest.raises(SandboxResourceLimitError) as exc_info:
            sandbox.write_file("big.bin", b"x" * 100)
        assert exc_info.value.resource == "memory_bytes"

    def test_kill_switch_is_thread_safe(self):
        """terminate() can be called from another thread safely."""
        sandbox = PluginSandbox(
            plugin_name="test",
            granted_scopes=["gmail.read.inbox"],
        )
        assert sandbox.is_terminated() is False

        def killer():
            time.sleep(0.01)
            sandbox.terminate()

        t = threading.Thread(target=killer)
        t.start()
        t.join(timeout=1.0)
        assert sandbox.is_terminated() is True


class TestComputePluginHash:
    """Tests for the standalone compute_plugin_hash helper."""

    def test_hash_is_deterministic(self):
        """Same content always produces the same hash."""
        content = b"deterministic content"
        assert compute_plugin_hash(content) == compute_plugin_hash(content)

    def test_hash_format(self):
        """Hash is in 'sha256:<64 hex chars>' format."""
        h = compute_plugin_hash(b"test")
        assert h.startswith("sha256:")
        assert len(h) == 7 + 64

    def test_different_content_different_hash(self):
        """Different content produces different hash."""
        h1 = compute_plugin_hash(b"content-a")
        h2 = compute_plugin_hash(b"content-b")
        assert h1 != h2
