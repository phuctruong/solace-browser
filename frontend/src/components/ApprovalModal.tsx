import { useEffect, useState } from "react";
import type { ApprovalPreview } from "../types/Approval";

interface ApprovalModalProps {
  open: boolean;
  preview: ApprovalPreview;
  onDecision: (decision: "approve" | "override" | "cancel", reason?: string) => void;
  autoDenySeconds?: number;
}

export function ApprovalModal({
  open,
  preview,
  onDecision,
  autoDenySeconds = 30,
}: ApprovalModalProps): JSX.Element | null {
  const [reason, setReason] = useState("");
  const [timeLeft, setTimeLeft] = useState(autoDenySeconds);

  useEffect(() => {
    if (!open) {
      setReason("");
      setTimeLeft(autoDenySeconds);
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
      onDecision("cancel");
    }
  }, [open, timeLeft, onDecision]);

  if (!open) {
    return null;
  }

  const canOverride = reason.trim().length > 3;

  return (
    <div role="dialog" aria-label="Approval Required" className="modal">
      <h3>Approve & Run</h3>
      <p>Steps: {preview.steps}</p>
      <p>Scopes: {preview.scopes.join(", ")}</p>
      <p>Est. Cost: ${preview.estimatedCostUsd.toFixed(2)}</p>
      <p>Est. Duration: {preview.estimatedDurationSec}s</p>
      <p>Auto-deny in {timeLeft}s</p>
      <textarea
        aria-label="Override reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Required for override"
      />
      <div className="actions">
        <button type="button" onClick={() => onDecision("approve")}>APPROVE & RUN</button>
        <button type="button" onClick={() => onDecision("override", reason)} disabled={!canOverride}>
          OVERRIDE & EXPLAIN
        </button>
        <button type="button" onClick={() => onDecision("cancel")}>CANCEL</button>
      </div>
    </div>
  );
}
