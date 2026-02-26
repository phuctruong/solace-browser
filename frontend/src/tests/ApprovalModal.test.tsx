import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApprovalModal } from "../components/ApprovalModal";

describe("ApprovalModal", () => {
  it("requires reason before override", () => {
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

    const override = screen.getByRole("button", { name: "OVERRIDE & EXPLAIN" });
    expect(override).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "Need manual exception" } });
    expect(override).toBeEnabled();

    fireEvent.click(override);
    expect(onDecision).toHaveBeenCalledWith("override", "Need manual exception");
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

    fireEvent.click(screen.getByRole("button", { name: "APPROVE & RUN" }));
    expect(onDecision).toHaveBeenCalledWith("approve");
  });
});
