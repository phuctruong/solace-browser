import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RunsTable } from "../../components/RunsTable";
import { mockRuns } from "../__fixtures__/mockData";

describe("<RunsTable>", () => {
  it("renders empty state", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByText("No runs yet.")).toBeInTheDocument();
  });

  it("renders table headers", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={mockRuns} />
      </MemoryRouter>,
    );
    ["Run", "App", "Status", "Started", "Duration", "Cost"].forEach((h) => {
      expect(screen.getByText(h)).toBeInTheDocument();
    });
  });

  it("renders all run ids", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={mockRuns} />
      </MemoryRouter>,
    );
    expect(screen.getByText("run_alpha")).toBeInTheDocument();
    expect(screen.getByText("run_beta")).toBeInTheDocument();
  });

  it("renders app names", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={mockRuns} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Gmail")).toBeInTheDocument();
    expect(screen.getByText("LinkedIn")).toBeInTheDocument();
  });

  it("renders status text", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={mockRuns} />
      </MemoryRouter>,
    );
    expect(screen.getByText("success")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("formats duration for seconds", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={mockRuns} />
      </MemoryRouter>,
    );
    expect(screen.getByText("14s")).toBeInTheDocument();
  });

  it("formats duration for ms", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={[mockRuns[1]]} />
      </MemoryRouter>,
    );
    expect(screen.getByText("900ms")).toBeInTheDocument();
  });

  it("formats usd cost", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={mockRuns} />
      </MemoryRouter>,
    );
    expect(screen.getByText("$0.12")).toBeInTheDocument();
    expect(screen.getByText("$0.03")).toBeInTheDocument();
  });

  it("renders links to run detail", () => {
    render(
      <MemoryRouter>
        <RunsTable runs={mockRuns} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "run_alpha" })).toHaveAttribute("href", "/run/run_alpha");
  });

  it("renders one body row per run", () => {
    const { container } = render(
      <MemoryRouter>
        <RunsTable runs={mockRuns} />
      </MemoryRouter>,
    );
    expect(container.querySelectorAll("tbody tr")).toHaveLength(2);
  });

  it("supports single-run list", () => {
    const { container } = render(
      <MemoryRouter>
        <RunsTable runs={[mockRuns[0]]} />
      </MemoryRouter>,
    );
    expect(container.querySelectorAll("tbody tr")).toHaveLength(1);
  });

  it("does not render table when runs are empty", () => {
    const { container } = render(
      <MemoryRouter>
        <RunsTable runs={[]} />
      </MemoryRouter>,
    );
    expect(container.querySelector("table")).toBeNull();
  });
});
