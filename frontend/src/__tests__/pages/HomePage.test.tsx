import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "../../pages/HomePage";
import { useSessionStore } from "../../state/useSessionStore";

const navigateMock = vi.fn();
const createApprovalRecordMock = vi.fn().mockResolvedValue({ id: "apr_1" });
const syncEvidenceMock = vi.fn().mockResolvedValue({ synced: true, runId: "run_111" });
const executeHeadlessMock = vi.fn().mockResolvedValue({
  status: "success",
  durationMs: 1500,
  screenshots: ["step_1.png"],
  output: { deterministic_nonce: 1 },
});

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../services/solaceagiClient", async () => {
  const actual = await vi.importActual<typeof import("../../services/solaceagiClient")>("../../services/solaceagiClient");
  return {
    ...actual,
    createApprovalRecord: (...args: unknown[]) => createApprovalRecordMock(...args),
    syncEvidence: (...args: unknown[]) => syncEvidenceMock(...args),
  };
});

vi.mock("../../services/playwrightClient", () => ({
  executeHeadless: (...args: unknown[]) => executeHeadlessMock(...args),
}));

describe("<HomePage>", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.useRealTimers();
    useSessionStore.setState({ session: null });
  });

  it("shows greyed apps on first visit", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Sign in to Solace to unlock apps")).toBeInTheDocument();
  });

  it("shows unlocked message after membership", () => {
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_local_dev",
        membershipTier: "Dragon Warrior $8/month",
        creditsUsd: 5,
        connectedApps: ["solace", "gmail"],
      },
    });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Apps unlocked and ready.")).toBeInTheDocument();
  });

  it("renders Solace tile", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "Open Solace" })).toBeInTheDocument();
  });

  it("click Solace while locked navigates to login", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Open Solace" }));
    expect(navigateMock).toHaveBeenCalledWith("/login");
  });

  it("locked Gmail click does not navigate", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Open Gmail" }));
    expect(navigateMock).not.toHaveBeenCalledWith("/app/gmail");
  });

  it("unlocked unconnected app opens oauth popup", () => {
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_local_dev",
        membershipTier: "Dragon Warrior $8/month",
        creditsUsd: 5,
        connectedApps: ["solace"],
      },
    });
    const popup = { closed: true } as Window;
    const openSpy = vi.spyOn(window, "open").mockReturnValue(popup);

    vi.useFakeTimers();
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Open Gmail" }));
    vi.advanceTimersByTime(210);

    expect(openSpy).toHaveBeenCalledWith(
      "https://accounts.google.com/o/oauth2/v2/auth",
      "oauth",
      "width=520,height=700",
    );
  });

  it("shows approval modal before run", () => {
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_local_dev",
        membershipTier: "Dragon Warrior $8/month",
        creditsUsd: 5,
        connectedApps: ["solace", "gmail"],
      },
    });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    expect(screen.getByRole("dialog", { name: "Approval Required" })).toBeInTheDocument();
  });

  it("cancel from approval closes modal", async () => {
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_local_dev",
        membershipTier: "Dragon Warrior $8/month",
        creditsUsd: 5,
        connectedApps: ["solace", "gmail"],
      },
    });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Abort" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Approval Required" })).toBeNull();
    });
  });

  it("approve runs execution and records approvals", async () => {
    vi.spyOn(Date, "now").mockReturnValue(111);
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_local_dev",
        membershipTier: "Dragon Warrior $8/month",
        creditsUsd: 5,
        connectedApps: ["solace", "gmail"],
      },
    });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(createApprovalRecordMock).toHaveBeenCalled();
      expect(executeHeadlessMock).toHaveBeenCalled();
      expect(syncEvidenceMock).toHaveBeenCalled();
      expect(screen.getByText("run_111")).toBeInTheDocument();
    });
  });

  it("shows runs table section", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Runs")).toBeInTheDocument();
  });
});
