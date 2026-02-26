import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SetupLLMPage } from "../../pages/SetupLLMPage";
import { SetupMembershipPage } from "../../pages/SetupMembershipPage";
import { useSessionStore } from "../../state/useSessionStore";

const navigateMock = vi.fn();
const setByokKeyMock = vi.fn();
const createStripeSessionMock = vi.fn();

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
    setByokKey: (...args: unknown[]) => setByokKeyMock(...args),
    createStripeSession: (...args: unknown[]) => createStripeSessionMock(...args),
  };
});

describe("<Setup pages>", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useSessionStore.setState({ session: null });
    setByokKeyMock.mockResolvedValue({ ok: true });
    createStripeSessionMock.mockResolvedValue({ sessionId: "cs_1", checkoutUrl: "https://example.test" });
  });

  it("setup llm renders mode options", () => {
    render(
      <MemoryRouter>
        <SetupLLMPage />
      </MemoryRouter>,
    );
    expect(screen.getByText("BYOK")).toBeInTheDocument();
    expect(screen.getByText("Managed")).toBeInTheDocument();
  });

  it("setup llm continue disabled by default", () => {
    render(
      <MemoryRouter>
        <SetupLLMPage />
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
  });

  it("managed mode allows continue and navigates", async () => {
    render(
      <MemoryRouter>
        <SetupLLMPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("radio", { name: "Managed" }));
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/setup/membership");
    });
  });

  it("byok mode shows key input", () => {
    render(
      <MemoryRouter>
        <SetupLLMPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("radio", { name: "BYOK" }));
    expect(screen.getByLabelText("API key")).toBeInTheDocument();
  });

  it("byok continue disabled for short key", () => {
    render(
      <MemoryRouter>
        <SetupLLMPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("radio", { name: "BYOK" }));
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-1" } });
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
  });

  it("byok valid key calls service", async () => {
    render(
      <MemoryRouter>
        <SetupLLMPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("radio", { name: "BYOK" }));
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-valid123" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => {
      expect(setByokKeyMock).toHaveBeenCalledWith("sk-valid123");
    });
  });

  it("byok error renders alert", async () => {
    setByokKeyMock.mockRejectedValue(new Error("Invalid API key format"));
    render(
      <MemoryRouter>
        <SetupLLMPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("radio", { name: "BYOK" }));
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-valid123" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid API key format");
    });
  });

  it("membership renders tiers", () => {
    render(
      <MemoryRouter>
        <SetupMembershipPage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Dragon Warrior $8/month")).toBeInTheDocument();
    expect(screen.getByText("Enterprise $99/month")).toBeInTheDocument();
  });

  it("membership without session redirects to login", async () => {
    render(
      <MemoryRouter>
        <SetupMembershipPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Pay & Unlock Apps" }));
    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/login");
    });
  });

  it("membership with session calls stripe and navigates", async () => {
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_local_dev",
        creditsUsd: 0,
        connectedApps: ["solace"],
      },
    });
    render(
      <MemoryRouter>
        <SetupMembershipPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Pay & Unlock Apps" }));
    await waitFor(() => {
      expect(createStripeSessionMock).toHaveBeenCalledWith("Dragon Warrior $8/month");
      expect(navigateMock).toHaveBeenCalledWith("/home");
    });
  });

  it("membership flow updates store credits", async () => {
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_local_dev",
        creditsUsd: 0,
        connectedApps: ["solace"],
      },
    });
    render(
      <MemoryRouter>
        <SetupMembershipPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Pay & Unlock Apps" }));
    await waitFor(() => {
      expect(useSessionStore.getState().session?.creditsUsd).toBe(5);
      expect(useSessionStore.getState().session?.membershipTier).toBe("Dragon Warrior $8/month");
    });
  });

  it("membership payment failure shows error", async () => {
    createStripeSessionMock.mockRejectedValue(new Error("Payment failed"));
    useSessionStore.setState({
      session: {
        uid: "u1",
        email: "u1@example.com",
        apiKey: "sk_browser_local_dev",
        creditsUsd: 0,
        connectedApps: ["solace"],
      },
    });
    render(
      <MemoryRouter>
        <SetupMembershipPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Pay & Unlock Apps" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Payment failed");
    });
  });
});
