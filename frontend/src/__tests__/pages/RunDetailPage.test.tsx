import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { RunDetailPage } from "../../pages/RunDetailPage";
import { STORAGE_KEYS } from "../../utils/constants";
import { mockRuns } from "../__fixtures__/mockData";

describe("<RunDetailPage>", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  function renderWithRoute(path: string): void {
    render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/run/:runId" element={<RunDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("renders run detail header with matching id", () => {
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(mockRuns));
    renderWithRoute("/run/run_alpha");
    expect(screen.getByText("Run Detail: run_alpha")).toBeInTheDocument();
  });

  it("falls back to sample when run id not found", () => {
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(mockRuns));
    renderWithRoute("/run/unknown_id");
    expect(screen.getByText(/Run Detail:/)).toBeInTheDocument();
  });

  it("renders timeline step names", () => {
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(mockRuns));
    renderWithRoute("/run/run_alpha");
    expect(screen.getByText(/Fetch inbox/)).toBeInTheDocument();
  });

  it("shows verified hash message for verified run", () => {
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(mockRuns));
    renderWithRoute("/run/run_alpha");
    expect(screen.getByText(/Hash chain verified/)).toBeInTheDocument();
  });

  it("shows failed hash message for unverified run", () => {
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(mockRuns));
    renderWithRoute("/run/run_beta");
    expect(screen.getByText("Hash chain verification failed")).toBeInTheDocument();
  });

  it("shows evidence gallery heading when screenshots exist", () => {
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(mockRuns));
    renderWithRoute("/run/run_alpha");
    expect(screen.getByText("Evidence Gallery")).toBeInTheDocument();
  });

  it("shows empty evidence message when screenshots missing", () => {
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(mockRuns));
    renderWithRoute("/run/run_beta");
    expect(screen.getByText("No screenshots captured.")).toBeInTheDocument();
  });

  it("shows cost savings text", () => {
    localStorage.setItem(STORAGE_KEYS.RUNS, JSON.stringify(mockRuns));
    renderWithRoute("/run/run_alpha");
    expect(screen.getByText(/Saved: \$0\.33/)).toBeInTheDocument();
  });
});
