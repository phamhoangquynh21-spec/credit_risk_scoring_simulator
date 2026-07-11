import { describe, it, expect } from "vitest";
import { bandCounts } from "./bands";

describe("bandCounts", () => {
  it("buckets scores into the three bands", () => {
    expect(bandCounts([10, 40, 40, 90])).toEqual({ Low: 1, Medium: 2, High: 1 });
  });
});
