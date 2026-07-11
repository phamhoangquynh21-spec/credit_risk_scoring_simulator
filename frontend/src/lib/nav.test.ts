import { describe, it, expect } from "vitest";
import { navForRole } from "./nav";

describe("navForRole", () => {
  it("gives analyst the applicant + portfolio + performance links", () => {
    const hrefs = navForRole("analyst").map((n) => n.href);
    expect(hrefs).toContain("/assess");
    expect(hrefs).toContain("/portfolio");
    expect(hrefs).toContain("/performance");
  });
  it("limits executive to performance only", () => {
    const hrefs = navForRole("executive").map((n) => n.href);
    expect(hrefs).toEqual(["/performance"]);
  });
});
