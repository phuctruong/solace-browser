"""
Plugin Registry — OAuth3-governed plugin lifecycle management.

Plugin lifecycle:
  DISCOVERED → VERIFIED → INSTALLED → ACTIVE → SUSPENDED → UNINSTALLED

Key invariants:
  - SHA256 hash must match on every load (integrity gate)
  - Required OAuth3 scopes must be granted before activation
  - Plugin rung must meet minimum rung for security-critical operations
  - SemVer: no downgrades unless explicitly approved
  - Evidence trail: every lifecycle event logged with ISO8601 UTC + SHA256

Fail-closed: any ambiguous gate check → deny.
No exec(), no eval(), no pickle.

Rung: 641
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PluginRegistryError(Exception):
    """Base exception for all plugin registry errors."""


class ScopeGateError(PluginRegistryError):
    """Plugin requires OAuth3 scopes that are not granted."""

    def __init__(self, plugin_name: str, missing_scopes: List[str]) -> None:
        self.plugin_name = plugin_name
        self.missing_scopes = missing_scopes
        super().__init__(
            f"Plugin '{plugin_name}' requires scopes {missing_scopes} "
            "that are not granted by the active token."
        )


class RungEnforcementError(PluginRegistryError):
    """Plugin rung is below the required minimum for the requested operation."""

    def __init__(self, plugin_name: str, plugin_rung: int, required_rung: int) -> None:
        self.plugin_name = plugin_name
        self.plugin_rung = plugin_rung
        self.required_rung = required_rung
        super().__init__(
            f"Plugin '{plugin_name}' rung {plugin_rung} is below required "
            f"minimum {required_rung} for this operation."
        )


class VersionDowngradeError(PluginRegistryError):
    """Attempted to install an older version without explicit approval."""

    def __init__(self, plugin_name: str, installed: str, attempted: str) -> None:
        self.plugin_name = plugin_name
        self.installed_version = installed
        self.attempted_version = attempted
        super().__init__(
            f"Cannot downgrade plugin '{plugin_name}' from {installed} to {attempted}. "
            "Pass allow_downgrade=True to override."
        )


class SHA256VerificationError(PluginRegistryError):
    """Plugin content hash does not match the manifest hash."""

    def __init__(self, plugin_name: str, expected: str, actual: str) -> None:
        self.plugin_name = plugin_name
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"SHA256 mismatch for plugin '{plugin_name}': "
            f"expected {expected!r}, got {actual!r}."
        )


# ---------------------------------------------------------------------------
# Plugin lifecycle states
# ---------------------------------------------------------------------------

class PluginState(str, Enum):
    """Valid states in the plugin lifecycle state machine."""
    DISCOVERED = "DISCOVERED"
    VERIFIED = "VERIFIED"
    INSTALLED = "INSTALLED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    UNINSTALLED = "UNINSTALLED"


# Allowed state transitions (from → set of allowed destinations)
_ALLOWED_TRANSITIONS: Dict[PluginState, frozenset] = {
    PluginState.DISCOVERED: frozenset({PluginState.VERIFIED, PluginState.UNINSTALLED}),
    PluginState.VERIFIED:   frozenset({PluginState.INSTALLED, PluginState.UNINSTALLED}),
    PluginState.INSTALLED:  frozenset({PluginState.ACTIVE, PluginState.UNINSTALLED}),
    PluginState.ACTIVE:     frozenset({PluginState.SUSPENDED, PluginState.UNINSTALLED}),
    PluginState.SUSPENDED:  frozenset({PluginState.ACTIVE, PluginState.UNINSTALLED}),
    PluginState.UNINSTALLED: frozenset(),   # terminal state
}


# ---------------------------------------------------------------------------
# SemVer helpers
# ---------------------------------------------------------------------------

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[a-zA-Z0-9.-]+))?(?:\+(?P<build>[a-zA-Z0-9.-]+))?$"
)


def _parse_semver(version: str) -> Tuple[int, int, int]:
    """
    Parse a SemVer string to (major, minor, patch) tuple.

    Raises:
        ValueError: If the version string is not valid SemVer.
    """
    m = _SEMVER_RE.match(version)
    if not m:
        raise ValueError(
            f"Invalid SemVer string: {version!r}. "
            "Expected format: MAJOR.MINOR.PATCH (e.g. '1.2.3')."
        )
    return int(m.group("major")), int(m.group("minor")), int(m.group("patch"))


def _is_downgrade(installed: str, candidate: str) -> bool:
    """
    Return True if candidate version is strictly older than installed version.

    Pre-release / build metadata are ignored in the comparison.
    """
    try:
        iv = _parse_semver(installed)
        cv = _parse_semver(candidate)
    except ValueError:
        # If we cannot parse, treat as no-downgrade (fail-open only for version parsing)
        return False
    return cv < iv


# ---------------------------------------------------------------------------
# PluginManifest — immutable plugin descriptor
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PluginManifest:
    """
    Immutable descriptor for a SolaceBrowser plugin.

    Fields:
        name:            Unique plugin identifier (slug, e.g. 'gmail-sorter').
        version:         SemVer string (e.g. '1.2.3').
        author:          Plugin author identifier (e.g. email or GitHub handle).
        description:     Human-readable description of what the plugin does.
        required_scopes: OAuth3 scopes the plugin needs to execute.
                         Plugin CANNOT activate without ALL scopes granted.
        entry_point:     Module path or callable reference (e.g. 'myplugin.main:run').
        sha256_hash:     SHA-256 hex digest of the plugin content ('sha256:<hex>').
        rung:            Minimum security rung declared by the plugin author.
                         Operations gated at rung 274177 or 65537 will be blocked
                         unless plugin.rung meets or exceeds that rung.
        belt:            Belt level (white/yellow/orange/green/blue/black).
    """

    name: str
    version: str
    author: str
    description: str
    required_scopes: Tuple[str, ...]
    entry_point: str
    sha256_hash: str
    rung: int
    belt: str

    def __post_init__(self) -> None:
        """Validate manifest fields after construction."""
        self._validate()

    def _validate(self) -> None:
        """Raise ValueError for any invalid manifest field."""
        if not self.name or not self.name.strip():
            raise ValueError("Plugin name must not be empty.")
        if not re.match(r"^[a-z0-9][a-z0-9_-]*$", self.name):
            raise ValueError(
                f"Plugin name {self.name!r} must be lowercase alphanumeric "
                "with hyphens/underscores only (no leading hyphen/underscore)."
            )
        # Validate SemVer
        _parse_semver(self.version)  # raises ValueError if invalid

        if not self.author or not self.author.strip():
            raise ValueError("Plugin author must not be empty.")
        if not self.description or not self.description.strip():
            raise ValueError("Plugin description must not be empty.")
        if not self.entry_point or not self.entry_point.strip():
            raise ValueError("Plugin entry_point must not be empty.")

        # SHA256 format: 'sha256:<64 hex chars>'
        if not self.sha256_hash.startswith("sha256:"):
            raise ValueError(
                f"sha256_hash must start with 'sha256:' prefix, got {self.sha256_hash!r}."
            )
        hex_part = self.sha256_hash[len("sha256:"):]
        if len(hex_part) != 64 or not all(c in "0123456789abcdef" for c in hex_part):
            raise ValueError(
                f"sha256_hash hex portion must be exactly 64 lowercase hex characters, "
                f"got {hex_part!r}."
            )

        # Rung must be one of the canonical values or positive int
        if not isinstance(self.rung, int) or self.rung <= 0:
            raise ValueError(f"Plugin rung must be a positive integer, got {self.rung!r}.")

        valid_belts = {"white", "yellow", "orange", "green", "blue", "black"}
        if self.belt not in valid_belts:
            raise ValueError(
                f"Plugin belt {self.belt!r} is not valid. "
                f"Must be one of: {sorted(valid_belts)}."
            )

    def manifest_hash(self) -> str:
        """
        Compute SHA-256 over the manifest fields (excluding sha256_hash itself).

        Used to detect manifest tampering independent of plugin content.

        Returns:
            'sha256:<hex_digest>'
        """
        canonical = {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "required_scopes": sorted(self.required_scopes),
            "entry_point": self.entry_point,
            "rung": self.rung,
            "belt": self.belt,
        }
        raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def to_dict(self) -> dict:
        """Serialize to plain dict (JSON-serializable)."""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "required_scopes": list(self.required_scopes),
            "entry_point": self.entry_point,
            "sha256_hash": self.sha256_hash,
            "rung": self.rung,
            "belt": self.belt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        """
        Deserialize from plain dict.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        required_scopes = data.get("required_scopes")
        if required_scopes is None:
            raise ValueError(
                "required_scopes must be a list, got null "
                "(null != zero — required_scopes cannot be None)."
            )
        return cls(
            name=data["name"],
            version=data["version"],
            author=data["author"],
            description=data["description"],
            required_scopes=tuple(required_scopes),
            entry_point=data["entry_point"],
            sha256_hash=data["sha256_hash"],
            rung=data["rung"],
            belt=data["belt"],
        )


# ---------------------------------------------------------------------------
# PluginLifecycleEvent — evidence trail entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PluginLifecycleEvent:
    """
    Immutable record of a single plugin lifecycle transition.

    Every event carries:
        timestamp:    ISO8601 UTC timestamp of the event.
        plugin_name:  Plugin identifier.
        from_state:   Previous state (None for the initial DISCOVERED event).
        to_state:     New state after the transition.
        manifest_hash: SHA256 of the manifest at the time of the event.
        actor:        Who triggered the event (token subject or 'system').
        detail:       Optional human-readable detail.
    """

    timestamp: str
    plugin_name: str
    from_state: Optional[PluginState]
    to_state: PluginState
    manifest_hash: str
    actor: str
    detail: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return {
            "timestamp": self.timestamp,
            "plugin_name": self.plugin_name,
            "from_state": self.from_state.value if self.from_state else None,
            "to_state": self.to_state.value,
            "manifest_hash": self.manifest_hash,
            "actor": self.actor,
            "detail": self.detail,
        }


def _now_iso8601() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# PluginRegistry — lifecycle + OAuth3 scope gate + rung enforcement
# ---------------------------------------------------------------------------

class PluginRegistry:
    """
    Central registry for SolaceBrowser plugins.

    Responsibilities:
      - Register plugins (DISCOVERED → VERIFIED with SHA256 check)
      - Activate plugins (VERIFIED/INSTALLED → ACTIVE with OAuth3 scope gate)
      - Suspend and uninstall plugins
      - Query by scope, belt, rung
      - Enforce rung requirements for security-critical operations
      - Enforce SemVer no-downgrade policy
      - Maintain evidence trail (immutable log of all lifecycle events)

    Fail-closed: any missing scope or hash mismatch → deny, no exceptions.

    Usage:
        registry = PluginRegistry(min_rung=641)
        registry.register(manifest, plugin_content_bytes)
        registry.activate(manifest.name, token)
    """

    def __init__(self, min_rung: int = 641) -> None:
        """
        Args:
            min_rung: Minimum rung a plugin must declare to be activated.
                      Plugins with rung < min_rung are rejected at registration.
        """
        self._min_rung: int = min_rung
        # plugin_name → PluginManifest
        self._manifests: Dict[str, PluginManifest] = {}
        # plugin_name → PluginState
        self._states: Dict[str, PluginState] = {}
        # Evidence trail (append-only)
        self._events: List[PluginLifecycleEvent] = []

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        manifest: PluginManifest,
        from_state: Optional[PluginState],
        to_state: PluginState,
        actor: str,
        detail: Optional[str] = None,
    ) -> PluginLifecycleEvent:
        """Append a lifecycle event to the evidence trail and return it."""
        event = PluginLifecycleEvent(
            timestamp=_now_iso8601(),
            plugin_name=manifest.name,
            from_state=from_state,
            to_state=to_state,
            manifest_hash=manifest.manifest_hash(),
            actor=actor,
            detail=detail,
        )
        self._events.append(event)
        return event

    def _transition(
        self,
        manifest: PluginManifest,
        to_state: PluginState,
        actor: str,
        detail: Optional[str] = None,
    ) -> PluginLifecycleEvent:
        """
        Perform a state transition for a plugin, recording the event.

        Raises:
            PluginRegistryError: If the transition is not allowed.
        """
        current = self._states.get(manifest.name)
        if current is None:
            raise PluginRegistryError(
                f"Plugin '{manifest.name}' is not registered. "
                "Call register() first."
            )
        allowed = _ALLOWED_TRANSITIONS.get(current, frozenset())
        if to_state not in allowed:
            raise PluginRegistryError(
                f"Plugin '{manifest.name}': transition {current.value} → "
                f"{to_state.value} is not allowed. "
                f"Allowed transitions from {current.value}: "
                f"{[s.value for s in sorted(allowed, key=lambda x: x.value)]}."
            )
        self._states[manifest.name] = to_state
        return self._record_event(manifest, current, to_state, actor, detail)

    # -------------------------------------------------------------------------
    # SHA256 verification
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """
        Compute SHA256 of plugin content bytes.

        Args:
            content: Raw plugin content bytes.

        Returns:
            'sha256:<hex_digest>'
        """
        digest = hashlib.sha256(content).hexdigest()
        return f"sha256:{digest}"

    def _verify_hash(self, manifest: PluginManifest, content: bytes) -> None:
        """
        Verify that content matches manifest.sha256_hash.

        Raises:
            SHA256VerificationError: If hashes do not match.
        """
        actual = self.compute_hash(content)
        if actual != manifest.sha256_hash:
            raise SHA256VerificationError(
                plugin_name=manifest.name,
                expected=manifest.sha256_hash,
                actual=actual,
            )

    # -------------------------------------------------------------------------
    # OAuth3 scope gate
    # -------------------------------------------------------------------------

    @staticmethod
    def _check_scopes(
        manifest: PluginManifest,
        granted_scopes: List[str],
    ) -> None:
        """
        Verify all required_scopes are in granted_scopes.

        Raises:
            ScopeGateError: If any required scope is missing.
        """
        missing = [s for s in manifest.required_scopes if s not in granted_scopes]
        if missing:
            raise ScopeGateError(plugin_name=manifest.name, missing_scopes=missing)

    # -------------------------------------------------------------------------
    # Rung enforcement
    # -------------------------------------------------------------------------

    def _check_rung(self, manifest: PluginManifest, required_rung: int) -> None:
        """
        Verify plugin.rung >= required_rung.

        Raises:
            RungEnforcementError: If plugin rung is insufficient.
        """
        if manifest.rung < required_rung:
            raise RungEnforcementError(
                plugin_name=manifest.name,
                plugin_rung=manifest.rung,
                required_rung=required_rung,
            )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def register(
        self,
        manifest: PluginManifest,
        content: bytes,
        actor: str = "system",
    ) -> PluginLifecycleEvent:
        """
        Register a plugin: DISCOVERED → VERIFIED (with SHA256 check).

        If a plugin with the same name already exists:
          - Upgrade (newer version): allowed.
          - Downgrade (older version): blocked unless allow_downgrade=True is set
            in a separate call to upgrade().

        Args:
            manifest: PluginManifest describing the plugin.
            content:  Raw plugin content bytes (for SHA256 verification).
            actor:    Identity of the registering principal.

        Returns:
            PluginLifecycleEvent for the DISCOVERED transition.

        Raises:
            SHA256VerificationError: If content hash does not match manifest.sha256_hash.
            RungEnforcementError:    If manifest.rung < self._min_rung.
            VersionDowngradeError:   If attempting to register an older version.
        """
        # Rung gate: plugin must declare at least min_rung
        if manifest.rung < self._min_rung:
            raise RungEnforcementError(
                plugin_name=manifest.name,
                plugin_rung=manifest.rung,
                required_rung=self._min_rung,
            )

        # Version downgrade check (if plugin is already registered)
        if manifest.name in self._manifests:
            installed_manifest = self._manifests[manifest.name]
            if _is_downgrade(installed_manifest.version, manifest.version):
                raise VersionDowngradeError(
                    plugin_name=manifest.name,
                    installed=installed_manifest.version,
                    attempted=manifest.version,
                )

        # SHA256 integrity gate
        self._verify_hash(manifest, content)

        # Transition to DISCOVERED then immediately to VERIFIED
        if manifest.name not in self._states:
            # Fresh registration
            self._manifests[manifest.name] = manifest
            self._states[manifest.name] = PluginState.DISCOVERED
            discovered_event = self._record_event(
                manifest, None, PluginState.DISCOVERED, actor,
                detail="Plugin discovered."
            )
        else:
            # Re-registration (upgrade): move back to DISCOVERED regardless of prior state
            old_manifest = self._manifests[manifest.name]
            self._manifests[manifest.name] = manifest
            self._states[manifest.name] = PluginState.DISCOVERED
            discovered_event = self._record_event(
                manifest, self._states.get(manifest.name, PluginState.DISCOVERED),
                PluginState.DISCOVERED, actor,
                detail=f"Plugin re-registered (upgrade from {old_manifest.version})."
            )

        # Immediately verify (DISCOVERED → VERIFIED)
        self._states[manifest.name] = PluginState.VERIFIED
        self._record_event(
            manifest, PluginState.DISCOVERED, PluginState.VERIFIED, actor,
            detail="SHA256 verified."
        )

        return discovered_event

    def install(
        self,
        plugin_name: str,
        actor: str = "system",
    ) -> PluginLifecycleEvent:
        """
        Move plugin from VERIFIED to INSTALLED.

        Args:
            plugin_name: Name of the plugin to install.
            actor:       Identity of the installing principal.

        Returns:
            PluginLifecycleEvent for the INSTALLED transition.

        Raises:
            PluginRegistryError: If plugin is not in VERIFIED state.
        """
        manifest = self._get_manifest(plugin_name)
        return self._transition(manifest, PluginState.INSTALLED, actor, detail="Plugin installed.")

    def activate(
        self,
        plugin_name: str,
        granted_scopes: List[str],
        actor: str = "system",
        required_rung: Optional[int] = None,
    ) -> PluginLifecycleEvent:
        """
        Activate a plugin (INSTALLED → ACTIVE) with OAuth3 scope gate.

        Args:
            plugin_name:    Name of the plugin to activate.
            granted_scopes: OAuth3 scopes granted by the active token.
            actor:          Token subject or 'system'.
            required_rung:  If set, plugin.rung must meet this rung.

        Returns:
            PluginLifecycleEvent for the ACTIVE transition.

        Raises:
            ScopeGateError:      If required scopes are not granted.
            RungEnforcementError: If plugin rung is insufficient.
            PluginRegistryError: If plugin is not in INSTALLED state.
        """
        manifest = self._get_manifest(plugin_name)

        # OAuth3 scope gate (fail-closed)
        self._check_scopes(manifest, granted_scopes)

        # Rung gate (if required_rung specified)
        if required_rung is not None:
            self._check_rung(manifest, required_rung)

        return self._transition(
            manifest, PluginState.ACTIVE, actor, detail="Plugin activated."
        )

    def suspend(
        self,
        plugin_name: str,
        actor: str = "system",
        reason: Optional[str] = None,
    ) -> PluginLifecycleEvent:
        """
        Suspend an active plugin (ACTIVE → SUSPENDED).

        Args:
            plugin_name: Name of the plugin to suspend.
            actor:       Identity of the suspending principal.
            reason:      Optional reason for suspension.

        Returns:
            PluginLifecycleEvent for the SUSPENDED transition.
        """
        manifest = self._get_manifest(plugin_name)
        detail = f"Plugin suspended. Reason: {reason}" if reason else "Plugin suspended."
        return self._transition(manifest, PluginState.SUSPENDED, actor, detail=detail)

    def resume(
        self,
        plugin_name: str,
        granted_scopes: List[str],
        actor: str = "system",
    ) -> PluginLifecycleEvent:
        """
        Resume a suspended plugin (SUSPENDED → ACTIVE) with scope re-check.

        Args:
            plugin_name:    Name of the plugin to resume.
            granted_scopes: OAuth3 scopes currently granted.
            actor:          Token subject or 'system'.

        Returns:
            PluginLifecycleEvent for the ACTIVE transition.

        Raises:
            ScopeGateError: If required scopes are no longer granted.
        """
        manifest = self._get_manifest(plugin_name)
        # Re-check scopes on resume (token may have been revoked/narrowed)
        self._check_scopes(manifest, granted_scopes)
        return self._transition(manifest, PluginState.ACTIVE, actor, detail="Plugin resumed.")

    def uninstall(
        self,
        plugin_name: str,
        actor: str = "system",
    ) -> PluginLifecycleEvent:
        """
        Uninstall a plugin (any state → UNINSTALLED).

        Args:
            plugin_name: Name of the plugin to uninstall.
            actor:       Identity of the uninstalling principal.

        Returns:
            PluginLifecycleEvent for the UNINSTALLED transition.
        """
        manifest = self._get_manifest(plugin_name)
        event = self._transition(
            manifest, PluginState.UNINSTALLED, actor, detail="Plugin uninstalled."
        )
        # Remove from active maps (evidence trail is preserved)
        del self._manifests[plugin_name]
        del self._states[plugin_name]
        return event

    # -------------------------------------------------------------------------
    # Query API
    # -------------------------------------------------------------------------

    def get_state(self, plugin_name: str) -> Optional[PluginState]:
        """Return current state of a plugin, or None if not registered."""
        return self._states.get(plugin_name)

    def get_manifest(self, plugin_name: str) -> Optional[PluginManifest]:
        """Return manifest for a plugin, or None if not registered."""
        return self._manifests.get(plugin_name)

    def _get_manifest(self, plugin_name: str) -> PluginManifest:
        """Return manifest or raise PluginRegistryError if not found."""
        m = self._manifests.get(plugin_name)
        if m is None:
            raise PluginRegistryError(
                f"Plugin '{plugin_name}' is not registered."
            )
        return m

    def list_all(self) -> List[PluginManifest]:
        """Return all registered plugin manifests."""
        return list(self._manifests.values())

    def list_active(self) -> List[PluginManifest]:
        """Return manifests for all ACTIVE plugins."""
        return [
            m for name, m in self._manifests.items()
            if self._states.get(name) == PluginState.ACTIVE
        ]

    def query_by_scope(self, scope: str) -> List[PluginManifest]:
        """
        Return all registered plugins that require the given scope.

        Args:
            scope: OAuth3 scope string (e.g. 'gmail.read.inbox').

        Returns:
            List of matching PluginManifest objects.
        """
        return [
            m for m in self._manifests.values()
            if scope in m.required_scopes
        ]

    def query_by_belt(self, belt: str) -> List[PluginManifest]:
        """
        Return all registered plugins with the given belt.

        Args:
            belt: Belt level string (e.g. 'orange').

        Returns:
            List of matching PluginManifest objects.
        """
        return [m for m in self._manifests.values() if m.belt == belt]

    def query_by_rung(self, min_rung: int) -> List[PluginManifest]:
        """
        Return all registered plugins with rung >= min_rung.

        Args:
            min_rung: Minimum rung value (inclusive).

        Returns:
            List of matching PluginManifest objects.
        """
        return [m for m in self._manifests.values() if m.rung >= min_rung]

    def evidence_trail(self) -> List[PluginLifecycleEvent]:
        """
        Return a copy of the immutable evidence trail.

        Returns:
            List of PluginLifecycleEvent in chronological order.
        """
        return list(self._events)

    def evidence_for_plugin(self, plugin_name: str) -> List[PluginLifecycleEvent]:
        """
        Return evidence trail entries for a specific plugin.

        Args:
            plugin_name: Plugin name to filter by.

        Returns:
            List of PluginLifecycleEvent for that plugin.
        """
        return [e for e in self._events if e.plugin_name == plugin_name]

    def verify_content(self, plugin_name: str, content: bytes) -> bool:
        """
        Verify plugin content against its registered manifest hash.

        Args:
            plugin_name: Name of the registered plugin.
            content:     Raw plugin content bytes.

        Returns:
            True if content matches; False if plugin is not registered.

        Raises:
            SHA256VerificationError: If plugin is registered but hash does not match.
        """
        manifest = self._manifests.get(plugin_name)
        if manifest is None:
            return False
        self._verify_hash(manifest, content)
        return True
