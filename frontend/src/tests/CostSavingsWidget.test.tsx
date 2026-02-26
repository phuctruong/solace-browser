import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CostSavingsWidget } from "../components/CostSavingsWidget";

describe("CostSavingsWidget", () => {
  it("renders calculated savings", () => {
    render(<CostSavingsWidget actualUsd={0.12} opusUsd={0.45} tokens={847} durationSec={17} />);
    expect(screen.getByText(/Saved: \$0\.33/)).toBeInTheDocument();
    expect(screen.getByText(/73% cheaper/)).toBeInTheDocument();
  });
});
