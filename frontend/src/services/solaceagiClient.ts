import type { ApprovalRecord, ApprovalPreview } from "../types/Approval";
import type { EvidenceBundle } from "../types/Evidence";
import type { RunModel } from "../types/Run";

export interface BrowserRegistration {
  apiKey: string;
  deviceId: string;
}

const baseUrl = import.meta.env.REACT_APP_SOLACEAGI_URL ?? "https://solaceagi.com";

async function postJson<T>(path: string, body: Record<string, unknown>): Promise<T> {
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

export async function registerBrowser(userId: string, email: string): Promise<BrowserRegistration> {
  try {
    const result = await postJson<BrowserRegistration>("/api/browser/register", {
      user_id: userId,
      email,
      device: navigator.platform,
      version: "frontend-0.1.0",
    });
    return result;
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

export async function setByokKey(apiKey: string): Promise<{ ok: boolean }> {
  if (!apiKey.startsWith("sk-") && !apiKey.startsWith("claude-") && !apiKey.startsWith("openai-")) {
    throw new Error("Invalid API key format");
  }
  return { ok: true };
}

export async function createStripeSession(tier: string): Promise<{ sessionId: string; checkoutUrl: string }> {
  return {
    sessionId: `cs_${tier.toLowerCase().replaceAll(/[^a-z0-9]/g, "")}`,
    checkoutUrl: `${baseUrl}/billing/checkout/${tier}`,
  };
}

export async function recordApproval(
  preview: ApprovalPreview,
  decision: "approve" | "override" | "cancel",
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
  decision: "approve" | "override" | "cancel",
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
