import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "../pages/HomePage";
import { useSessionStore } from "../state/useSessionStore";

vi.stubGlobal("open", vi.fn(() => ({ closed: true })));

describe("HomePage", () => {
  beforeEach(() => {
    localStorage.clear();
    useSessionStore.setState({ session: null });
  });

  it("shows locked state without session", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Sign in to Solace to unlock apps")).toBeInTheDocument();
  });

  it("shows unlocked state with membership", () => {
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
});
