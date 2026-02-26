import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("App", () => {
  it("renders home route by default", () => {
    render(<App />);
    expect(screen.getByText("Home")).toBeInTheDocument();
  });
});
