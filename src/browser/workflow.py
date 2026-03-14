# Diagram: 01-triangle-architecture
"""
workflow.py — Pausable, Resumable, Approval-Gating Workflow State Machine

Executes multi-step recipes with:
  - Approval gates (pause/resume at sensitive steps)
  - Cryptographic resume tokens (HMAC-SHA256)
  - Append-only audit transition log
  - ISO8601 UTC timestamps throughout
  - No external dependencies (stdlib only)

Rung: 641
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESUME_TOKEN_TTL_SECONDS: int = 3600  # 1 hour default TTL for resume tokens
STEP_ID_FORMAT: str = "step_{:03d}"   # "step_001", "step_002", …


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WorkflowState(Enum):
    PENDING            = "pending"
    RUNNING            = "running"
    PAUSED             = "paused"             # paused at approval gate
    WAITING_APPROVAL   = "waiting_approval"
    APPROVED           = "approved"
    REJECTED           = "rejected"
    COMPLETED          = "completed"
    FAILED             = "failed"
    CANCELLED          = "cancelled"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WorkflowStep:
    """A single step in a workflow (click, type, navigate, approve, …)."""

    step_id: str                        # sequential: "step_001", "step_002"
    action: str                         # "click", "type", "navigate", "approve", …
    target: str                         # CSS selector, URL ref, or description
    value: str = ""                     # input value for type actions
    requires_approval: bool = False     # if True, workflow pauses before executing
    oauth3_scope: str = ""              # required OAuth3 scope for this step
    timeout_seconds: int = 30
    completed: bool = False
    result: dict = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""


@dataclass
class ResumeToken:
    """Cryptographic resume token for paused workflows.

    Token integrity: HMAC-SHA256(token_id + workflow_id + step_id, secret)
    Validates: not expired, not already used, hash matches.
    """

    token_id: str       # uuid4
    workflow_id: str
    step_id: str        # which step to resume from
    created_at: str     # ISO8601 UTC
    expires_at: str     # ISO8601 UTC  (TTL: 1 hour default)
    token_hash: str     # hmac-sha256(token_id + workflow_id + step_id + secret)
    used: bool = False


@dataclass
class Workflow:
    """Full workflow execution state."""

    workflow_id: str                    # uuid4
    recipe_id: str                      # which recipe this workflow executes
    user_id: str
    token_id: str                       # OAuth3 token
    state: WorkflowState = WorkflowState.PENDING
    steps: List[WorkflowStep] = field(default_factory=list)
    current_step_index: int = 0
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    paused_at: str = ""
    resume_token: Optional[ResumeToken] = None
    evidence: List[dict] = field(default_factory=list)
    transitions: List[dict] = field(default_factory=list)  # append-only audit log


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time as an ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(dt_str: str) -> datetime:
    """Parse an ISO8601 string to a timezone-aware datetime."""
    dt_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _compute_token_hash(
    token_id: str,
    workflow_id: str,
    step_id: str,
    secret: str,
) -> str:
    """Compute HMAC-SHA256 of (token_id|workflow_id|step_id) keyed with secret.

    Returns: 'hmac-sha256:<hex_digest>'
    """
    msg = f"{token_id}|{workflow_id}|{step_id}".encode("utf-8")
    key = secret.encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return f"hmac-sha256:{digest}"


# ---------------------------------------------------------------------------
# WorkflowEngine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """Pausable, resumable, approval-gating workflow execution engine.

    All state is kept in-process (dict keyed by workflow_id).
    Transitions are append-only (audit trail).
    Resume tokens use HMAC-SHA256 and have a 1-hour TTL by default.

    Usage:
        engine = WorkflowEngine(secret="my-secret")
        wf = engine.create("recipe-42", steps_list, user_id="alice", token_id="tok-1")
        engine.start(wf.workflow_id)
        step = engine.execute_step(wf.workflow_id)
        # If step.requires_approval is True, the workflow is now PAUSED
        # and a resume_token was generated.
        engine.approve(wf.workflow_id)          # approve and continue
        engine.resume(wf.workflow_id, resume_token.token_id)  # resume after pause
    """

    def __init__(self, secret: str = "") -> None:
        self._workflows: Dict[str, Workflow] = {}
        self._secret: str = secret or "default-dev-secret"

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def create(
        self,
        recipe_id: str,
        steps: List[dict],
        user_id: str,
        token_id: str,
    ) -> Workflow:
        """Create a new workflow from a list of step dicts.

        Each step dict maps to a WorkflowStep. Recognised keys:
            action, target, value, requires_approval, oauth3_scope,
            timeout_seconds

        Steps are assigned sequential IDs: step_001, step_002, …

        Args:
            recipe_id:  Identifier of the recipe being executed.
            steps:      List of step configuration dicts.
            user_id:    Consenting principal identifier.
            token_id:   OAuth3 AgencyToken ID bound to this workflow.

        Returns:
            New Workflow in PENDING state.
        """
        workflow_id = str(uuid.uuid4())
        now = _now_iso()

        workflow_steps: List[WorkflowStep] = []
        for idx, raw in enumerate(steps):
            step_id = STEP_ID_FORMAT.format(idx + 1)
            workflow_steps.append(
                WorkflowStep(
                    step_id=step_id,
                    action=str(raw.get("action", "")),
                    target=str(raw.get("target", "")),
                    value=str(raw.get("value", "")),
                    requires_approval=bool(raw.get("requires_approval", False)),
                    oauth3_scope=str(raw.get("oauth3_scope", "")),
                    timeout_seconds=int(raw.get("timeout_seconds", 30)),
                )
            )

        wf = Workflow(
            workflow_id=workflow_id,
            recipe_id=recipe_id,
            user_id=user_id,
            token_id=token_id,
            state=WorkflowState.PENDING,
            steps=workflow_steps,
            current_step_index=0,
            created_at=now,
            started_at="",
            completed_at="",
            paused_at="",
            resume_token=None,
            evidence=[],
            transitions=[],
        )

        # Record creation transition
        self._transition(wf, WorkflowState.PENDING, reason="workflow_created")
        self._workflows[workflow_id] = wf
        return wf

    def start(self, workflow_id: str) -> Workflow:
        """Transition a PENDING workflow to RUNNING.

        Args:
            workflow_id: UUID of the workflow to start.

        Returns:
            Updated Workflow in RUNNING state.

        Raises:
            KeyError:   If workflow_id is not found.
            ValueError: If workflow is not in PENDING state.
        """
        wf = self._get(workflow_id)
        if wf.state != WorkflowState.PENDING:
            raise ValueError(
                f"Cannot start workflow in state {wf.state.value!r}. "
                "Workflow must be in PENDING state to start."
            )

        wf.started_at = _now_iso()
        self._transition(wf, WorkflowState.RUNNING, reason="workflow_started")
        return wf

    def execute_step(self, workflow_id: str) -> WorkflowStep:
        """Execute the current step.

        If the current step has requires_approval=True, the workflow is paused
        immediately (state → PAUSED) and a resume token is generated — the step
        is NOT marked as completed yet.

        If the step does not require approval, it is marked completed, evidence
        is recorded, and the index advances.  When all steps are complete the
        workflow transitions to COMPLETED.

        Args:
            workflow_id: UUID of the workflow.

        Returns:
            The WorkflowStep that was either executed or paused on.

        Raises:
            KeyError:   If workflow_id is not found.
            ValueError: If workflow is not in RUNNING or APPROVED state,
                        or if there are no steps remaining.
        """
        wf = self._get(workflow_id)

        if wf.state not in (WorkflowState.RUNNING, WorkflowState.APPROVED):
            raise ValueError(
                f"Cannot execute step when workflow state is {wf.state.value!r}. "
                "Workflow must be RUNNING or APPROVED."
            )

        if wf.current_step_index >= len(wf.steps):
            raise ValueError(
                f"No remaining steps in workflow {workflow_id!r}. "
                f"current_step_index={wf.current_step_index}, "
                f"total_steps={len(wf.steps)}"
            )

        step = wf.steps[wf.current_step_index]
        step.started_at = _now_iso()

        if step.requires_approval:
            # Pause before executing — generate resume token
            self.pause(workflow_id, reason="approval_required")
            return step

        # Execute the step (simulate execution — mark completed with result)
        step.result = {
            "status": "executed",
            "action": step.action,
            "target": step.target,
            "value": step.value,
        }
        step.completed = True
        step.completed_at = _now_iso()

        # Append evidence
        wf.evidence.append({
            "step_id": step.step_id,
            "action": step.action,
            "target": step.target,
            "completed_at": step.completed_at,
            "result": step.result,
        })

        # Advance index
        wf.current_step_index += 1

        # Check if all steps are done
        if wf.current_step_index >= len(wf.steps):
            wf.completed_at = _now_iso()
            self._transition(wf, WorkflowState.COMPLETED, reason="all_steps_completed")
        else:
            # Remain in RUNNING state — keep current state logged
            if wf.state == WorkflowState.APPROVED:
                self._transition(wf, WorkflowState.RUNNING, reason="step_completed_resuming")

        return step

    def pause(self, workflow_id: str, reason: str = "approval_required") -> ResumeToken:
        """Pause a workflow and generate a cryptographic resume token.

        Args:
            workflow_id: UUID of the workflow to pause.
            reason:      Human-readable reason for pausing.

        Returns:
            A ResumeToken the caller can use to resume later.

        Raises:
            KeyError:   If workflow_id is not found.
            ValueError: If the workflow is not in a pausable state
                        (RUNNING or WAITING_APPROVAL).
        """
        wf = self._get(workflow_id)

        if wf.state not in (
            WorkflowState.RUNNING,
            WorkflowState.WAITING_APPROVAL,
            WorkflowState.APPROVED,
        ):
            raise ValueError(
                f"Cannot pause workflow in state {wf.state.value!r}. "
                "Workflow must be RUNNING or WAITING_APPROVAL."
            )

        wf.paused_at = _now_iso()
        self._transition(wf, WorkflowState.PAUSED, reason=reason)
        self._transition(wf, WorkflowState.WAITING_APPROVAL, reason="awaiting_approver")

        token = self._generate_resume_token(wf)
        wf.resume_token = token
        return token

    def resume(self, workflow_id: str, token_id: str) -> Workflow:
        """Resume a paused workflow using a valid resume token.

        Validates that the resume token:
          1. Belongs to this workflow.
          2. Has not expired (TTL check).
          3. Has not already been used.
          4. Has an intact HMAC-SHA256 hash.

        Marks the token as used (single-use), then transitions to RUNNING.

        Args:
            workflow_id: UUID of the workflow.
            token_id:    UUID of the resume token.

        Returns:
            Updated Workflow in RUNNING state.

        Raises:
            KeyError:   If workflow_id is not found.
            ValueError: If the workflow is not PAUSED/WAITING_APPROVAL,
                        or if the resume token is invalid/expired/used.
        """
        wf = self._get(workflow_id)

        if wf.state not in (WorkflowState.PAUSED, WorkflowState.WAITING_APPROVAL):
            raise ValueError(
                f"Cannot resume workflow in state {wf.state.value!r}. "
                "Workflow must be PAUSED or WAITING_APPROVAL."
            )

        if not self._validate_resume_token(wf, token_id):
            raise ValueError(
                f"Invalid, expired, or already-used resume token {token_id!r} "
                f"for workflow {workflow_id!r}."
            )

        # Mark token used (single-use guarantee)
        if wf.resume_token is not None:
            wf.resume_token.used = True

        self._transition(wf, WorkflowState.RUNNING, reason="resume_token_accepted")
        return wf

    def approve(self, workflow_id: str) -> Workflow:
        """Approve the current step and continue execution.

        Marks the paused step as completed, advances the index, and
        transitions back to RUNNING (or COMPLETED if last step).

        Args:
            workflow_id: UUID of the workflow.

        Returns:
            Updated Workflow (RUNNING or COMPLETED).

        Raises:
            KeyError:   If workflow_id is not found.
            ValueError: If workflow is not in PAUSED or WAITING_APPROVAL state.
        """
        wf = self._get(workflow_id)

        if wf.state not in (WorkflowState.PAUSED, WorkflowState.WAITING_APPROVAL):
            raise ValueError(
                f"Cannot approve workflow in state {wf.state.value!r}. "
                "Workflow must be PAUSED or WAITING_APPROVAL."
            )

        self._transition(wf, WorkflowState.APPROVED, reason="step_approved")

        # Complete the step that was waiting for approval
        if wf.current_step_index < len(wf.steps):
            step = wf.steps[wf.current_step_index]
            if not step.started_at:
                step.started_at = _now_iso()
            step.result = {
                "status": "approved_and_executed",
                "action": step.action,
                "target": step.target,
                "value": step.value,
            }
            step.completed = True
            step.completed_at = _now_iso()

            wf.evidence.append({
                "step_id": step.step_id,
                "action": step.action,
                "target": step.target,
                "completed_at": step.completed_at,
                "result": step.result,
                "approved": True,
            })

            wf.current_step_index += 1

        # Transition to COMPLETED or back to RUNNING
        if wf.current_step_index >= len(wf.steps):
            wf.completed_at = _now_iso()
            self._transition(wf, WorkflowState.COMPLETED, reason="all_steps_completed")
        else:
            self._transition(wf, WorkflowState.RUNNING, reason="step_approved_continuing")

        return wf

    def reject(self, workflow_id: str, reason: str = "") -> Workflow:
        """Reject the current step and fail the workflow.

        Args:
            workflow_id: UUID of the workflow.
            reason:      Human-readable rejection reason (optional).

        Returns:
            Updated Workflow in REJECTED then FAILED state.

        Raises:
            KeyError:   If workflow_id is not found.
            ValueError: If workflow is not in PAUSED or WAITING_APPROVAL state.
        """
        wf = self._get(workflow_id)

        if wf.state not in (WorkflowState.PAUSED, WorkflowState.WAITING_APPROVAL):
            raise ValueError(
                f"Cannot reject workflow in state {wf.state.value!r}. "
                "Workflow must be PAUSED or WAITING_APPROVAL."
            )

        reject_reason = reason or "step_rejected_by_user"
        self._transition(wf, WorkflowState.REJECTED, reason=reject_reason)
        self._transition(wf, WorkflowState.FAILED, reason="workflow_failed_on_rejection")

        wf.evidence.append({
            "event": "rejected",
            "reason": reject_reason,
            "rejected_at": _now_iso(),
            "step_index": wf.current_step_index,
        })

        return wf

    def cancel(self, workflow_id: str) -> Workflow:
        """Cancel a running or paused workflow.

        Cancellation is allowed from: PENDING, RUNNING, PAUSED, WAITING_APPROVAL.
        Existing evidence is preserved.

        Args:
            workflow_id: UUID of the workflow.

        Returns:
            Updated Workflow in CANCELLED state.

        Raises:
            KeyError:   If workflow_id is not found.
            ValueError: If the workflow is in a terminal state
                        (COMPLETED, FAILED, REJECTED, CANCELLED).
        """
        wf = self._get(workflow_id)

        terminal = {
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.REJECTED,
            WorkflowState.CANCELLED,
        }
        if wf.state in terminal:
            raise ValueError(
                f"Cannot cancel workflow in terminal state {wf.state.value!r}."
            )

        self._transition(wf, WorkflowState.CANCELLED, reason="workflow_cancelled")
        return wf

    def get_status(self, workflow_id: str) -> dict:
        """Return workflow status with progress percentage.

        Args:
            workflow_id: UUID of the workflow.

        Returns:
            dict with:
                workflow_id, recipe_id, user_id, state, progress_pct,
                current_step_index, total_steps, created_at, started_at,
                completed_at, paused_at, steps_completed, steps_remaining,
                transitions_count, has_resume_token

        Raises:
            KeyError: If workflow_id is not found.
        """
        wf = self._get(workflow_id)
        total = len(wf.steps)
        done = wf.current_step_index
        pct = int((done / total) * 100) if total > 0 else 0

        return {
            "workflow_id": wf.workflow_id,
            "recipe_id": wf.recipe_id,
            "user_id": wf.user_id,
            "token_id": wf.token_id,
            "state": wf.state.value,
            "progress_pct": pct,
            "current_step_index": wf.current_step_index,
            "total_steps": total,
            "steps_completed": done,
            "steps_remaining": max(0, total - done),
            "created_at": wf.created_at,
            "started_at": wf.started_at,
            "completed_at": wf.completed_at,
            "paused_at": wf.paused_at,
            "transitions_count": len(wf.transitions),
            "has_resume_token": wf.resume_token is not None,
        }

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get(self, workflow_id: str) -> Workflow:
        """Retrieve a workflow by ID, raising KeyError if not found."""
        try:
            return self._workflows[workflow_id]
        except KeyError:
            raise KeyError(f"Workflow not found: {workflow_id!r}")

    def _transition(
        self,
        workflow: Workflow,
        new_state: WorkflowState,
        reason: str = "",
    ) -> None:
        """Record a state transition in the workflow's append-only audit log.

        Mutates workflow.state to new_state and appends a transition record
        with: from_state, to_state, timestamp, reason.

        Args:
            workflow:  The Workflow to transition.
            new_state: Target WorkflowState.
            reason:    Human-readable reason for the transition.
        """
        old_state = workflow.state
        workflow.state = new_state
        workflow.transitions.append({
            "from_state": old_state.value,
            "to_state": new_state.value,
            "timestamp": _now_iso(),
            "reason": reason,
        })

    def _generate_resume_token(
        self,
        workflow: Workflow,
        ttl_seconds: int = RESUME_TOKEN_TTL_SECONDS,
    ) -> ResumeToken:
        """Generate a cryptographic HMAC-SHA256 resume token for a paused workflow.

        The current step_id is embedded in the token so that attempts to
        resume at a different step fail hash validation.

        Args:
            workflow:    The paused Workflow.
            ttl_seconds: Token lifetime in seconds (default: 3600).

        Returns:
            A new ResumeToken (not yet stored on the workflow — caller does that).
        """
        token_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        created_at = now.isoformat()

        # Determine the step_id we're pausing on
        if workflow.current_step_index < len(workflow.steps):
            step_id = workflow.steps[workflow.current_step_index].step_id
        else:
            step_id = "end"

        token_hash = _compute_token_hash(
            token_id=token_id,
            workflow_id=workflow.workflow_id,
            step_id=step_id,
            secret=self._secret,
        )

        return ResumeToken(
            token_id=token_id,
            workflow_id=workflow.workflow_id,
            step_id=step_id,
            created_at=created_at,
            expires_at=expires_at,
            token_hash=token_hash,
            used=False,
        )

    def _validate_resume_token(
        self,
        workflow: Workflow,
        token_id: str,
    ) -> bool:
        """Validate a resume token for the given workflow.

        Checks (all must pass):
          1. Workflow has a resume_token attached.
          2. token_id matches the stored resume token.
          3. Token has not been used yet.
          4. Token has not expired (TTL check against UTC now).
          5. HMAC-SHA256 hash is intact (tamper detection).

        Args:
            workflow: The Workflow whose resume token to validate.
            token_id: The token_id presented by the caller.

        Returns:
            True if all checks pass; False otherwise (fail-closed).
        """
        rt = workflow.resume_token
        if rt is None:
            return False

        # Check token_id matches
        if rt.token_id != token_id:
            return False

        # Check already-used (single-use guarantee)
        if rt.used:
            return False

        # Check not expired
        try:
            expires_at = _parse_iso(rt.expires_at)
        except (ValueError, AttributeError):
            return False

        now = datetime.now(timezone.utc)
        if now > expires_at:
            return False

        # Verify HMAC hash integrity
        expected_hash = _compute_token_hash(
            token_id=rt.token_id,
            workflow_id=rt.workflow_id,
            step_id=rt.step_id,
            secret=self._secret,
        )
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(rt.token_hash, expected_hash):
            return False

        return True
