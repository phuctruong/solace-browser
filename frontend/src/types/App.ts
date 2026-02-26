export type AppStatus = "locked" | "connected" | "error";

export interface AppModel {
  id: string;
  name: string;
  icon: string;
  status: AppStatus;
  lastRunAt?: string;
  budgetRemaining?: number;
  oauthUrl?: string;
  scopes: string[];
}
