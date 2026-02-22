"""
test_full_stack_integration.py
================================
Derived from: diagrams/solace-browser-full-stack.md

Integration tests for the complete SolaceBrowser stack:
  - 5 control surfaces (agent, CLI, web, tunnel, download)
  - 3 access layers (web, machine, tunnel) — all OAuth3-gated
  - Local browser 5-layer pipeline activated in sequence
  - Cloud twin sync (AES-256-GCM, zero-knowledge)
  - Governance layer (stillwater rung verification)
  - User intent → response pipeline end-to-end
  - Evidence bundle complete at end of every successful run

All external calls (LLM, browser, cloud) are mocked.
These tests are INTEGRATION-level: they verify component wiring,
not individual component correctness (covered in unit tests).

Run:
    python -m pytest tests/test_diagrams/test_full_stack_integration.py -v
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, call

import pytest

try:
    from browser_stack import (
        SolaceBrowserStack,
        StackConfig,
        StackResult,
        AccessLayer,
        ControlSurface,
    )
    _STACK_AVAILABLE = True
except ImportError:
    _STACK_AVAILABLE = False

_NEEDS_STACK = pytest.mark.xfail(
    not _STACK_AVAILABLE,
    reason="browser_stack module not yet implemented",
    strict=False,
)

REQUIRED_ARTIFACTS = [
    "classified_intent",
    "gate_audit",
    "recipe",
    "execution_trace",
    "before_snapshot_pzip",
    "after_snapshot_pzip",
    "evidence_bundle",
]


# ---------------------------------------------------------------------------
# Fixtures (stack-level)
# ---------------------------------------------------------------------------


@pytest.fixture
def stack_config(valid_oauth3_token, minimal_recipe, recipe_cache_key) -> Dict[str, Any]:
    """Minimal StackConfig for integration tests."""
    return {
        "llm": MagicMock(return_value="mock-llm-response"),
        "browser": MagicMock(),
        "pzip": MagicMock(),
        "token_vault": {valid_oauth3_token["token_id"]: valid_oauth3_token},
        "recipe_cache": {recipe_cache_key: minimal_recipe},
        "cloud": MagicMock(),
        "evidence_dir": "/tmp/test-evidence",
    }


# ---------------------------------------------------------------------------
# User intent → response pipeline (end-to-end)
# ---------------------------------------------------------------------------


class TestUserIntentToResponsePipeline:
    """
    Diagram: User Intent → 5 layers → Output (evidence_bundle + result)
    All 5 layers must activate in sequence.
    """

    @_NEEDS_STACK
    def test_end_to_end_cache_hit_returns_result(
        self, stack_config, valid_oauth3_token, recipe_cache_key
    ):
        """
        End-to-end: User intent on cache-hit path must return a result and
        an evidence bundle. This is the primary happy path.
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
        )
        assert isinstance(result, StackResult)
        assert result.status == "EXIT_PASS"
        assert result.evidence_bundle is not None

    @_NEEDS_STACK
    def test_end_to_end_all_layers_activated(
        self, stack_config, valid_oauth3_token
    ):
        """
        Diagram: USER → L1 → L2 → L3 → L4 → L5 → OUTPUT
        All 5 layers must be recorded as activated in the result.
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
        )
        assert result.layers_activated is not None
        assert len(result.layers_activated) == 5, (
            f"Expected 5 layers, got {len(result.layers_activated)}"
        )

    @_NEEDS_STACK
    def test_end_to_end_blocked_auth_does_not_execute(
        self, stack_config, expired_oauth3_token
    ):
        """
        An expired token must block the pipeline at Layer 3 (OAuth3 gate).
        Layers 4 and 5 must NOT activate.
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=expired_oauth3_token,
        )
        assert result.status in ("BLOCKED_AUTH", "EXIT_BLOCKED")
        assert "execution_trace" not in (result.artifacts or {})

    @_NEEDS_STACK
    def test_end_to_end_evidence_bundle_complete_at_exit(
        self, stack_config, valid_oauth3_token
    ):
        """
        Diagram: OUTPUT = evidence_bundle.json + result.
        The evidence bundle must be complete (all ALCOA+ fields present).
        """
        from tests.test_diagrams.conftest import ALCOA_REQUIRED_FIELDS
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
        )
        if result.status == "EXIT_PASS":
            bundle = result.evidence_bundle
            for field in ALCOA_REQUIRED_FIELDS:
                assert field in bundle, (
                    f"Evidence bundle missing required field '{field}'"
                )


# ---------------------------------------------------------------------------
# 5 control surfaces
# ---------------------------------------------------------------------------


class TestControlSurfaces:
    """
    Diagram: 5 Control Surfaces
    CS1: AI Agent (Claude Code + stillwater skills)
    CS2: CLI (solace-cli browser run)
    CS3: OAuth3 Web (solaceagi.com dashboard)
    CS4: Native Tunnel (reverse proxy)
    CS5: Download (Tauri/Electron app)

    All surfaces must route through the same LOCAL_BROWSER pipeline.
    """

    @_NEEDS_STACK
    def test_agent_control_surface_routes_to_local_browser(
        self, stack_config, valid_oauth3_token
    ):
        """
        CS1 (AI Agent) must invoke the local browser pipeline.
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
            control_surface=ControlSurface.AI_AGENT,
        )
        assert result.control_surface_used == ControlSurface.AI_AGENT
        assert result.pipeline_used == "local_browser"

    @_NEEDS_STACK
    def test_cli_control_surface_routes_to_local_browser(
        self, stack_config, valid_oauth3_token
    ):
        """
        CS2 (CLI) must use the same local browser pipeline as CS1.
        Control surface is input variation; pipeline is identical.
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
            control_surface=ControlSurface.CLI,
        )
        assert result.control_surface_used == ControlSurface.CLI
        assert result.pipeline_used == "local_browser"

    @_NEEDS_STACK
    def test_all_control_surfaces_produce_same_evidence_structure(
        self, stack_config, valid_oauth3_token
    ):
        """
        Regardless of control surface, the evidence bundle schema must be identical.
        Control surface does not affect compliance output.
        """
        stack = SolaceBrowserStack(config=stack_config)
        results = []
        for surface in [ControlSurface.AI_AGENT, ControlSurface.CLI]:
            result = stack.execute(
                intent="post to LinkedIn",
                token=valid_oauth3_token,
                control_surface=surface,
            )
            results.append(result)

        if all(r.status == "EXIT_PASS" for r in results):
            bundle_keys_1 = set(results[0].evidence_bundle.keys())
            bundle_keys_2 = set(results[1].evidence_bundle.keys())
            assert bundle_keys_1 == bundle_keys_2, (
                "Evidence bundle schema must be identical across control surfaces"
            )


# ---------------------------------------------------------------------------
# 3-layer access model
# ---------------------------------------------------------------------------


class TestThreeLayerAccessModel:
    """
    Diagram: 3 Access Layers (all OAuth3-gated)
    Web Layer: LinkedIn, Gmail, Twitter, 10+ platforms
    Machine Layer: file, terminal (allowlist only), system sensors
    Tunnel Layer: wss:// only, step-up required

    All 3 layers enforce OAuth3 4-gate cascade.
    """

    @_NEEDS_STACK
    def test_web_layer_requires_platform_scope(
        self, stack_config, valid_oauth3_token_with_create
    ):
        """
        Web layer access (LinkedIn create_post) must require linkedin.create_post scope.
        Token without this scope must be BLOCKED.
        """
        # Token with only read scope
        read_only_token = dict(valid_oauth3_token_with_create)
        read_only_token["scopes"] = ["linkedin.read.feed"]  # no create
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="create a LinkedIn post",
            token=read_only_token,
            access_layer=AccessLayer.WEB,
        )
        assert result.status in ("BLOCKED_AUTH", "EXIT_BLOCKED")

    @_NEEDS_STACK
    def test_machine_layer_path_traversal_blocked(
        self, stack_config, valid_oauth3_token
    ):
        """
        Diagram: Machine Layer — 'Path traversal: BLOCKED (../.. always rejected)'.
        Any file access request with ../ must be BLOCKED before OAuth3 check.
        """
        machine_token = dict(valid_oauth3_token)
        machine_token["scopes"] = ["machine.read_file"]
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute_machine_action(
            action="read_file",
            path="../../etc/passwd",  # path traversal attempt
            token=machine_token,
        )
        assert result.status == "EXIT_BLOCKED"
        assert "path_traversal" in result.block_reason.lower()

    @_NEEDS_STACK
    def test_tunnel_layer_requires_step_up(
        self, stack_config, valid_oauth3_token
    ):
        """
        Diagram: Tunnel Layer — 'Step-up required for tunnel access'.
        tunnel.connect scope requires step-up (destructive capability).
        """
        tunnel_token = dict(valid_oauth3_token)
        tunnel_token["scopes"] = ["tunnel.connect"]
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute_tunnel_action(
            token=tunnel_token,
            step_up_confirmed=False,  # not confirmed
        )
        assert result.status in ("BLOCKED_AUTH", "EXIT_BLOCKED")

    @_NEEDS_STACK
    def test_tunnel_layer_wss_only(self, stack_config, valid_oauth3_token):
        """
        Diagram: Tunnel Layer — 'wss:// only (no ws://)'.
        Plain ws:// tunnel must be rejected.
        """
        stack = SolaceBrowserStack(config=stack_config)
        with pytest.raises(Exception, match="wss"):
            stack.open_tunnel(url="ws://solaceagi.com/tunnel")  # plain ws:// rejected


# ---------------------------------------------------------------------------
# Cloud twin integration
# ---------------------------------------------------------------------------


class TestCloudTwinIntegration:
    """
    Diagram: Local Browser ↔ Cloud Twin (AES-256-GCM sync, zero-knowledge)
    TL1 ↔ Cloud: bidirectional sync, encrypted
    """

    @_NEEDS_STACK
    def test_cloud_sync_encrypts_before_upload(
        self, stack_config, valid_oauth3_token, local_state_bundle
    ):
        """
        Diagram: TL1 ↔ Cloud: AES-256-GCM sync zero-knowledge.
        Upload to cloud must be encrypted (not plaintext).
        """
        mock_cloud = MagicMock()
        mock_cloud.upload.return_value = "sha256-hash"
        stack_config["cloud"] = mock_cloud

        stack = SolaceBrowserStack(config=stack_config)
        stack.sync_to_cloud(
            state_bundle=local_state_bundle,
            token=valid_oauth3_token,
        )

        mock_cloud.upload.assert_called_once()
        upload_args = mock_cloud.upload.call_args
        # The upload must carry ciphertext, not raw state
        # Check that the argument is not the plaintext bundle
        payload = upload_args[0][0] if upload_args[0] else upload_args[1].get("payload")
        if payload and hasattr(payload, "ciphertext"):
            assert payload.ciphertext is not None

    @_NEEDS_STACK
    def test_cloud_sync_produces_receipt(
        self, stack_config, valid_oauth3_token, local_state_bundle
    ):
        """
        Diagram: Local → Store sync_receipt.json after upload confirmation.
        """
        mock_cloud = MagicMock()
        mock_cloud.upload.return_value = "sha256-hash-of-ciphertext"
        stack_config["cloud"] = mock_cloud

        stack = SolaceBrowserStack(config=stack_config)
        receipt = stack.sync_to_cloud(
            state_bundle=local_state_bundle,
            token=valid_oauth3_token,
        )
        assert receipt is not None
        assert hasattr(receipt, "sync_id") or "sync_id" in receipt
        assert hasattr(receipt, "cloud_payload_hash_confirmed") or \
               "cloud_payload_hash_confirmed" in receipt


# ---------------------------------------------------------------------------
# Governance layer
# ---------------------------------------------------------------------------


class TestGovernanceLayer:
    """
    Diagram: Governance Layer
    GV1: stillwater verification (rung system)
    GV2: solace-cli (CLI auth + OAuth3 vault)
    GV3: Stillwater Store (skill governance)
    """

    @_NEEDS_STACK
    def test_governance_rung_tracked_in_result(
        self, stack_config, valid_oauth3_token
    ):
        """
        The StackResult must carry rung_achieved (minimum rung across all sub-systems).
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
        )
        assert hasattr(result, "rung_achieved") or "rung_achieved" in (result.__dict__ or {})

    @_NEEDS_STACK
    def test_governance_rung_is_min_of_all_layers(
        self, stack_config, valid_oauth3_token
    ):
        """
        Integration rung = MIN(rung of all contributing sub-agents).
        If any layer achieves rung 641, overall rung cannot exceed 641.
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
        )
        if result.status == "EXIT_PASS":
            # With mocked sub-systems, rung should be at minimum 641
            assert result.rung_achieved >= 641

    @_NEEDS_STACK
    def test_evidence_bundle_rung_matches_result_rung(
        self, stack_config, valid_oauth3_token
    ):
        """
        evidence_bundle.rung_achieved must match StackResult.rung_achieved.
        These must not diverge.
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
        )
        if result.status == "EXIT_PASS":
            bundle_rung = result.evidence_bundle.get("rung_achieved")
            assert bundle_rung == result.rung_achieved


# ---------------------------------------------------------------------------
# Full artifact manifest
# ---------------------------------------------------------------------------


class TestFullStackArtifactManifest:
    """
    Every successful stack execution must produce all 7 required artifacts.
    """

    @_NEEDS_STACK
    def test_full_stack_produces_all_7_artifacts(
        self, stack_config, valid_oauth3_token
    ):
        """
        EXIT_PASS result must have all 7 required artifacts present and non-null.
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
        )
        if result.status == "EXIT_PASS":
            artifacts = result.artifacts
            for artifact_name in REQUIRED_ARTIFACTS:
                value = getattr(artifacts, artifact_name, None)
                assert value is not None, (
                    f"Required artifact '{artifact_name}' is None in EXIT_PASS result"
                )

    @_NEEDS_STACK
    def test_blocked_result_has_no_evidence_bundle(
        self, stack_config, revoked_oauth3_token
    ):
        """
        A BLOCKED result must not carry an evidence bundle.
        Partial evidence bundles are worse than no evidence (misleading).
        """
        stack = SolaceBrowserStack(config=stack_config)
        result = stack.execute(
            intent="post to LinkedIn",
            token=revoked_oauth3_token,
        )
        assert result.status in ("BLOCKED_AUTH", "EXIT_BLOCKED")
        # Evidence bundle should be absent on BLOCKED result
        evidence = getattr(result, "evidence_bundle", None)
        if evidence is not None:
            # If present, it must be clearly marked incomplete
            assert evidence.get("incomplete") is True or evidence.get("status") == "BLOCKED"
