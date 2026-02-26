import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "../../pages/HomePage";
import { LoginPage } from "../../pages/LoginPage";
import { SetupLLMPage } from "../../pages/SetupLLMPage";
import { SetupMembershipPage } from "../../pages/SetupMembershipPage";
import { useSessionStore } from "../../state/useSessionStore";

const signInWithPopupMock = vi.fn();
const registerBrowserMock = vi.fn();
const encryptSecretMock = vi.fn();
const setByokKeyMock = vi.fn();
const createStripeSessionMock = vi.fn();
const createApprovalRecordMock = vi.fn().mockResolvedValue({ id: "apr_1" });
const syncEvidenceMock = vi.fn().mockResolvedValue({ synced: true, runId: "run_1" });
const executeHeadlessMock = vi.fn().mockResolvedValue({
  status: "success",
  durationMs: 1200,
  screenshots: ["step_1.png"],
  output: { deterministic_nonce: 123 },
});

vi.mock("../../services/firebaseAuth", () => ({
  signInWithPopup: (...args: unknown[]) => signInWithPopupMock(...args),
}));

vi.mock("../../services/vault", () => ({
  encryptSecret: (...args: unknown[]) => encryptSecretMock(...args),
}));

vi.mock("../../services/playwrightClient", () => ({
  executeHeadless: (...args: unknown[]) => executeHeadlessMock(...args),
}));

vi.mock("../../services/solaceagiClient", async () => {
  const actual = await vi.importActual<typeof import("../../services/solaceagiClient")>("../../services/solaceagiClient");
  return {
    ...actual,
    registerBrowser: (...args: unknown[]) => registerBrowserMock(...args),
    setByokKey: (...args: unknown[]) => setByokKeyMock(...args),
    createStripeSession: (...args: unknown[]) => createStripeSessionMock(...args),
    createApprovalRecord: (...args: unknown[]) => createApprovalRecordMock(...args),
    syncEvidence: (...args: unknown[]) => syncEvidenceMock(...args),
  };
});

describe("integration: auth flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useSessionStore.setState({ session: null });
    signInWithPopupMock.mockResolvedValue({ uid: "u1", email: "u1@example.com", idToken: "idtok" });
    registerBrowserMock.mockResolvedValue({ apiKey: "sk_browser_auth", deviceId: "device_1" });
    encryptSecretMock.mockResolvedValue("enc");
    setByokKeyMock.mockResolvedValue({ ok: true });
    createStripeSessionMock.mockResolvedValue({ sessionId: "cs_1", checkoutUrl: "https://checkout" });
  });

  function renderFlow(initial = "/login"): void {
    render(
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/setup/llm-choice" element={<SetupLLMPage />} />
          <Route path="/setup/membership" element={<SetupMembershipPage />} />
          <Route path="/home" element={<HomePage />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("user logs in and reaches llm setup", async () => {
    renderFlow("/login");
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    await waitFor(() => {
      expect(screen.getByText("Choose LLM Mode")).toBeInTheDocument();
    });
  });

  it("byok path blocks continue with invalid key", () => {
    renderFlow("/setup/llm-choice");
    fireEvent.click(screen.getByRole("radio", { name: "BYOK" }));
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "short" } });
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
  });

  it("managed llm can proceed to membership", async () => {
    renderFlow("/setup/llm-choice");
    fireEvent.click(screen.getByRole("radio", { name: "Managed" }));
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => {
      expect(screen.getByText("Select Membership")).toBeInTheDocument();
    });
  });

  it("membership payment unlocks home", async () => {
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_auth",
        creditsUsd: 0,
        connectedApps: ["solace"],
      },
    });
    renderFlow("/setup/membership");
    fireEvent.click(screen.getByRole("button", { name: "Pay & Unlock Apps" }));
    await waitFor(() => {
      expect(screen.getByText("Home")).toBeInTheDocument();
    });
  });

  it("approval modal appears before run", () => {
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
    renderFlow("/home");
    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    expect(screen.getByRole("dialog", { name: "Approval Required" })).toBeInTheDocument();
  });

  it("approve starts execution path", async () => {
    vi.spyOn(Date, "now").mockReturnValue(707);
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
    renderFlow("/home");
    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "APPROVE & RUN" }));

    await waitFor(() => {
      expect(createApprovalRecordMock).toHaveBeenCalled();
      expect(executeHeadlessMock).toHaveBeenCalled();
      expect(syncEvidenceMock).toHaveBeenCalled();
    });
  });

  it("completed run appears in runs table", async () => {
    vi.spyOn(Date, "now").mockReturnValue(999);
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
    renderFlow("/home");
    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "APPROVE & RUN" }));
    await waitFor(() => {
      expect(screen.getByText("run_999")).toBeInTheDocument();
    });
  });
});
