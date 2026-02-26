export interface ApprovalPreview {
  steps: number;
  scopes: string[];
  estimatedCostUsd: number;
  estimatedDurationSec: number;
}

export interface ApprovalRecord {
  id: string;
  approvedAt: string;
  decision: "approve" | "override" | "cancel";
  reason?: string;
  approver: string;
  preview: ApprovalPreview;
}
