import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "../../pages/LoginPage";
import { useSessionStore } from "../../state/useSessionStore";
import { STORAGE_KEYS } from "../../utils/constants";

const navigateMock = vi.fn();
const signInWithPopupMock = vi.fn();
const createUserWithEmailAndPasswordMock = vi.fn();
const registerBrowserMock = vi.fn();
const encryptSecretMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("firebase/auth", () => ({
  getAuth: vi.fn(() => ({})),
  GoogleAuthProvider: vi.fn().mockImplementation(() => ({})),
  signInWithPopup: (...args: unknown[]) => signInWithPopupMock(...args),
  createUserWithEmailAndPassword: (...args: unknown[]) => createUserWithEmailAndPasswordMock(...args),
}));

vi.mock("../../services/solaceagiClient", async () => {
  const actual = await vi.importActual<typeof import("../../services/solaceagiClient")>("../../services/solaceagiClient");
  return {
    ...actual,
    registerBrowser: (...args: unknown[]) => registerBrowserMock(...args),
  };
});

vi.mock("../../services/vault", () => ({
  encryptSecret: (...args: unknown[]) => encryptSecretMock(...args),
}));

describe("<LoginPage>", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useSessionStore.setState({ session: null });

    signInWithPopupMock.mockResolvedValue({ user: { uid: "uid_1", email: "u1@example.com" } });
    createUserWithEmailAndPasswordMock.mockResolvedValue({ user: { uid: "uid_2", email: "u2@example.com" } });
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
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email address")).toBeInTheDocument();
  });

  it("google login registers the browser", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => {
      expect(registerBrowserMock).toHaveBeenCalledWith("uid_1", "u1@example.com");
    });
  });

  it("encrypts and stores the browser key after google login", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => {
      expect(encryptSecretMock).toHaveBeenCalledWith("sk_browser_abc", "uid_1");
      const vault = JSON.parse(localStorage.getItem(STORAGE_KEYS.VAULT) ?? "{}");
      expect(vault.payload).toBe("encrypted_payload");
      expect(vault.user).toBe("uid_1");
    });
  });

  it("writes the authenticated session to the store", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => {
      const session = useSessionStore.getState().session;
      expect(session?.apiKey).toBe("sk_browser_abc");
      expect(session?.connectedApps).toContain("solace");
    });
  });

  it("navigates to llm setup on success", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/setup/llm-choice");
    });
  });

  it("disables actions during pending login", () => {
    signInWithPopupMock.mockReturnValue(new Promise(() => undefined));
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Create account" })).toBeDisabled();
  });

  it("shows error on google auth failure", async () => {
    signInWithPopupMock.mockRejectedValue(new Error("Auth failed"));
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Auth failed");
    });
  });

  it("creates an email account and completes registration", async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => {
      expect(createUserWithEmailAndPasswordMock).toHaveBeenCalled();
      expect(registerBrowserMock).toHaveBeenCalledWith("uid_2", "u2@example.com");
    });
  });
});
