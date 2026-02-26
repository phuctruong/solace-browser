import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RunDetailPage } from "../pages/RunDetailPage";

describe("RunDetailPage", () => {
  it("renders timeline and hash verification", () => {
    render(
      <MemoryRouter initialEntries={["/run/run_001"]}>
        <Routes>
          <Route path="/run/:runId" element={<RunDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText(/Run Detail: run_001/)).toBeInTheDocument();
    expect(screen.getByText(/Hash chain verified/)).toBeInTheDocument();
    expect(screen.getByText(/Saved: \$0\.33/)).toBeInTheDocument();
  });
});
