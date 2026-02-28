import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApprovalModal } from "../components/ApprovalModal";

describe("ApprovalModal", () => {
  it("requires reason before modify when override is enabled", () => {
    const onDecision = vi.fn();
    render(
      <ApprovalModal
        open
        preview={{
          steps: 5,
          scopes: ["gmail.read.inbox"],
          estimatedCostUsd: 0.12,
          estimatedDurationSec: 18,
        }}
        onDecision={onDecision}
      />,
    );

    fireEvent.click(screen.getByRole("checkbox", { name: "Override safety check" }));
    const modify = screen.getByRole("button", { name: "Modify" });

    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "Need manual exception" } });
    expect(screen.getByLabelText("Override reason")).toBeEnabled();

    fireEvent.click(modify);
    expect(onDecision).toHaveBeenCalledWith("modify", "Need manual exception");
  });

  it("supports approve decision", () => {
    const onDecision = vi.fn();
    render(
      <ApprovalModal
        open
        preview={{
          steps: 2,
          scopes: ["browser.click"],
          estimatedCostUsd: 0.05,
          estimatedDurationSec: 4,
        }}
        onDecision={onDecision}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(onDecision).toHaveBeenCalledWith("approve", undefined);
  });
});
