import type { AppModel } from "../types/App";
import type { RunModel } from "../types/Run";
import type { AppBudget, AppScopeSet } from "../types/App";

export const STORAGE_KEYS = {
  SESSION: "solace.session",
  RUNS: "solace.runs",
  VAULT: "solace.vault",
} as const;

const GMAIL_SCOPES: AppScopeSet = {
  required: ["gmail.read.inbox"],
  optional: ["gmail.read.labels"],
  stepUp: ["gmail.send"],
};

const SLACK_SCOPES: AppScopeSet = {
  required: ["slack.read.channels"],
  optional: ["slack.read.users"],
  stepUp: ["slack.post.message"],
};

const GMAIL_BUDGETS: AppBudget = {
  maxReads: 25,
  maxSends: 5,
  maxDeletes: 0,
};

const SLACK_BUDGETS: AppBudget = {
  maxReads: 40,
  maxSends: 8,
  maxDeletes: 0,
};

export const APPS: AppModel[] = [
  {
    id: "solace",
    name: "Solace",
    icon: "S",
    status: "connected",
    scopes: ["browser.read", "browser.click"],
    description: "Reference browser control app for Solace Browser.",
    category: "Core",
    riskTier: "low",
    budgets: { maxReads: 50, maxSends: 0, maxDeletes: 0 },
    scopeDetails: {
      required: ["browser.read"],
      optional: ["browser.click"],
      stepUp: [],
    },
    approvalTaskId: "task_solace_001",
  },
  {
    id: "gmail",
    name: "Gmail",
    icon: "G",
    status: "locked",
    oauthUrl: "https://accounts.google.com/o/oauth2/v2/auth",
    scopes: ["gmail.read.inbox", "gmail.draft.create"],
    budgetRemaining: 24,
    description: "Triage inbox, draft replies, and capture evidence.",
    category: "Communication",
    riskTier: "medium",
    budgets: GMAIL_BUDGETS,
    scopeDetails: GMAIL_SCOPES,
    approvalTaskId: "task_gmail_001",
  },
  {
    id: "linkedin",
    name: "LinkedIn",
    icon: "L",
    status: "locked",
    oauthUrl: "https://www.linkedin.com/oauth/v2/authorization",
    scopes: ["linkedin.read.feed", "linkedin.post.create"],
    budgetRemaining: 12,
    description: "Review feed activity and prepare outbound post drafts.",
    category: "Social",
    riskTier: "high",
    budgets: { maxReads: 15, maxSends: 3, maxDeletes: 1 },
    scopeDetails: {
      required: ["linkedin.read.feed"],
      optional: ["linkedin.post.create"],
      stepUp: ["linkedin.post.delete"],
    },
    approvalTaskId: "task_linkedin_001",
  },
  {
    id: "slack",
    name: "Slack",
    icon: "#",
    status: "locked",
    oauthUrl: "https://slack.com/oauth/v2/authorize",
    scopes: ["slack.read.channels", "slack.post.message"],
    budgetRemaining: 30,
    description: "Summarize channel activity and draft follow-up notes.",
    category: "Collaboration",
    riskTier: "medium",
    budgets: SLACK_BUDGETS,
    scopeDetails: SLACK_SCOPES,
    approvalTaskId: "task_slack_001",
  },
];

export const APP_MANIFESTS: Record<string, AppModel> = Object.fromEntries(
  APPS.map((app) => [app.id, app]),
);

export const MEMBERSHIP_PLANS = [
  {
    id: "free",
    name: "Free",
    priceLabel: "$0",
    current: false,
    features: ["2 installed apps", "Manual approvals", "Local evidence bundle"],
  },
  {
    id: "pro",
    name: "Dragon Warrior",
    priceLabel: "$8/month",
    current: true,
    features: ["Unlimited apps", "Managed LLM routing", "Replay history + outbox"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    priceLabel: "$99/month",
    current: false,
    features: ["Policy controls", "Dedicated support", "Review queues + exports"],
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
    tokensConsumed: 847,
    modelLevel: "L2/Sonnet",
    savingsVsFullLlm: 0.33,
    evidence: [
      { src: "/evidence/step_1.png", label: "Inbox loaded" },
      { src: "/evidence/step_2.png", label: "Draft prepared" },
    ],
  },
];
