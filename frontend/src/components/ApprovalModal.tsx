import { useEffect, useState } from "react";
import type { ApprovalPreview } from "../types/Approval";
import { abortTask, approveTask, modifyTask } from "../services/solaceagiClient";
import { LoadingSpinner } from "./LoadingSpinner";

interface ApprovalModalProps {
  open: boolean;
  preview: ApprovalPreview;
  onDecision?: (decision: "approve" | "modify" | "abort", reason?: string) => Promise<void> | void;
  taskId?: string;
  onClose?: () => void;
  autoDenySeconds?: number;
}

export function ApprovalModal({
  open,
  preview,
  onDecision,
  taskId,
  onClose,
  autoDenySeconds = 30,
}: ApprovalModalProps): JSX.Element | null {
  const [reason, setReason] = useState("");
  const [overrideEnabled, setOverrideEnabled] = useState(false);
  const [timeLeft, setTimeLeft] = useState(autoDenySeconds);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setReason("");
      setOverrideEnabled(false);
      setTimeLeft(autoDenySeconds);
      setBusy(false);
      setError(null);
      return;
    }
    setTimeLeft(autoDenySeconds);
    const timer = window.setInterval(() => {
      setTimeLeft((value) => Math.max(0, value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [open, autoDenySeconds]);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (timeLeft === 0) {
      void handleDecision("abort");
    }
  }, [open, timeLeft]);

  if (!open) {
    return null;
  }

  const canSubmitReason = !overrideEnabled || reason.trim().length >= 4;

  async function handleDecision(decision: "approve" | "modify" | "abort"): Promise<void> {
    const submittedReason = overrideEnabled ? reason.trim() : undefined;
    if (!canSubmitReason) {
      setError("Override reason must be at least 4 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (taskId) {
        if (decision === "approve") {
          await approveTask(taskId, submittedReason);
        } else if (decision === "modify") {
          await modifyTask(taskId, submittedReason);
        } else {
          await abortTask(taskId, submittedReason);
        }
      }
      await onDecision?.(decision, submittedReason);
      onClose?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-shell" role="presentation">
      <div className="modal-backdrop" onClick={onClose} />
      <div role="dialog" aria-label="Approval Required" className="modal">
        <h3>Approve & Run</h3>
        <p className="modal-copy">Review the exact scopes, steps, and cost before Solace executes this task.</p>
        <div className="approval-grid">
          <div>
            <strong>Steps</strong>
            <p>{preview.steps}</p>
            {preview.stepLabels?.length ? (
              <ul className="approval-list">
                {preview.stepLabels.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            ) : null}
          </div>
          <div>
            <strong>Scopes</strong>
            <ul className="approval-list">
              {preview.scopes.map((scope) => (
                <li key={scope}>{scope}</li>
              ))}
            </ul>
          </div>
          <div>
            <strong>Cost estimate</strong>
            <p>${preview.estimatedCostUsd.toFixed(2)}</p>
            <p>{preview.estimatedDurationSec}s</p>
            <p>Auto-deny in {timeLeft}s</p>
          </div>
        </div>

        <label className="approval-toggle">
          <input
            type="checkbox"
            checked={overrideEnabled}
            onChange={(event) => setOverrideEnabled(event.target.checked)}
          />
          Override safety check
        </label>

        <textarea
          aria-label="Override reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Explain why this task should proceed"
          disabled={!overrideEnabled}
        />

        {error ? <p role="alert">{error}</p> : null}
        {busy ? <LoadingSpinner /> : null}

        <div className="actions">
          <button type="button" onClick={() => void handleDecision("approve")} disabled={busy}>
            Approve
          </button>
          <button type="button" onClick={() => void handleDecision("modify")} disabled={busy}>
            Modify
          </button>
          <button type="button" onClick={() => void handleDecision("abort")} disabled={busy}>
            Abort
          </button>
        </div>
      </div>
    </div>
  );
}
