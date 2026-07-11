import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ApplicantForm } from "./ApplicantForm";

describe("ApplicantForm", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn((url: string) => {
      if (url === "/api/predict") {
        return Promise.resolve({
          json: () => Promise.resolve({ risk_score: 82, model_version: "1.0.0-real-uci" }),
        });
      }
      if (url === "/api/explain") {
        return Promise.resolve({
          json: () => Promise.resolve({
            top_factors: [
              { feature: "pay_0", friendly: "Most recent repayment status", contribution: 1.2, direction: "increases" },
            ],
          }),
        });
      }
      return Promise.reject(new Error(`unexpected fetch: ${url}`));
    }));
  });

  it("renders SHAP top_factors from the explain response after scoring", async () => {
    render(<ApplicantForm />);
    fireEvent.click(screen.getByText("Score applicant"));
    expect(await screen.findByText("Most recent repayment status")).toBeInTheDocument();
  });
});
