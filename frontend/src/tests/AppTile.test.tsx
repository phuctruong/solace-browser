import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppTile } from "../components/AppTile";
import type { AppModel } from "../types/App";

const app: AppModel = {
  id: "gmail",
  name: "Gmail",
  icon: "G",
  status: "connected",
  scopes: ["gmail.read.inbox"],
};

describe("AppTile", () => {
  it("disables run button when locked", () => {
    render(<AppTile app={app} locked onOpen={vi.fn()} onRun={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Run Now" })).toBeDisabled();
    expect(screen.getByText("Locked")).toBeInTheDocument();
  });

  it("calls handlers when unlocked", () => {
    const onOpen = vi.fn();
    const onRun = vi.fn();
    render(<AppTile app={app} locked={false} onOpen={onOpen} onRun={onRun} />);

    fireEvent.click(screen.getByRole("button", { name: "Open Gmail" }));
    fireEvent.click(screen.getByRole("button", { name: "Run Now" }));

    expect(onOpen).toHaveBeenCalledOnce();
    expect(onRun).toHaveBeenCalledOnce();
  });
});
