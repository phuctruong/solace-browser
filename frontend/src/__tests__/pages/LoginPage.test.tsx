import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "../../pages/LoginPage";
import { useSessionStore } from "../../state/useSessionStore";
import { STORAGE_KEYS } from "../../utils/constants";

const navigateMock = vi.fn();
const signInWithPopupMock = vi.fn();
const registerBrowserMock = vi.fn();
const encryptSecretMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../services/firebaseAuth", () => ({
  signInWithPopup: (...args: unknown[]) => signInWithPopupMock(...args),
}));

vi.mock("../../services/solaceagiClient", () => ({
  registerBrowser: (...args: unknown[]) => registerBrowserMock(...args),
}));

vi.mock("../../services/vault", () => ({
  encryptSecret: (...args: unknown[]) => encryptSecretMock(...args),
}));

describe("<LoginPage>", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useSessionStore.setState({ session: null });

    signInWithPopupMock.mockResolvedValue({ uid: "uid_1", email: "u1@example.com", idToken: "idtok" });
    registerBrowserMock.mockResolvedValue({ apiKey: "sk_browser_abc", deviceId: "device_1" });
    encryptSecretMock.mockResolvedValue("encrypted_payload");
  });

  it("renders login headings and actions", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Login")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue with Gmail" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue with GitHub" })).toBeInTheDocument();
  });

  it("gmail login calls popup service with gmail provider", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    await waitFor(() => {
      expect(signInWithPopupMock).toHaveBeenCalledWith("gmail");
    });
  });

  it("github login calls popup service with github provider", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with GitHub" }));
    await waitFor(() => {
      expect(signInWithPopupMock).toHaveBeenCalledWith("github");
    });
  });

  it("registers browser with user identity", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    await waitFor(() => {
      expect(registerBrowserMock).toHaveBeenCalledWith("uid_1", "u1@example.com");
    });
  });

  it("encrypts API key with uid", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    await waitFor(() => {
      expect(encryptSecretMock).toHaveBeenCalledWith("sk_browser_abc", "uid_1");
    });
  });

  it("stores encrypted vault payload", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    await waitFor(() => {
      const vault = JSON.parse(localStorage.getItem(STORAGE_KEYS.VAULT) ?? "{}");
      expect(vault.payload).toBe("encrypted_payload");
      expect(vault.user).toBe("uid_1");
    });
  });

  it("writes session to store", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    await waitFor(() => {
      const session = useSessionStore.getState().session;
      expect(session?.apiKey).toBe("sk_browser_abc");
      expect(session?.connectedApps).toContain("solace");
    });
  });

  it("navigates to setup flow on success", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/setup/llm-choice");
    });
  });

  it("disables buttons during pending login", async () => {
    signInWithPopupMock.mockReturnValue(new Promise(() => undefined));
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    expect(screen.getByRole("button", { name: "Continue with Gmail" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Continue with GitHub" })).toBeDisabled();
  });

  it("shows error on auth failure", async () => {
    signInWithPopupMock.mockRejectedValue(new Error("Auth failed"));
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Gmail" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Auth failed");
    });
  });
});
