import type { AppModel } from "../types/App";
import type { RunModel } from "../types/Run";

export const STORAGE_KEYS = {
  SESSION: "solace.session",
  RUNS: "solace.runs",
  VAULT: "solace.vault",
} as const;

export const APPS: AppModel[] = [
  {
    id: "solace",
    name: "Solace",
    icon: "S",
    status: "connected",
    scopes: ["browser.read", "browser.click"],
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
    status: "locked",
    oauthUrl: "https://www.linkedin.com/oauth/v2/authorization",
    scopes: ["linkedin.read.feed", "linkedin.post.create"],
    budgetRemaining: 12,
  },
  {
    id: "slack",
    name: "Slack",
    icon: "#",
    status: "locked",
    oauthUrl: "https://slack.com/oauth/v2/authorize",
    scopes: ["slack.read.channels", "slack.post.message"],
    budgetRemaining: 30,
  },
];

export const SAMPLE_RUNS: RunModel[] = [
  {
    id: "run_001",
    appId: "gmail",
    appName: "Gmail",
    status: "success",
    startedAt: "2026-02-26T10:00:00.000Z",
    durationMs: 17000,
    tokenCostUsd: 0.12,
    model: "L2/Sonnet",
    estimatedOpusUsd: 0.45,
    screenshots: ["step_1.png", "step_2.png"],
    steps: [
      {
        id: "s1",
        name: "Fetch inbox",
        action: "read",
        status: "success",
        durationMs: 4100,
        scope: "gmail.read.inbox",
      },
      {
        id: "s2",
        name: "Draft response",
        action: "draft",
        status: "success",
        durationMs: 6800,
        scope: "gmail.draft.create",
      },
    ],
    firstHash: "f0b5b5",
    lastHash: "a93e12",
    hashVerified: true,
  },
];
