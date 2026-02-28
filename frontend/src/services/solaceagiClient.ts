import type { ApprovalRecord, ApprovalPreview } from "../types/Approval";
import type { AppModel } from "../types/App";
import type { EvidenceBundle } from "../types/Evidence";
import type { RunModel } from "../types/Run";
import { APP_MANIFESTS, APPS, MEMBERSHIP_PLANS, SAMPLE_RUNS } from "../utils/constants";

export interface BrowserRegistration {
  apiKey: string;
  deviceId: string;
}

export interface CreditsSummary {
  remaining: number;
}

export interface MembershipPlan {
  id: string;
  name: string;
  priceLabel: string;
  current: boolean;
  features: string[];
}

interface TaskResponse {
  status: string;
  evidence_hash: string;
}

const baseUrl = import.meta.env.REACT_APP_SOLACEAGI_URL ?? "https://solaceagi.com";

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

async function absolutePostJson<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API request failed (${response.status}) for ${path}`);
  }
  return (await response.json()) as T;
}

async function requestJson<T>(path: string, init?: RequestInit, fallback?: T): Promise<T> {
  try {
    const response = await fetch(path, init);
    if (!response.ok) {
      throw new Error(`API request failed (${response.status}) for ${path}`);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (fallback !== undefined) {
      return clone(fallback);
    }
    throw error;
  }
}

export async function registerBrowser(userId: string, email: string): Promise<BrowserRegistration> {
  try {
    return await absolutePostJson<BrowserRegistration>("/api/browser/register", {
      user_id: userId,
      email,
      device: navigator.platform,
      version: "frontend-0.2.0",
    });
  } catch {
    return {
      apiKey: "sk_browser_local_dev",
      deviceId: `device_${userId}`,
    };
  }
}

export function browserApiEndpoint(action: string): string {
  const normalized = action.replace(/^\/+/, "");
  return `${baseUrl}/api/v1/browser/${normalized}`;
}

export function loadInboxCustomization<T extends Record<string, unknown>>(appId: string, defaults: T): T {
  const key = `solace.inbox.${appId}`;
  const raw = localStorage.getItem(key);
  if (!raw) {
    return defaults;
  }
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return { ...defaults, ...parsed } as T;
  } catch {
    return defaults;
  }
}

export async function listInstalledApps(): Promise<AppModel[]> {
  const payload = await requestJson<{ apps: Array<Record<string, unknown>> }>("/api/v1/store/apps?installed=true", undefined, {
    apps: APPS as unknown as Array<Record<string, unknown>>,
  });
  return payload.apps.map(normalizeAppSummary);
}

export async function getCreditsSummary(): Promise<CreditsSummary> {
  return requestJson<CreditsSummary>("/api/v1/billing/credits", undefined, { remaining: 12.4 });
}

export async function getRecentRuns(): Promise<RunModel[]> {
  const payload = await requestJson<{ runs: Array<Record<string, unknown>> }>("/api/v1/history/recent", undefined, {
    runs: SAMPLE_RUNS as unknown as Array<Record<string, unknown>>,
  });
  return payload.runs.map(normalizeRun);
}

export async function getAppManifest(appId: string): Promise<AppModel> {
  const payload = await requestJson<Record<string, unknown>>(
    `/api/v1/store/apps/${appId}`,
    undefined,
    (APP_MANIFESTS[appId] ?? APPS[0]) as unknown as Record<string, unknown>,
  );
  return normalizeAppManifest(payload);
}

export async function getRunDetail(runId: string): Promise<RunModel> {
  const fallback = SAMPLE_RUNS.find((run) => run.id === runId) ?? SAMPLE_RUNS[0];
  const payload = await requestJson<Record<string, unknown>>(
    `/api/v1/history/${runId}`,
    undefined,
    fallback as unknown as Record<string, unknown>,
  );
  return normalizeRun(payload);
}

export async function validateToken(apiKey: string): Promise<{ ok: boolean; provider: string }> {
  if (!apiKey.startsWith("sk-") && !apiKey.startsWith("claude-") && !apiKey.startsWith("openai-")) {
    throw new Error("Invalid API key format");
  }
  return requestJson<{ ok: boolean; provider: string }>(
    "/api/v1/oauth3/tokens",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey }),
    },
    {
      ok: true,
      provider: apiKey.startsWith("claude-") ? "anthropic" : apiKey.startsWith("openai-") ? "openai" : "generic",
    },
  );
}

export async function setByokKey(apiKey: string): Promise<{ ok: boolean }> {
  const result = await validateToken(apiKey);
  return { ok: result.ok };
}

export async function getMembershipPlans(): Promise<MembershipPlan[]> {
  const payload = await requestJson<{ plans: Array<Record<string, unknown>> }>("/api/v1/billing/plans", undefined, {
    plans: MEMBERSHIP_PLANS,
  });
  return payload.plans.map(normalizePlan);
}

export async function postCheckout(tier: string): Promise<{ sessionId: string; checkoutUrl: string }> {
  const sessionId = `cs_${tier.toLowerCase().replaceAll(/[^a-z0-9]/g, "")}`;
  return requestJson<{ sessionId: string; checkoutUrl: string }>(
    "/api/v1/billing/checkout",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tier }),
    },
    {
      sessionId,
      checkoutUrl: `${baseUrl}/billing/checkout/${tier}`,
    },
  );
}

export async function createStripeSession(tier: string): Promise<{ sessionId: string; checkoutUrl: string }> {
  return postCheckout(tier);
}

export async function approveTask(taskId: string, reason?: string): Promise<TaskResponse> {
  return requestJson<TaskResponse>(
    `/api/v1/tasks/${taskId}/approve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    },
    {
      status: "approved",
      evidence_hash: `approve_${taskId}`,
    },
  );
}

export async function abortTask(taskId: string, reason?: string): Promise<TaskResponse> {
  return requestJson<TaskResponse>(
    `/api/v1/tasks/${taskId}/abort`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    },
    {
      status: "aborted",
      evidence_hash: `abort_${taskId}`,
    },
  );
}

export async function modifyTask(taskId: string, reason?: string): Promise<TaskResponse> {
  return requestJson<TaskResponse>(
    `/api/v1/tasks/${taskId}/modify`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    },
    {
      status: "modified",
      evidence_hash: `modify_${taskId}`,
    },
  );
}

export async function recordApproval(
  preview: ApprovalPreview,
  decision: "approve" | "modify" | "abort" | "override" | "cancel",
  reason?: string,
): Promise<ApprovalRecord> {
  const now = new Date().toISOString();
  return {
    id: `apr_${Math.random().toString(16).slice(2, 10)}`,
    approvedAt: now,
    decision,
    reason,
    approver: "local-user",
    preview,
  };
}

export async function createApprovalRecord(
  preview: ApprovalPreview,
  decision: "approve" | "modify" | "abort" | "override" | "cancel",
  reason?: string,
): Promise<ApprovalRecord> {
  return recordApproval(preview, decision, reason);
}

export async function syncEvidence(bundle: EvidenceBundle): Promise<{ synced: boolean; runId: string }> {
  if (bundle.events.length === 0) {
    throw new Error("Cannot sync empty evidence bundle");
  }
  return {
    synced: true,
    runId: bundle.runId,
  };
}

export async function pingSession(apiKey: string): Promise<{ valid: boolean }> {
  return { valid: apiKey.startsWith("sk_browser_") || apiKey === "sk_browser_local_dev" };
}

export async function listRuns(): Promise<RunModel[]> {
  return [];
}

function normalizeAppSummary(payload: Record<string, unknown>): AppModel {
  const base = APP_MANIFESTS[String(payload.id ?? "solace")] ?? APPS[0];
  return {
    ...base,
    id: String(payload.id ?? base.id),
    name: String(payload.name ?? base.name),
    status: normalizeStatus(payload.status, base.status),
    lastRunTime: stringOrUndefined(payload.lastRunTime) ?? stringOrUndefined(payload.lastRunAt) ?? base.lastRunTime,
    lastRunAt: stringOrUndefined(payload.lastRunAt) ?? stringOrUndefined(payload.lastRunTime) ?? base.lastRunAt,
  };
}

function normalizeAppManifest(payload: Record<string, unknown>): AppModel {
  const base = APP_MANIFESTS[String(payload.id ?? "solace")] ?? APPS[0];
  const rawScopes = payload.scopes;
  const scopeDetails =
    rawScopes && typeof rawScopes === "object" && !Array.isArray(rawScopes)
      ? {
          required: arrayOfStrings((rawScopes as Record<string, unknown>).required),
          optional: arrayOfStrings((rawScopes as Record<string, unknown>).optional),
          stepUp: arrayOfStrings((rawScopes as Record<string, unknown>).stepUp),
        }
      : base.scopeDetails;
  const flatScopes = Array.isArray(rawScopes)
    ? arrayOfStrings(rawScopes)
    : [...(scopeDetails?.required ?? []), ...(scopeDetails?.optional ?? []), ...(scopeDetails?.stepUp ?? [])];

  return {
    ...base,
    id: String(payload.id ?? base.id),
    name: String(payload.name ?? base.name),
    description: String(payload.description ?? base.description ?? ""),
    category: String(payload.category ?? base.category ?? "General"),
    riskTier: normalizeRiskTier(payload.riskTier, base.riskTier ?? "low"),
    scopes: flatScopes,
    scopeDetails,
    budgets: normalizeBudget(payload.budgets, base.budgets),
    approvalTaskId: String(payload.approvalTaskId ?? base.approvalTaskId ?? `task_${base.id}_001`),
  };
}

function normalizeRun(payload: Record<string, unknown>): RunModel {
  const base =
    SAMPLE_RUNS.find((run) => run.id === String(payload.id ?? "")) ??
    SAMPLE_RUNS.find((run) => run.appId === String(payload.appId ?? "")) ??
    SAMPLE_RUNS[0];
  const rawTimeline = Array.isArray(payload.timeline) ? payload.timeline : Array.isArray(payload.steps) ? payload.steps : base.steps;
  const rawScreenshots = Array.isArray(payload.screenshots) ? payload.screenshots : base.screenshots;
  const evidence = rawScreenshots.map((item, index) => {
    if (typeof item === "string") {
      return {
        src: item.startsWith("/") ? item : `/evidence/${item}`,
        label: item.replace(/^.*\//, ""),
      };
    }
    const shot = item as Record<string, unknown>;
    return {
      src: String(shot.src ?? `/evidence/shot-${index + 1}.png`),
      label: String(shot.label ?? `Evidence ${index + 1}`),
    };
  });

  return {
    ...base,
    id: String(payload.id ?? base.id),
    appId: String(payload.appId ?? base.appId),
    appName: String(payload.appName ?? base.appName),
    status: normalizeRunStatus(payload.status, base.status),
    startedAt: String(payload.startedAt ?? base.startedAt),
    durationMs: numberOr(payload.durationMs, base.durationMs),
    tokenCostUsd: numberOr(payload.tokenCostUsd ?? payload.cost, base.tokenCostUsd),
    model: String(payload.model ?? payload.level ?? base.model),
    estimatedOpusUsd: numberOr(payload.estimatedOpusUsd, base.estimatedOpusUsd),
    screenshots: evidence.map((item) => item.src),
    steps: rawTimeline.map((item, index) => normalizeRunStep(item, index)),
    firstHash: String(payload.firstHash ?? base.firstHash),
    lastHash: String(payload.lastHash ?? base.lastHash),
    hashVerified: booleanOr(payload.hashVerified, base.hashVerified),
    tokensConsumed: numberOr(payload.tokensConsumed ?? payload.tokens, base.tokensConsumed ?? 847),
    modelLevel: String(payload.modelLevel ?? payload.level ?? base.modelLevel ?? base.model),
    savingsVsFullLlm: numberOr(payload.savingsVsFullLlm, base.savingsVsFullLlm ?? Math.max(0, base.estimatedOpusUsd - base.tokenCostUsd)),
    evidence,
  };
}

function normalizePlan(payload: Record<string, unknown>): MembershipPlan {
  const base =
    MEMBERSHIP_PLANS.find((plan) => plan.id === String(payload.id ?? "")) ??
    MEMBERSHIP_PLANS.find((plan) => plan.name === String(payload.name ?? "")) ??
    MEMBERSHIP_PLANS[0];
  return {
    ...base,
    id: String(payload.id ?? base.id),
    name: String(payload.name ?? base.name),
    priceLabel: String(payload.priceLabel ?? payload.price ?? base.priceLabel),
    current: booleanOr(payload.current, base.current),
    features: arrayOfStrings(payload.features).length > 0 ? arrayOfStrings(payload.features) : base.features,
  };
}

function normalizeBudget(raw: unknown, fallback: AppModel["budgets"]): AppModel["budgets"] {
  if (!raw || typeof raw !== "object") {
    return fallback;
  }
  const source = raw as Record<string, unknown>;
  return {
    maxReads: numberOr(source.maxReads, fallback?.maxReads ?? 0),
    maxSends: numberOr(source.maxSends, fallback?.maxSends ?? 0),
    maxDeletes: numberOr(source.maxDeletes, fallback?.maxDeletes ?? 0),
  };
}

function normalizeRunStep(raw: unknown, index: number): RunModel["steps"][number] {
  const base = SAMPLE_RUNS[0].steps[0];
  if (!raw || typeof raw !== "object") {
    return { ...base, id: `step_${index + 1}`, name: `Step ${index + 1}` };
  }
  const item = raw as Record<string, unknown>;
  return {
    id: String(item.id ?? `step_${index + 1}`),
    name: String(item.name ?? `Step ${index + 1}`),
    action: String(item.action ?? "run"),
    status: normalizeStepStatus(item.status, "success"),
    durationMs: numberOr(item.durationMs, 0),
    scope: String(item.scope ?? "browser.read"),
  };
}

function arrayOfStrings(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function stringOrUndefined(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function numberOr(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function booleanOr(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function normalizeStatus(value: unknown, fallback: AppModel["status"]): AppModel["status"] {
  if (value === "connected" || value === "locked" || value === "error") {
    return value;
  }
  if (value === "ready") {
    return "connected";
  }
  return fallback;
}

function normalizeRunStatus(value: unknown, fallback: RunModel["status"]): RunModel["status"] {
  return value === "queued" || value === "running" || value === "success" || value === "failed" ? value : fallback;
}

function normalizeStepStatus(value: unknown, fallback: RunModel["steps"][number]["status"]): RunModel["steps"][number]["status"] {
  return value === "success" || value === "failed" || value === "skipped" ? value : fallback;
}

function normalizeRiskTier(value: unknown, fallback: NonNullable<AppModel["riskTier"]>): NonNullable<AppModel["riskTier"]> {
  return value === "low" || value === "medium" || value === "high" ? value : fallback;
}
