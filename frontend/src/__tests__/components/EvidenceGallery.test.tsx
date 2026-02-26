import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceGallery } from "../../components/EvidenceGallery";

describe("<EvidenceGallery>", () => {
  it("shows empty message with no screenshots", () => {
    render(<EvidenceGallery screenshots={[]} />);
    expect(screen.getByText("No screenshots captured.")).toBeInTheDocument();
  });

  it("renders heading when screenshots exist", () => {
    render(<EvidenceGallery screenshots={["step_1.png"]} />);
    expect(screen.getByText("Evidence Gallery")).toBeInTheDocument();
  });

  it("renders one image per screenshot", () => {
    const { container } = render(<EvidenceGallery screenshots={["step_1.png", "step_2.png"]} />);
    expect(container.querySelectorAll("img")).toHaveLength(2);
  });

  it("renders correct alt text", () => {
    render(<EvidenceGallery screenshots={["step_9.png"]} />);
    expect(screen.getByAltText("step_9.png")).toBeInTheDocument();
  });

  it("renders evidence path in src", () => {
    render(<EvidenceGallery screenshots={["shot.png"]} />);
    expect(screen.getByAltText("shot.png")).toHaveAttribute("src", "/evidence/shot.png");
  });

  it("renders figcaption text", () => {
    render(<EvidenceGallery screenshots={["proof.png"]} />);
    expect(screen.getByText("proof.png")).toBeInTheDocument();
  });

  it("supports many screenshots", () => {
    const shots = Array.from({ length: 5 }, (_, i) => `s${i}.png`);
    const { container } = render(<EvidenceGallery screenshots={shots} />);
    expect(container.querySelectorAll("figure")).toHaveLength(5);
  });

  it("does not render heading on empty state", () => {
    const { queryByText } = render(<EvidenceGallery screenshots={[]} />);
    expect(queryByText("Evidence Gallery")).toBeNull();
  });

  it("renders unique screenshot names", () => {
    render(<EvidenceGallery screenshots={["a.png", "b.png"]} />);
    expect(screen.getByAltText("a.png")).toBeInTheDocument();
    expect(screen.getByAltText("b.png")).toBeInTheDocument();
  });

  it("handles screenshot names with spaces", () => {
    render(<EvidenceGallery screenshots={["step 1.png"]} />);
    expect(screen.getByAltText("step 1.png")).toHaveAttribute("src", "/evidence/step 1.png");
  });
});
