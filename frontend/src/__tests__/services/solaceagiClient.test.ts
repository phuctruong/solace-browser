import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  browserApiEndpoint,
  createApprovalRecord,
  createStripeSession,
  listRuns,
  loadInboxCustomization,
  pingSession,
  registerBrowser,
  setByokKey,
  syncEvidence,
} from "../../services/solaceagiClient";

describe("solaceagiClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("registerBrowser falls back on request failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    const result = await registerBrowser("user_1", "u@example.com");
    expect(result.apiKey).toBe("sk_browser_local_dev");
  });

  it("registerBrowser returns server payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ apiKey: "sk_browser_remote", deviceId: "dev123" }),
      }),
    );
    const result = await registerBrowser("user_1", "u@example.com");
    expect(result).toEqual({ apiKey: "sk_browser_remote", deviceId: "dev123" });
  });

  it("setByokKey accepts sk prefix", async () => {
    await expect(setByokKey("sk-abc")).resolves.toEqual({ ok: true });
  });

  it("setByokKey accepts claude prefix", async () => {
    await expect(setByokKey("claude-abc")).resolves.toEqual({ ok: true });
  });

  it("setByokKey rejects invalid key", async () => {
    await expect(setByokKey("invalid")).rejects.toThrow("Invalid API key format");
  });

  it("createStripeSession returns generated values", async () => {
    const result = await createStripeSession("Dragon Warrior $8/month");
    expect(result.sessionId).toContain("cs_");
    expect(result.checkoutUrl).toContain("/billing/checkout/");
  });

  it("createApprovalRecord returns approval object", async () => {
    const preview = { steps: 2, scopes: ["browser.read"], estimatedCostUsd: 0.05, estimatedDurationSec: 9 };
    const result = await createApprovalRecord(preview, "approve");
    expect(result.decision).toBe("approve");
    expect(result.preview.steps).toBe(2);
  });

  it("syncEvidence returns synced true", async () => {
    const result = await syncEvidence({
      runId: "run_1",
      appId: "gmail",
      events: [
        {
          timestamp: "2026-02-26T10:00:00.000Z",
          action: "X",
          data: {},
          prevHash: "",
          eventHash: "h",
        },
      ],
      screenshots: [],
      manifestHash: "m",
    });
    expect(result).toEqual({ synced: true, runId: "run_1" });
  });

  it("syncEvidence rejects empty bundle", async () => {
    await expect(
      syncEvidence({ runId: "run_1", appId: "gmail", events: [], screenshots: [], manifestHash: "m" }),
    ).rejects.toThrow("Cannot sync empty evidence bundle");
  });

  it("pingSession validates browser keys", async () => {
    await expect(pingSession("sk_browser_abc")).resolves.toEqual({ valid: true });
  });

  it("pingSession validates local dev key", async () => {
    await expect(pingSession("sk_browser_local_dev")).resolves.toEqual({ valid: true });
  });

  it("listRuns returns array", async () => {
    await expect(listRuns()).resolves.toEqual([]);
  });

  it("builds /api/v1/browser endpoint paths", () => {
    expect(browserApiEndpoint("execute")).toContain("/api/v1/browser/execute");
    expect(browserApiEndpoint("/status")).toContain("/api/v1/browser/status");
  });

  it("applies inbox customization overrides from localStorage", () => {
    localStorage.setItem("solace.inbox.gmail", JSON.stringify({ retries: 3, label: "urgent" }));
    const result = loadInboxCustomization("gmail", { retries: 1, mode: "safe" });
    expect(result).toEqual({ retries: 3, mode: "safe", label: "urgent" });
  });

  it("falls back to defaults when inbox override invalid json", () => {
    localStorage.setItem("solace.inbox.gmail", "{invalid");
    const result = loadInboxCustomization("gmail", { retries: 1, mode: "safe" });
    expect(result).toEqual({ retries: 1, mode: "safe" });
  });
});
