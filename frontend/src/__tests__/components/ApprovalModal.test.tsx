import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApprovalModal } from "../../components/ApprovalModal";
import { mockPreview } from "../__fixtures__/mockData";

describe("<ApprovalModal>", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not render when closed", () => {
    const { container } = render(<ApprovalModal open={false} preview={mockPreview} onDecision={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders when open", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByRole("dialog", { name: "Approval Required" })).toBeInTheDocument();
  });

  it("renders steps", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("Steps: 5")).toBeInTheDocument();
  });

  it("renders scopes list", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("Scopes: gmail.read.inbox, gmail.draft.create")).toBeInTheDocument();
  });

  it("renders estimated cost", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("Est. Cost: $0.12")).toBeInTheDocument();
  });

  it("renders estimated duration", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("Est. Duration: 18s")).toBeInTheDocument();
  });

  it("has override reason textbox", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByLabelText("Override reason")).toBeInTheDocument();
  });

  it("keeps override disabled for short reason", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "no" } });
    expect(screen.getByRole("button", { name: "OVERRIDE & EXPLAIN" })).toBeDisabled();
  });

  it("enables override when reason length > 3", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "valid reason" } });
    expect(screen.getByRole("button", { name: "OVERRIDE & EXPLAIN" })).toBeEnabled();
  });

  it("approve triggers decision", () => {
    const onDecision = vi.fn();
    render(<ApprovalModal open preview={mockPreview} onDecision={onDecision} />);
    fireEvent.click(screen.getByRole("button", { name: "APPROVE & RUN" }));
    expect(onDecision).toHaveBeenCalledWith("approve");
  });

  it("override triggers decision with reason", () => {
    const onDecision = vi.fn();
    render(<ApprovalModal open preview={mockPreview} onDecision={onDecision} />);
    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "security exception" } });
    fireEvent.click(screen.getByRole("button", { name: "OVERRIDE & EXPLAIN" }));
    expect(onDecision).toHaveBeenCalledWith("override", "security exception");
  });

  it("cancel triggers decision", () => {
    const onDecision = vi.fn();
    render(<ApprovalModal open preview={mockPreview} onDecision={onDecision} />);
    fireEvent.click(screen.getByRole("button", { name: "CANCEL" }));
    expect(onDecision).toHaveBeenCalledWith("cancel");
  });

  it("shows all action buttons", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByRole("button", { name: "APPROVE & RUN" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "OVERRIDE & EXPLAIN" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CANCEL" })).toBeInTheDocument();
  });

  it("trims whitespace for override enablement", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "    " } });
    expect(screen.getByRole("button", { name: "OVERRIDE & EXPLAIN" })).toBeDisabled();
  });

  it("shows 30 second auto deny timer by default", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("Auto-deny in 30s")).toBeInTheDocument();
  });

  it("auto-denies when timer reaches zero", async () => {
    const onDecision = vi.fn();
    render(<ApprovalModal open preview={mockPreview} onDecision={onDecision} autoDenySeconds={0} />);
    await waitFor(() => {
      expect(onDecision).toHaveBeenCalledWith("cancel");
    });
  });
});
