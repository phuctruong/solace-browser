import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CostSavingsWidget } from "../../components/CostSavingsWidget";

describe("<CostSavingsWidget>", () => {
  it("renders completion summary", () => {
    render(<CostSavingsWidget actualUsd={0.12} opusUsd={0.45} tokens={847} durationSec={17} />);
    expect(screen.getByText("Completed in 17s, 847 tokens")).toBeInTheDocument();
  });

  it("renders actual cost", () => {
    render(<CostSavingsWidget actualUsd={0.12} opusUsd={0.45} tokens={847} durationSec={17} />);
    expect(screen.getByText("Your cost: $0.12")).toBeInTheDocument();
  });

  it("renders opus cost", () => {
    render(<CostSavingsWidget actualUsd={0.12} opusUsd={0.45} tokens={847} durationSec={17} />);
    expect(screen.getByText("If you ran L3/Opus: $0.45")).toBeInTheDocument();
  });

  it("renders saved amount and percent", () => {
    render(<CostSavingsWidget actualUsd={0.12} opusUsd={0.45} tokens={847} durationSec={17} />);
    expect(screen.getByText("Saved: $0.33 (73% cheaper)")).toBeInTheDocument();
  });

  it("renders abcd note", () => {
    render(<CostSavingsWidget actualUsd={0.12} opusUsd={0.45} tokens={847} durationSec={17} />);
    expect(screen.getByText("ABCD testing found L2 works for this task")).toBeInTheDocument();
  });

  it("handles equal costs", () => {
    render(<CostSavingsWidget actualUsd={0.20} opusUsd={0.20} tokens={20} durationSec={2} />);
    expect(screen.getByText("Saved: $0.00 (0% cheaper)")).toBeInTheDocument();
  });

  it("handles zero opus cost", () => {
    render(<CostSavingsWidget actualUsd={0.20} opusUsd={0} tokens={20} durationSec={2} />);
    expect(screen.getByText("Saved: $0.00 (0% cheaper)")).toBeInTheDocument();
  });

  it("handles actual > opus", () => {
    render(<CostSavingsWidget actualUsd={0.50} opusUsd={0.45} tokens={20} durationSec={2} />);
    expect(screen.getByText("Saved: $0.00 (0% cheaper)")).toBeInTheDocument();
  });

  it("handles 1 token render", () => {
    render(<CostSavingsWidget actualUsd={0.01} opusUsd={0.02} tokens={1} durationSec={1} />);
    expect(screen.getByText("Completed in 1s, 1 tokens")).toBeInTheDocument();
  });

  it("formats tiny currency values", () => {
    render(<CostSavingsWidget actualUsd={0.001} opusUsd={0.002} tokens={10} durationSec={3} />);
    expect(screen.getByText("Your cost: $0.00")).toBeInTheDocument();
  });

  it("supports large token values", () => {
    render(<CostSavingsWidget actualUsd={1.2} opusUsd={4.5} tokens={120000} durationSec={44} />);
    expect(screen.getByText("Completed in 44s, 120000 tokens")).toBeInTheDocument();
  });

  it("supports large savings percentage", () => {
    render(<CostSavingsWidget actualUsd={0.01} opusUsd={1.0} tokens={200} durationSec={6} />);
    expect(screen.getByText("Saved: $0.99 (99% cheaper)")).toBeInTheDocument();
  });
});
