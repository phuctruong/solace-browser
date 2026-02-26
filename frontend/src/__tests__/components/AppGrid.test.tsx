import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppGrid } from "../../components/AppGrid";
import { mockApps } from "../__fixtures__/mockData";

describe("<AppGrid>", () => {
  it("renders all app tiles", () => {
    render(<AppGrid apps={mockApps} locked connectedAppIds={[]} onOpen={vi.fn()} onRun={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Open Solace" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Gmail" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open LinkedIn" })).toBeInTheDocument();
  });

  it("shows solace as connected even when locked", () => {
    render(<AppGrid apps={mockApps} locked connectedAppIds={[]} onOpen={vi.fn()} onRun={vi.fn()} />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("shows non-solace tiles as locked when locked", () => {
    render(<AppGrid apps={mockApps} locked connectedAppIds={[]} onOpen={vi.fn()} onRun={vi.fn()} />);
    const lockedLabels = screen.getAllByText("Locked");
    expect(lockedLabels.length).toBeGreaterThanOrEqual(2);
  });

  it("marks connected apps from connectedAppIds", () => {
    render(<AppGrid apps={mockApps} locked={false} connectedAppIds={["gmail"]} onOpen={vi.fn()} onRun={vi.fn()} />);
    const runButtons = screen.getAllByRole("button", { name: "Run Now" });
    expect(runButtons.some((button) => !button.hasAttribute("disabled"))).toBe(true);
  });

  it("passes onOpen callback", () => {
    const onOpen = vi.fn();
    render(<AppGrid apps={mockApps} locked={false} connectedAppIds={["gmail"]} onOpen={onOpen} onRun={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Gmail" }));
    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: "gmail" }));
  });

  it("passes onRun callback", () => {
    const onRun = vi.fn();
    render(<AppGrid apps={mockApps} locked={false} connectedAppIds={["gmail"]} onOpen={vi.fn()} onRun={onRun} />);
    fireEvent.click(screen.getAllByRole("button", { name: "Run Now" })[1]);
    expect(onRun).toHaveBeenCalledWith(expect.objectContaining({ id: "gmail" }));
  });

  it("renders budgets", () => {
    render(<AppGrid apps={mockApps} locked={false} connectedAppIds={[]} onOpen={vi.fn()} onRun={vi.fn()} />);
    expect(screen.getByText("Budget 24")).toBeInTheDocument();
    expect(screen.getByText("Budget 12")).toBeInTheDocument();
  });

  it("renders fallback no budget", () => {
    render(<AppGrid apps={mockApps} locked={false} connectedAppIds={[]} onOpen={vi.fn()} onRun={vi.fn()} />);
    expect(screen.getByText("No budget")).toBeInTheDocument();
  });

  it("renders expected number of run buttons", () => {
    render(<AppGrid apps={mockApps} locked={false} connectedAppIds={["solace", "gmail", "linkedin"]} onOpen={vi.fn()} onRun={vi.fn()} />);
    expect(screen.getAllByRole("button", { name: "Run Now" })).toHaveLength(3);
  });

  it("handles empty apps list", () => {
    const { container } = render(<AppGrid apps={[]} locked={false} connectedAppIds={[]} onOpen={vi.fn()} onRun={vi.fn()} />);
    expect(container.querySelectorAll("article")).toHaveLength(0);
  });
});
