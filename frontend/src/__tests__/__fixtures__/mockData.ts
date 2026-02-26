import type { AppModel } from "../../types/App";
import type { ApprovalPreview } from "../../types/Approval";
import type { RunModel } from "../../types/Run";

export const mockApps: AppModel[] = [
  {
    id: "solace",
    name: "Solace",
    icon: "S",
    status: "connected",
    scopes: ["browser.read"],
  },
  {
    id: "gmail",
    name: "Gmail",
    icon: "G",
    status: "locked",
    oauthUrl: "https://accounts.google.com/o/oauth2/v2/auth",
    scopes: ["gmail.read.inbox", "gmail.draft.create"],
    budgetRemaining: 24,
  },
  {
    id: "linkedin",
    name: "LinkedIn",
    icon: "L",
    status: "error",
    oauthUrl: "https://www.linkedin.com/oauth/v2/authorization",
    scopes: ["linkedin.read.feed"],
    budgetRemaining: 12,
  },
];

export const mockRuns: RunModel[] = [
  {
    id: "run_alpha",
    appId: "gmail",
    appName: "Gmail",
    status: "success",
    startedAt: "2026-02-26T11:00:00.000Z",
    durationMs: 14000,
    tokenCostUsd: 0.12,
    model: "L2/Sonnet",
    estimatedOpusUsd: 0.45,
    screenshots: ["step_1.png", "step_2.png"],
    steps: [
      {
        id: "1",
        name: "Fetch inbox",
        action: "read",
        status: "success",
        durationMs: 5000,
        scope: "gmail.read.inbox",
      },
    ],
    firstHash: "abc111",
    lastHash: "def222",
    hashVerified: true,
  },
  {
    id: "run_beta",
    appId: "linkedin",
    appName: "LinkedIn",
    status: "failed",
    startedAt: "2026-02-26T12:00:00.000Z",
    durationMs: 900,
    tokenCostUsd: 0.03,
    model: "L2/Sonnet",
    estimatedOpusUsd: 0.15,
    screenshots: [],
    steps: [
      {
        id: "2",
        name: "Open feed",
        action: "read",
        status: "failed",
        durationMs: 900,
        scope: "linkedin.read.feed",
      },
    ],
    firstHash: "aaa000",
    lastHash: "bbb999",
    hashVerified: false,
  },
];

export const mockPreview: ApprovalPreview = {
  steps: 5,
  scopes: ["gmail.read.inbox", "gmail.draft.create"],
  estimatedCostUsd: 0.12,
  estimatedDurationSec: 18,
};
