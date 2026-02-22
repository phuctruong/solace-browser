"""
Plugin Architecture for SolaceBrowser — OAuth3-governed plugin system.

Better than OpenClaw's ClawHub Registry:
  - OAuth3 scope gates (plugin cannot run without granted scopes)
  - SHA256 integrity verification on every load
  - Rung-enforced access to security-critical operations
  - Full evidence trail (ISO8601 timestamp + SHA256 per lifecycle event)
  - SemVer version pinning with no-downgrade enforcement
  - Sandboxed execution: no filesystem/network access beyond declared scopes

Rung: 641
"""

from .registry import (
    PluginManifest,
    PluginRegistry,
    PluginState,
    PluginLifecycleEvent,
    PluginRegistryError,
    ScopeGateError,
    RungEnforcementError,
    VersionDowngradeError,
    SHA256VerificationError,
)
from .loader import (
    PluginLoader,
    LoaderEvidenceEntry,
)
from .sandbox import (
    PluginSandbox,
    SandboxViolationError,
    SandboxResourceLimitError,
    SandboxTerminatedError,
)

__all__ = [
    # Registry
    "PluginManifest",
    "PluginRegistry",
    "PluginState",
    "PluginLifecycleEvent",
    "PluginRegistryError",
    "ScopeGateError",
    "RungEnforcementError",
    "VersionDowngradeError",
    "SHA256VerificationError",
    # Loader
    "PluginLoader",
    "LoaderEvidenceEntry",
    # Sandbox
    "PluginSandbox",
    "SandboxViolationError",
    "SandboxResourceLimitError",
    "SandboxTerminatedError",
]

__version__ = "1.0.0"
__rung__ = 641
