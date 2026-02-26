export interface RunStep {
  id: string;
  name: string;
  action: string;
  status: "success" | "failed" | "skipped";
  durationMs: number;
  scope: string;
}

export interface RunModel {
  id: string;
  appId: string;
  appName: string;
  status: "queued" | "running" | "success" | "failed";
  startedAt: string;
  durationMs: number;
  tokenCostUsd: number;
  model: string;
  estimatedOpusUsd: number;
  screenshots: string[];
  steps: RunStep[];
  firstHash: string;
  lastHash: string;
  hashVerified: boolean;
}
