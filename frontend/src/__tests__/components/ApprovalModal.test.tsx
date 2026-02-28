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
    expect(screen.getByText("Steps")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("renders scopes list", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("gmail.read.inbox")).toBeInTheDocument();
    expect(screen.getByText("gmail.draft.create")).toBeInTheDocument();
  });

  it("renders estimated cost", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("$0.12")).toBeInTheDocument();
  });

  it("renders estimated duration", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("18s")).toBeInTheDocument();
  });

  it("has override reason textbox", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByLabelText("Override reason")).toBeInTheDocument();
  });

  it("keeps override reason disabled until enabled", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByLabelText("Override reason")).toBeDisabled();
  });

  it("enables override reason when safety check is enabled", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Override safety check" }));
    expect(screen.getByLabelText("Override reason")).toBeEnabled();
  });

  it("approve triggers decision", async () => {
    const onDecision = vi.fn();
    render(<ApprovalModal open preview={mockPreview} onDecision={onDecision} />);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => {
      expect(onDecision).toHaveBeenCalledWith("approve", undefined);
    });
  });

  it("modify triggers decision with reason", async () => {
    const onDecision = vi.fn();
    render(<ApprovalModal open preview={mockPreview} onDecision={onDecision} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Override safety check" }));
    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "security exception" } });
    fireEvent.click(screen.getByRole("button", { name: "Modify" }));
    await waitFor(() => {
      expect(onDecision).toHaveBeenCalledWith("modify", "security exception");
    });
  });

  it("abort triggers decision", async () => {
    const onDecision = vi.fn();
    render(<ApprovalModal open preview={mockPreview} onDecision={onDecision} />);
    fireEvent.click(screen.getByRole("button", { name: "Abort" }));
    await waitFor(() => {
      expect(onDecision).toHaveBeenCalledWith("abort", undefined);
    });
  });

  it("shows all action buttons", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Modify" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abort" })).toBeInTheDocument();
  });

  it("trims whitespace for override validation", async () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Override safety check" }));
    fireEvent.change(screen.getByLabelText("Override reason"), { target: { value: "    " } });
    fireEvent.click(screen.getByRole("button", { name: "Modify" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Override reason must be at least 4 characters.");
    });
  });

  it("shows 30 second auto deny timer by default", () => {
    render(<ApprovalModal open preview={mockPreview} onDecision={vi.fn()} />);
    expect(screen.getByText("Auto-deny in 30s")).toBeInTheDocument();
  });

  it("auto-denies when timer reaches zero", async () => {
    const onDecision = vi.fn();
    render(<ApprovalModal open preview={mockPreview} onDecision={onDecision} autoDenySeconds={0} />);
    await waitFor(() => {
      expect(onDecision).toHaveBeenCalledWith("abort", undefined);
    });
  });
});
