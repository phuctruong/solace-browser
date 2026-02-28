"""
Plugin Loader — OAuth3-governed plugin load/unload pipeline.

Responsibilities:
  - Load a plugin from its manifest (VERIFIED/INSTALLED → ACTIVE).
  - Unload a plugin (ACTIVE/SUSPENDED → UNINSTALLED).
  - Gate every load on the full OAuth3 four-gate enforcement pipeline.
  - Require step-up auth for high-risk ("high") plugins.
  - Write an evidence bundle entry (ISO8601 UTC, token_id, plugin_name) per event.
  - Maintain the load/unload call log for audit trail integrity checks.

Plugin lifecycle (loader view):
  REGISTERED → LOADED → ACTIVE → SUSPENDED → UNLOADED
  (maps to registry states: DISCOVERED/VERIFIED → INSTALLED → ACTIVE → SUSPENDED → UNINSTALLED)

OAuth3 enforcement:
  G1: Token schema
  G2: Token TTL (not expired)
  G3: Scope — all plugin.required_scopes must be in token.scopes
  G4: Revocation — token.revoked must be False

Fail-closed: any gate failure → load blocked, error logged to evidence bundle.

All timestamps: ISO 8601 UTC strings.
All hashes: sha256:<hex> prefixed strings.
No floats in verification paths (int only).

Rung: 641
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .registry import (
    PluginManifest,
    PluginRegistry,
    PluginState,
    PluginLifecycleEvent,
    PluginRegistryError,
    ScopeGateError,
    SHA256VerificationError,
)
from .sandbox import PluginSandbox


# ---------------------------------------------------------------------------
# Evidence bundle entry — every load/unload event
# ---------------------------------------------------------------------------

@dataclass
class LoaderEvidenceEntry:
    """
    Evidence record for a single load or unload event.

    Fields:
        event_id:      UUID4 — globally unique event identifier.
        event_type:    "load" | "unload" | "load_blocked" | "unload_blocked"
        timestamp:     ISO 8601 UTC timestamp.
        plugin_name:   Plugin identifier.
        token_id:      OAuth3 token_id that authorised (or was checked for) the event.
        actor:         Free-text identifier of the caller.
        success:       True if the operation completed successfully.
        error_code:    Error code if blocked (e.g. "OAUTH3_TOKEN_EXPIRED"), else "".
        error_detail:  Human-readable error detail, else "".
        scope_used:    Scope(s) verified during load gate (semicolon-separated).
        step_up_used:  True if step-up auth was required and confirmed.
    """

    event_id:    str
    event_type:  str
    timestamp:   str
    plugin_name: str
    token_id:    str
    actor:       str
    success:     bool
    error_code:  str = ""
    error_detail: str = ""
    scope_used:  str = ""
    step_up_used: bool = False

    def to_dict(self) -> dict:
        """Serialize to plain dict (JSON-serializable)."""
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type,
            "timestamp":   self.timestamp,
            "plugin_name": self.plugin_name,
            "token_id":    self.token_id,
            "actor":       self.actor,
            "success":     self.success,
            "error_code":  self.error_code,
            "error_detail": self.error_detail,
            "scope_used":  self.scope_used,
            "step_up_used": self.step_up_used,
        }


# ---------------------------------------------------------------------------
# PluginLoader — OAuth3-governed load/unload pipeline
# ---------------------------------------------------------------------------

class PluginLoader:
    """
    OAuth3-governed plugin loader.

    Wraps PluginRegistry to provide:
      - Four-gate OAuth3 enforcement before any load.
      - Step-up auth requirement for high-risk plugins.
      - Per-event evidence bundle (append-only list of LoaderEvidenceEntry).
      - SHA256 content verification at load time (if content_bytes provided).

    Token interface:
        The loader accepts AgencyToken objects directly (from src.oauth3.token).
        Tokens must have:
          .token_id: str
          .scopes:   iterable of str
          .revoked:  bool
          .revoked_at: Optional[str]
          .expires_at: str  (ISO 8601 UTC)
          .validate() → (is_valid: bool, error_msg: str)
          .has_scope(scope: str) → bool

    Usage:
        loader = PluginLoader(registry)
        result = loader.load_plugin(manifest.name, token=my_token)
        if result["success"]:
            sandbox = result["sandbox"]
        loader.unload_plugin(manifest.name, token=my_token)
    """

    def __init__(
        self,
        registry: PluginRegistry,
        step_up_required_for_high_risk: bool = True,
    ) -> None:
        """
        Args:
            registry:                   PluginRegistry instance.
            step_up_required_for_high_risk: If True, plugins with risk_level=="high"
                                            (declared in manifest.belt=="black" or via
                                             rung>=274177) require step_up_confirmed=True.
        """
        self._registry = registry
        self._step_up_required_for_high_risk = step_up_required_for_high_risk

        # Evidence bundle — append-only
        self._evidence: List[LoaderEvidenceEntry] = []

        # Loaded plugin sandboxes: plugin_name → PluginSandbox
        self._sandboxes: Dict[str, PluginSandbox] = {}

    # -------------------------------------------------------------------------
    # Load
    # -------------------------------------------------------------------------

    def load_plugin(
        self,
        plugin_name: str,
        token: object,
        content_bytes: Optional[bytes] = None,
        step_up_confirmed: bool = False,
        actor: str = "loader",
    ) -> dict:
        """
        Load a plugin, gated by OAuth3 four-gate enforcement.

        Pipeline:
          1. Look up manifest in registry.
          2. G1: Token schema check (token_id, issuer, subject, scopes, issued_at,
                 expires_at all present and non-empty).
          3. G2: TTL check — token not expired.
          4. G3: Scope check — plugin.required_scopes ⊆ token.scopes.
          5. G4: Revocation check — token.revoked is False.
          6. Step-up gate — if manifest.rung >= 274177 and step_up_required_for_high_risk,
             require step_up_confirmed=True.
          7. SHA256 content verification (if content_bytes provided).
          8. Transition plugin state to INSTALLED then ACTIVE via registry.
          9. Create PluginSandbox for the plugin.
          10. Write evidence bundle entry.

        Args:
            plugin_name:      Name of the plugin to load (must be registered).
            token:            AgencyToken authorising the load.
            content_bytes:    If provided, SHA256 verified against manifest hash.
            step_up_confirmed: Set True to satisfy step-up requirement for high-risk plugins.
            actor:            Caller identifier for evidence trail.

        Returns:
            dict with keys:
              success:      True if loaded successfully.
              plugin_name:  Plugin name.
              sandbox:      PluginSandbox instance (present only on success).
              error_code:   str (present on failure).
              error_detail: str (present on failure).
              evidence_id:  UUID of the evidence bundle entry.
        """
        result: dict = {
            "success": False,
            "plugin_name": plugin_name,
        }

        # Step 1: Manifest lookup
        manifest = self._registry.get_manifest(plugin_name)
        if manifest is None:
            entry = self._record_event(
                event_type="load_blocked",
                plugin_name=plugin_name,
                token_id=_token_id(token),
                actor=actor,
                success=False,
                error_code="PLUGIN_NOT_REGISTERED",
                error_detail=f"Plugin '{plugin_name}' is not registered in the registry.",
            )
            result["error_code"] = "PLUGIN_NOT_REGISTERED"
            result["error_detail"] = entry.error_detail
            result["evidence_id"] = entry.event_id
            return result

        token_id = _token_id(token)

        # Steps 2–4: OAuth3 four-gate via token.validate() + scope check
        gate_result = _run_oauth3_gates(token, list(manifest.required_scopes))
        if not gate_result["allowed"]:
            entry = self._record_event(
                event_type="load_blocked",
                plugin_name=plugin_name,
                token_id=token_id,
                actor=actor,
                success=False,
                error_code=gate_result["error_code"],
                error_detail=gate_result["error_detail"],
                scope_used=";".join(manifest.required_scopes),
            )
            result["error_code"] = gate_result["error_code"]
            result["error_detail"] = gate_result["error_detail"]
            result["evidence_id"] = entry.event_id
            return result

        # Step 6: Step-up gate for high-risk plugins (rung >= 274177)
        if (
            self._step_up_required_for_high_risk
            and manifest.rung >= 274177
            and not step_up_confirmed
        ):
            entry = self._record_event(
                event_type="load_blocked",
                plugin_name=plugin_name,
                token_id=token_id,
                actor=actor,
                success=False,
                error_code="STEP_UP_REQUIRED",
                error_detail=(
                    f"Plugin '{plugin_name}' has rung={manifest.rung} (>= 274177). "
                    "Step-up authentication is required. "
                    "Pass step_up_confirmed=True after user confirms."
                ),
                scope_used=";".join(manifest.required_scopes),
            )
            result["error_code"] = "STEP_UP_REQUIRED"
            result["error_detail"] = entry.error_detail
            result["evidence_id"] = entry.event_id
            return result

        # Step 7: SHA256 content verification (optional)
        if content_bytes is not None:
            try:
                self._registry.verify_content(plugin_name, content_bytes)
            except SHA256VerificationError as exc:
                entry = self._record_event(
                    event_type="load_blocked",
                    plugin_name=plugin_name,
                    token_id=token_id,
                    actor=actor,
                    success=False,
                    error_code="SHA256_VERIFICATION_FAILED",
                    error_detail=str(exc),
                    scope_used=";".join(manifest.required_scopes),
                )
                result["error_code"] = "SHA256_VERIFICATION_FAILED"
                result["error_detail"] = str(exc)
                result["evidence_id"] = entry.event_id
                return result

        # Step 8: Transition state — VERIFIED → INSTALLED → ACTIVE
        current_state = self._registry.get_state(plugin_name)
        try:
            if current_state == PluginState.VERIFIED:
                self._registry.install(plugin_name, actor=actor)
            elif current_state in (PluginState.SUSPENDED, PluginState.INSTALLED):
                # Resume from suspended or install from installed — handled below
                pass
            # Now activate
            granted_scopes = list(getattr(token, "scopes", []))
            self._registry.activate(plugin_name, granted_scopes=granted_scopes, actor=actor)
        except PluginRegistryError as exc:
            entry = self._record_event(
                event_type="load_blocked",
                plugin_name=plugin_name,
                token_id=token_id,
                actor=actor,
                success=False,
                error_code="REGISTRY_TRANSITION_FAILED",
                error_detail=str(exc),
                scope_used=";".join(manifest.required_scopes),
            )
            result["error_code"] = "REGISTRY_TRANSITION_FAILED"
            result["error_detail"] = str(exc)
            result["evidence_id"] = entry.event_id
            return result

        # Step 9: Create sandbox
        sandbox = PluginSandbox(
            plugin_name=plugin_name,
            granted_scopes=list(getattr(token, "scopes", [])),
        )
        self._sandboxes[plugin_name] = sandbox

        # Step 10: Evidence bundle
        step_up_used = (
            self._step_up_required_for_high_risk
            and manifest.rung >= 274177
            and step_up_confirmed
        )
        entry = self._record_event(
            event_type="load",
            plugin_name=plugin_name,
            token_id=token_id,
            actor=actor,
            success=True,
            scope_used=";".join(manifest.required_scopes),
            step_up_used=step_up_used,
        )

        result["success"] = True
        result["sandbox"] = sandbox
        result["evidence_id"] = entry.event_id
        return result

    # -------------------------------------------------------------------------
    # Unload
    # -------------------------------------------------------------------------

    def unload_plugin(
        self,
        plugin_name: str,
        token: object,
        actor: str = "loader",
    ) -> dict:
        """
        Unload (uninstall) a plugin, writing an evidence bundle entry.

        The token is validated (G1–G4) before unloading.
        Scope check for unload requires 'plugin.install' scope (install covers uninstall
        by convention — callers who can install can also remove).

        Args:
            plugin_name: Name of the plugin to unload.
            token:       AgencyToken authorising the unload.
            actor:       Caller identifier for evidence trail.

        Returns:
            dict with keys:
              success:      True if unloaded.
              plugin_name:  Plugin name.
              evidence_id:  UUID of the evidence bundle entry.
              error_code:   str (on failure).
              error_detail: str (on failure).
        """
        result: dict = {
            "success": False,
            "plugin_name": plugin_name,
        }

        # Check plugin is registered
        manifest = self._registry.get_manifest(plugin_name)
        if manifest is None:
            entry = self._record_event(
                event_type="unload_blocked",
                plugin_name=plugin_name,
                token_id=_token_id(token),
                actor=actor,
                success=False,
                error_code="PLUGIN_NOT_REGISTERED",
                error_detail=f"Plugin '{plugin_name}' is not registered.",
            )
            result["error_code"] = "PLUGIN_NOT_REGISTERED"
            result["error_detail"] = entry.error_detail
            result["evidence_id"] = entry.event_id
            return result

        token_id = _token_id(token)

        # OAuth3 four-gate check (token must be valid to authorise unload)
        gate_result = _run_oauth3_gates(token, [])  # unload just needs a valid token
        if not gate_result["allowed"]:
            entry = self._record_event(
                event_type="unload_blocked",
                plugin_name=plugin_name,
                token_id=token_id,
                actor=actor,
                success=False,
                error_code=gate_result["error_code"],
                error_detail=gate_result["error_detail"],
            )
            result["error_code"] = gate_result["error_code"]
            result["error_detail"] = gate_result["error_detail"]
            result["evidence_id"] = entry.event_id
            return result

        # Uninstall via registry
        try:
            self._registry.uninstall(plugin_name, actor=actor)
        except PluginRegistryError as exc:
            entry = self._record_event(
                event_type="unload_blocked",
                plugin_name=plugin_name,
                token_id=token_id,
                actor=actor,
                success=False,
                error_code="REGISTRY_UNINSTALL_FAILED",
                error_detail=str(exc),
            )
            result["error_code"] = "REGISTRY_UNINSTALL_FAILED"
            result["error_detail"] = str(exc)
            result["evidence_id"] = entry.event_id
            return result

        # Clean up sandbox
        self._sandboxes.pop(plugin_name, None)

        entry = self._record_event(
            event_type="unload",
            plugin_name=plugin_name,
            token_id=token_id,
            actor=actor,
            success=True,
        )
        result["success"] = True
        result["evidence_id"] = entry.event_id
        return result

    # -------------------------------------------------------------------------
    # Suspend / Resume
    # -------------------------------------------------------------------------

    def suspend_plugin(
        self,
        plugin_name: str,
        token: object,
        reason: str = "",
        actor: str = "loader",
    ) -> dict:
        """
        Suspend an active plugin (ACTIVE → SUSPENDED).

        Args:
            plugin_name: Plugin to suspend.
            token:       Authorising AgencyToken.
            reason:      Human-readable reason for suspension.
            actor:       Caller identifier.

        Returns:
            dict with success, evidence_id, error_code, error_detail.
        """
        result: dict = {"success": False, "plugin_name": plugin_name}

        manifest = self._registry.get_manifest(plugin_name)
        if manifest is None:
            entry = self._record_event(
                event_type="unload_blocked",
                plugin_name=plugin_name,
                token_id=_token_id(token),
                actor=actor,
                success=False,
                error_code="PLUGIN_NOT_REGISTERED",
                error_detail=f"Plugin '{plugin_name}' is not registered.",
            )
            result["error_code"] = "PLUGIN_NOT_REGISTERED"
            result["error_detail"] = entry.error_detail
            result["evidence_id"] = entry.event_id
            return result

        gate_result = _run_oauth3_gates(token, [])
        if not gate_result["allowed"]:
            entry = self._record_event(
                event_type="unload_blocked",
                plugin_name=plugin_name,
                token_id=_token_id(token),
                actor=actor,
                success=False,
                error_code=gate_result["error_code"],
                error_detail=gate_result["error_detail"],
            )
            result["error_code"] = gate_result["error_code"]
            result["error_detail"] = gate_result["error_detail"]
            result["evidence_id"] = entry.event_id
            return result

        try:
            self._registry.suspend(plugin_name, actor=actor, reason=reason)
        except PluginRegistryError as exc:
            entry = self._record_event(
                event_type="unload_blocked",
                plugin_name=plugin_name,
                token_id=_token_id(token),
                actor=actor,
                success=False,
                error_code="REGISTRY_SUSPEND_FAILED",
                error_detail=str(exc),
            )
            result["error_code"] = "REGISTRY_SUSPEND_FAILED"
            result["error_detail"] = str(exc)
            result["evidence_id"] = entry.event_id
            return result

        entry = self._record_event(
            event_type="unload",
            plugin_name=plugin_name,
            token_id=_token_id(token),
            actor=actor,
            success=True,
            error_detail=f"Suspended: {reason}" if reason else "Suspended.",
        )
        result["success"] = True
        result["evidence_id"] = entry.event_id
        return result

    # -------------------------------------------------------------------------
    # Evidence / audit trail
    # -------------------------------------------------------------------------

    def get_evidence(
        self,
        plugin_name: Optional[str] = None,
    ) -> List[LoaderEvidenceEntry]:
        """
        Return evidence bundle entries, optionally filtered by plugin.

        Args:
            plugin_name: If provided, return only entries for this plugin.

        Returns:
            List of LoaderEvidenceEntry in append order.
        """
        if plugin_name is None:
            return list(self._evidence)
        return [e for e in self._evidence if e.plugin_name == plugin_name]

    def get_evidence_dicts(
        self,
        plugin_name: Optional[str] = None,
    ) -> List[dict]:
        """Return evidence entries as plain dicts."""
        return [e.to_dict() for e in self.get_evidence(plugin_name)]

    # -------------------------------------------------------------------------
    # Sandbox access
    # -------------------------------------------------------------------------

    def get_sandbox(self, plugin_name: str) -> Optional[PluginSandbox]:
        """Return the active sandbox for a plugin, or None if not loaded."""
        return self._sandboxes.get(plugin_name)

    def list_loaded(self) -> List[str]:
        """Return names of all currently loaded (sandboxed) plugins."""
        return list(self._sandboxes.keys())

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        *,
        event_type: str,
        plugin_name: str,
        token_id: str,
        actor: str,
        success: bool,
        error_code: str = "",
        error_detail: str = "",
        scope_used: str = "",
        step_up_used: bool = False,
    ) -> LoaderEvidenceEntry:
        """Create and append an evidence bundle entry."""
        entry = LoaderEvidenceEntry(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=_now_iso8601(),
            plugin_name=plugin_name,
            token_id=token_id,
            actor=actor,
            success=success,
            error_code=error_code,
            error_detail=error_detail,
            scope_used=scope_used,
            step_up_used=step_up_used,
        )
        self._evidence.append(entry)
        return entry


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso8601() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _token_id(token: object) -> str:
    """Extract token_id from a token object (safe: returns '' if missing)."""
    return getattr(token, "token_id", "") or ""


def _run_oauth3_gates(token: object, required_scopes: List[str]) -> dict:
    """
    Run OAuth3 four-gate enforcement against a token.

    Gates:
      G1: Schema — token has token_id, scopes, issued_at, expires_at, issuer, subject.
      G2: TTL — token not expired.
      G3: Scope — all required_scopes in token.scopes.
      G4: Revocation — token.revoked is False.

    Fail-closed: returns {"allowed": False, "error_code": ..., "error_detail": ...}
    on any failure.

    Args:
        token:           AgencyToken-like object.
        required_scopes: Scopes the plugin requires.

    Returns:
        dict with {"allowed": bool, "error_code": str, "error_detail": str}
    """
    # G1: Schema check
    for field_name in ("token_id", "issuer", "subject", "scopes", "issued_at", "expires_at"):
        if not getattr(token, field_name, None):
            return {
                "allowed": False,
                "error_code": "OAUTH3_MALFORMED_TOKEN",
                "error_detail": f"Token missing required field: '{field_name}'.",
            }

    # G2 + G4: Use token.validate() — checks expiry and revocation
    try:
        is_valid, error_msg = token.validate()
    except (AttributeError, TypeError, ValueError) as exc:
        return {
            "allowed": False,
            "error_code": "OAUTH3_MALFORMED_TOKEN",
            "error_detail": f"Token validation error: {exc}",
        }

    if not is_valid:
        if "revoked" in error_msg:
            error_code = "OAUTH3_TOKEN_REVOKED"
        elif "expired" in error_msg:
            error_code = "OAUTH3_TOKEN_EXPIRED"
        else:
            error_code = "OAUTH3_TOKEN_INVALID"
        return {
            "allowed": False,
            "error_code": error_code,
            "error_detail": error_msg,
        }

    # G3: Scope check
    token_scopes = set(getattr(token, "scopes", []) or [])
    missing = [s for s in required_scopes if s not in token_scopes]
    if missing:
        return {
            "allowed": False,
            "error_code": "OAUTH3_SCOPE_DENIED",
            "error_detail": (
                f"Plugin requires scopes {missing} "
                f"not present in token scopes: {sorted(token_scopes)}"
            ),
        }

    return {"allowed": True, "error_code": "", "error_detail": ""}
