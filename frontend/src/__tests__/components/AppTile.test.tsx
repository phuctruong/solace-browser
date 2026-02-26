import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppTile } from "../../components/AppTile";
import { mockApps } from "../__fixtures__/mockData";

describe("<AppTile>", () => {
  const onOpen = vi.fn();
  const onRun = vi.fn();

  it("shows Locked status when locked", () => {
    render(<AppTile app={mockApps[1]} locked onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByText("Locked")).toBeInTheDocument();
  });

  it("shows Connected status when connected", () => {
    render(<AppTile app={{ ...mockApps[1], status: "connected" }} locked={false} onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("shows Error status when error", () => {
    render(<AppTile app={mockApps[2]} locked={false} onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("shows Ready status when unlocked and non-connected", () => {
    render(<AppTile app={mockApps[1]} locked={false} onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("run button disabled when locked", () => {
    render(<AppTile app={mockApps[1]} locked onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByRole("button", { name: "Run Now" })).toBeDisabled();
  });

  it("run button disabled when not connected", () => {
    render(<AppTile app={mockApps[1]} locked={false} onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByRole("button", { name: "Run Now" })).toBeDisabled();
  });

  it("run button enabled for connected app", () => {
    render(<AppTile app={{ ...mockApps[1], status: "connected" }} locked={false} onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByRole("button", { name: "Run Now" })).toBeEnabled();
  });

  it("invokes onOpen", () => {
    const openSpy = vi.fn();
    render(<AppTile app={mockApps[1]} locked={false} onOpen={openSpy} onRun={onRun} />);
    fireEvent.click(screen.getByRole("button", { name: "Open Gmail" }));
    expect(openSpy).toHaveBeenCalledWith(expect.objectContaining({ id: "gmail" }));
  });

  it("invokes onRun", () => {
    const runSpy = vi.fn();
    render(<AppTile app={{ ...mockApps[1], status: "connected" }} locked={false} onOpen={onOpen} onRun={runSpy} />);
    fireEvent.click(screen.getByRole("button", { name: "Run Now" }));
    expect(runSpy).toHaveBeenCalledOnce();
  });

  it("shows budget value", () => {
    render(<AppTile app={mockApps[1]} locked={false} onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByText("Budget 24")).toBeInTheDocument();
  });

  it("shows no budget when budget is undefined", () => {
    render(<AppTile app={mockApps[0]} locked={false} onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByText("No budget")).toBeInTheDocument();
  });

  it("renders icon content", () => {
    render(<AppTile app={mockApps[2]} locked={false} onOpen={onOpen} onRun={onRun} />);
    expect(screen.getByText("L")).toBeInTheDocument();
  });
});
