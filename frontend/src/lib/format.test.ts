import { describe, it, expect } from "vitest";
import { riskBand, bandColor } from "./format";

describe("riskBand", () => {
  it("maps scores to bands", () => {
    expect(riskBand(10)).toBe("Low");
    expect(riskBand(50)).toBe("Medium");
    expect(riskBand(80)).toBe("High");
  });
  it("gives each band a distinct color", () => {
    expect(bandColor("Low")).not.toBe(bandColor("High"));
  });
});
