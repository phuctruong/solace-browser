export interface ApprovalPreview {
  steps: number;
  scopes: string[];
  estimatedCostUsd: number;
  estimatedDurationSec: number;
  stepLabels?: string[];
  taskId?: string;
}

export interface ApprovalRecord {
  id: string;
  approvedAt: string;
  decision: "approve" | "modify" | "abort" | "override" | "cancel";
  reason?: string;
  approver: string;
  preview: ApprovalPreview;
}
