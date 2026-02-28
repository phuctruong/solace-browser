import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApprovalModal } from "../../components/ApprovalModal";
import { AppDetailPage } from "../../pages/AppDetailPage";
import { HomePage } from "../../pages/HomePage";
import { LoginPage } from "../../pages/LoginPage";
import { RunDetailPage } from "../../pages/RunDetailPage";
import { SetupMembershipPage } from "../../pages/SetupMembershipPage";
import { useSessionStore } from "../../state/useSessionStore";

const navigateMock = vi.fn();
const signInWithPopupMock = vi.fn();
const createUserWithEmailAndPasswordMock = vi.fn();

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

function mockFetch(routes: Record<string, unknown>): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      const key = `${method} ${url}`;
      const payload = routes[key];
      if (payload === undefined) {
        return Promise.resolve(new Response("missing", { status: 404 }));
      }
      return Promise.resolve(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }),
  );
}

describe("TASK-002 frontend contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useSessionStore.setState({
      session: {
        uid: "user_1",
        email: "user@example.com",
        apiKey: "sk_browser_local_dev",
        creditsUsd: 8,
        membershipTier: "Solace Pro",
        connectedApps: ["solace", "gmail"],
      },
    });
  });

  it("HomePage fetches installed apps, credits, and recent runs", async () => {
    mockFetch({
      "GET /api/v1/store/apps?installed=true": {
        apps: [
          { id: "gmail", name: "Gmail", status: "connected", lastRunTime: "2026-02-28T10:00:00Z" },
          { id: "slack", name: "Slack", status: "ready", lastRunTime: "2026-02-28T09:00:00Z" },
        ],
      },
      "GET /api/v1/billing/credits": { remaining: 42.75 },
      "GET /api/v1/history/recent": {
        runs: [
          { id: "run_201", appName: "Gmail", status: "success", startedAt: "2026-02-28T10:00:00Z", cost: 0.12 },
        ],
      },
    });

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Credits remaining")).toBeInTheDocument();
      expect(screen.getByText("42.75")).toBeInTheDocument();
      expect(screen.getByText("Recent runs")).toBeInTheDocument();
      expect(screen.getByText("Slack")).toBeInTheDocument();
    });
  });

  it("LoginPage renders Google sign-in plus email/password error flow", async () => {
    createUserWithEmailAndPasswordMock.mockRejectedValue(new Error("network error"));

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Continue with Google" })).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveTextContent("network error");
    });
  });

  it("AppDetailPage fetches manifest and renders scope table", async () => {
    mockFetch({
      "GET /api/v1/store/apps/gmail": {
        id: "gmail",
        name: "Gmail",
        description: "Inbox automation",
        category: "Communication",
        riskTier: "medium",
        scopes: {
          required: ["gmail.read.inbox"],
          optional: ["gmail.read.labels"],
          stepUp: ["gmail.send"],
        },
        budgets: { maxReads: 25, maxSends: 5, maxDeletes: 0 },
        approvalTaskId: "task_gmail_1",
      },
    });

    render(
      <MemoryRouter initialEntries={["/app/gmail"]}>
        <Routes>
          <Route path="/app/:appId" element={<AppDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Inbox automation")).toBeInTheDocument();
      expect(screen.getByRole("table", { name: "Scopes" })).toBeInTheDocument();
      expect(screen.getByText("gmail.send")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Run Now" })).toBeInTheDocument();
    });
  });

  it("RunDetailPage fetches run detail and renders verified timeline", async () => {
    mockFetch({
      "GET /api/v1/history/run_201": {
        id: "run_201",
        appName: "Gmail",
        status: "success",
        startedAt: "2026-02-28T10:00:00Z",
        cost: 0.12,
        level: "L2/Sonnet",
        tokens: 912,
        savingsVsFullLlm: 0.31,
        hashVerified: true,
        screenshots: [{ src: "/evidence/run_201-step-1.png", label: "Inbox" }],
        timeline: [{ name: "Fetch inbox", status: "success", durationMs: 1400 }],
      },
    });

    render(
      <MemoryRouter initialEntries={["/run/run_201"]}>
        <Routes>
          <Route path="/run/:runId" element={<RunDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Fetch inbox")).toBeInTheDocument();
      expect(screen.getByText("Verified")).toBeInTheDocument();
      expect(screen.getByRole("img", { name: "Inbox" })).toBeInTheDocument();
    });
  });

  it("ApprovalModal approve action posts to the task endpoint", async () => {
    mockFetch({
      "POST /api/v1/tasks/task_123/approve": { status: "approved", evidence_hash: "abc123" },
      "POST /api/v1/tasks/task_123/abort": { status: "aborted", evidence_hash: "def456" },
    });

    const onDecision = vi.fn();
    render(
      <ApprovalModal
        open
        preview={{ steps: 4, scopes: ["gmail.read.inbox"], estimatedCostUsd: 0.15, estimatedDurationSec: 12 }}
        onDecision={onDecision}
        taskId="task_123"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/v1/tasks/task_123/approve",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("SetupMembershipPage fetches plan cards and renders upgrade choices", async () => {
    mockFetch({
      "GET /api/v1/billing/plans": {
        plans: [
          { id: "free", name: "Free", price: "$0" },
          { id: "pro", name: "Solace Pro", price: "$8/mo" },
          { id: "enterprise", name: "Enterprise", price: "Custom" },
        ],
      },
    });

    render(
      <MemoryRouter>
        <SetupMembershipPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Free")).toBeInTheDocument();
      expect(screen.getByText("Solace Pro")).toBeInTheDocument();
      expect(screen.getByText("Enterprise")).toBeInTheDocument();
    });
  });
});
