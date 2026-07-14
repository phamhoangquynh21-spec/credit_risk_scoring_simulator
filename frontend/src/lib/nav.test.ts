import { describe, it, expect } from "vitest";
import { navForRole, navGroups } from "./nav";

describe("navForRole", () => {
  it("gives analyst the applicant + portfolio + performance links", () => {
    const hrefs = navForRole("analyst").map((n) => n.href);
    expect(hrefs).toContain("/assess");
    expect(hrefs).toContain("/portfolio");
    expect(hrefs).toContain("/performance");
  });
  it("gives every role the executive overview landing", () => {
    expect(navForRole("analyst").map((n) => n.href)).toContain("/");
    expect(navForRole("executive").map((n) => n.href)).toContain("/");
  });
  it("limits executive to read-only analytical surfaces (no data entry)", () => {
    const hrefs = navForRole("executive").map((n) => n.href);
    expect(hrefs).not.toContain("/assess");
    expect(hrefs).not.toContain("/portfolio");
    expect(hrefs).toContain("/performance");
    expect(hrefs).toContain("/fairness");
  });
});

describe("navGroups", () => {
  it("groups items under their section, preserving order", () => {
    const groups = navGroups("analyst").map((g) => g.group);
    expect(groups).toEqual(["Overview", "Assessment", "Governance"]);
  });
});
