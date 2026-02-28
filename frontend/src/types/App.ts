export type AppStatus = "locked" | "connected" | "error";

export interface AppScopeSet {
  required: string[];
  optional: string[];
  stepUp: string[];
}

export interface AppBudget {
  maxReads: number;
  maxSends: number;
  maxDeletes: number;
}

export interface AppModel {
  id: string;
  name: string;
  icon: string;
  status: AppStatus;
  lastRunAt?: string;
  lastRunTime?: string;
  budgetRemaining?: number;
  oauthUrl?: string;
  scopes: string[];
  description?: string;
  category?: string;
  riskTier?: "low" | "medium" | "high";
  budgets?: AppBudget;
  scopeDetails?: AppScopeSet;
  approvalTaskId?: string;
}
