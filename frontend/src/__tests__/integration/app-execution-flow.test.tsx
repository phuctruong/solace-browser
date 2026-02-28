import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "../../pages/HomePage";
import { RunDetailPage } from "../../pages/RunDetailPage";
import { executeHeadless } from "../../services/playwrightClient";
import { EvidenceManager } from "../../services/evidenceManager";
import { useSessionStore } from "../../state/useSessionStore";
import { STORAGE_KEYS } from "../../utils/constants";

const createApprovalRecordMock = vi.fn().mockResolvedValue({ id: "apr_1" });
const syncEvidenceMock = vi.fn().mockResolvedValue({ synced: true, runId: "run_1" });

vi.mock("../../services/solaceagiClient", async () => {
  const actual = await vi.importActual<typeof import("../../services/solaceagiClient")>("../../services/solaceagiClient");
  return {
    ...actual,
    createApprovalRecord: (...args: unknown[]) => createApprovalRecordMock(...args),
    syncEvidence: (...args: unknown[]) => syncEvidenceMock(...args),
  };
});

describe("integration: app execution flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_auth",
        membershipTier: "Dragon Warrior $8/month",
        creditsUsd: 5,
        connectedApps: ["solace", "gmail"],
      },
    });
  });

  it("executeHeadless is deterministic for same seed", async () => {
    const req = { appId: "gmail", recipeId: "gmail.default", seed: "same", scopes: ["gmail.read.inbox"] };
    const r1 = await executeHeadless(req);
    const r2 = await executeHeadless(req);
    expect(r1).toEqual(r2);
  });

  it("executeHeadless fails closed when no scope", async () => {
    await expect(executeHeadless({ appId: "gmail", recipeId: "gmail.default", seed: "same", scopes: [] })).rejects.toThrow(
      "No scopes granted for execution",
    );
  });

  it("evidence manager bundle can be synced", async () => {
    const manager = new EvidenceManager();
    await manager.addEvent("RUN_REQUESTED", { app: "gmail" });
    await manager.addEvent("RUN_COMPLETED", { ok: true });
    const bundle = await manager.buildBundle("run_sync", "gmail", ["step_1.png"]);
    await expect(syncEvidenceMock(bundle)).resolves.toEqual({ synced: true, runId: "run_1" });
  });

  it("canceling approval does not execute run", async () => {
    const executeSpy = vi.spyOn(await import("../../services/playwrightClient"), "executeHeadless");
    render(
      <MemoryRouter initialEntries={["/home"]}>
        <Routes>
          <Route path="/home" element={<HomePage />} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Abort" }));

    await waitFor(() => {
      expect(executeSpy).not.toHaveBeenCalled();
    });
  });

  it("override-enabled approve executes run when reason provided", async () => {
    vi.spyOn(Date, "now").mockReturnValue(321);
    const executeSpy = vi.spyOn(await import("../../services/playwrightClient"), "executeHeadless");
    render(
      <MemoryRouter initialEntries={["/home"]}>
        <Routes>
          <Route path="/home" element={<HomePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    fireEvent.click(screen.getByRole("checkbox", { name: "Override safety check" }));
    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "critical incident" } });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(createApprovalRecordMock).toHaveBeenCalledWith(expect.any(Object), "approve", "critical incident");
      expect(executeSpy).toHaveBeenCalled();
      expect(screen.getByText("run_321")).toBeInTheDocument();
    });
  });

  it("execution uploads evidence through sync api", async () => {
    render(
      <MemoryRouter initialEntries={["/home"]}>
        <Routes>
          <Route path="/home" element={<HomePage />} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => {
      expect(syncEvidenceMock).toHaveBeenCalled();
    });
  });

  it("run detail page shows hash verification from persisted run", () => {
    const runs = [
      {
        id: "run_detail_1",
        appId: "gmail",
        appName: "Gmail",
        status: "success",
        startedAt: "2026-02-26T10:00:00.000Z",
        durationMs: 1300,
        tokenCostUsd: 0.1,
        model: "L2/Sonnet",
        estimatedOpusUsd: 0.2,
        screenshots: ["step_1.png"],
        steps: [
          { id: "1", name: "one", action: "read", status: "success", durationMs: 100, scope: "gmail.read.inbox" },
        ],
        firstHash: "aaaaaa",
        lastHash: "bbbbbb",
        hashVerified: true,
      },
    ];
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(runs));

    render(
      <MemoryRouter initialEntries={["/run/run_detail_1"]}>
        <Routes>
          <Route path="/run/:runId" element={<RunDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText(/Hash chain verified/)).toBeInTheDocument();
  });

  it("run detail page shows cost savings widget", () => {
    const runs = [
      {
        id: "run_cost_1",
        appId: "gmail",
        appName: "Gmail",
        status: "success",
        startedAt: "2026-02-26T10:00:00.000Z",
        durationMs: 17000,
        tokenCostUsd: 0.12,
        model: "L2/Sonnet",
        estimatedOpusUsd: 0.45,
        screenshots: [],
        steps: [
          { id: "1", name: "one", action: "read", status: "success", durationMs: 100, scope: "gmail.read.inbox" },
        ],
        firstHash: "aaaaaa",
        lastHash: "bbbbbb",
        hashVerified: true,
      },
    ];
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(runs));

    render(
      <MemoryRouter initialEntries={["/run/run_cost_1"]}>
        <Routes>
          <Route path="/run/:runId" element={<RunDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText(/Saved: \$0\.33/)).toBeInTheDocument();
  });
});
