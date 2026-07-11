import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricTile } from "./MetricTile";

describe("MetricTile", () => {
  it("renders label and value", () => {
    render(<MetricTile label="AUC-ROC" value="0.780" />);
    expect(screen.getByText("AUC-ROC")).toBeInTheDocument();
    expect(screen.getByText("0.780")).toBeInTheDocument();
  });
});
